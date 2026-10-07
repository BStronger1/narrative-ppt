"""整份 PPT 质量报告：组装 Deck 与来源上下文，复用导出前检查。"""

from __future__ import annotations

import uuid

from app.domain.content import Deck as ContentDeck
from app.domain.export_check import ExportCheckReport, run_export_check
from app.domain.narrative_quality import review_narrative
from app.domain.outline import OutlinePage
from app.domain.quality import check_unsourced_numbers
from app.domain.theme import resolve_project_theme
from app.domain.validation import StructureIssue
from app.llm.base import OutlineSourceSection
from app.models.project import Project
from app.models.slide import Slide
from app.services.deck import outline_pages, to_content_slide
from app.services.evidence import checked_page
from app.services.media import load_image, media_key_from_url


def project_to_content_deck(project: Project, slides: list[Slide]) -> ContentDeck:
    content_slides = []
    for slide in slides:
        if slide.status != "ready" or not slide.blocks:
            continue
        content_slides.append(to_content_slide(slide))
    return ContentDeck(
        id=str(project.id),
        title=project.title,
        theme_id=project.theme_id,
        slides=content_slides,
    )


def _section_index(project: Project) -> dict[str, OutlineSourceSection]:
    return {
        f"S{source_index}:{section_index}": OutlineSourceSection(
            ref=f"S{source_index}:{section_index}",
            heading=section.get("heading"),
            level=section.get("level", 0),
            text=section.get("text", ""),
            locator=section.get("locator", ""),
        )
        for source_index, source in enumerate(project.sources, start=1)
        for section_index, section in enumerate(source.sections, start=1)
    }


def _page_by_outline_id(project: Project) -> dict[uuid.UUID, OutlinePage]:
    return {page.id: page for page in outline_pages(project)}


def slide_titles_map(slides: list[Slide]) -> dict[str, str]:
    return {str(slide.id): slide.title for slide in slides if slide.status == "ready"}


def slide_sources_map(project: Project, slides: list[Slide]) -> dict[str, str]:
    """每页引用材料拼成文本，供「数据无来源」检查。"""
    sections = _section_index(project)
    pages = _page_by_outline_id(project)
    result: dict[str, str] = {}
    for slide in slides:
        if slide.status != "ready":
            continue
        page = pages.get(slide.outline_page_id)
        if page is None:
            result[str(slide.id)] = ""
            continue
        parts: list[str] = []
        for ref in page.source_refs:
            section = sections.get(ref)
            if section is None:
                continue
            if section.heading:
                parts.append(section.heading)
            if section.text:
                parts.append(section.text)
        result[str(slide.id)] = "\n".join(parts)
    return result


def slide_roles_map(project: Project, slides: list[Slide]) -> dict[str, str]:
    pages = _page_by_outline_id(project)
    result: dict[str, str] = {}
    for slide in slides:
        if slide.status != "ready":
            continue
        page = pages.get(slide.outline_page_id)
        if page is None:
            continue
        result[str(slide.id)] = getattr(page, "page_role", None) or "content"
    return result


def build_quality_report(project: Project, slides: list[Slide]) -> ExportCheckReport:
    """可复用的质量报告入口，供导出等接口直接调用。"""
    deck = project_to_content_deck(project, slides)
    report = run_export_check(
        deck,
        theme=resolve_project_theme(project),
        slide_titles=slide_titles_map(slides),
        slide_sources=slide_sources_map(project, slides),
        content_density=getattr(project, "content_density", None) or "medium",
        slide_roles=slide_roles_map(project, slides),
        load_image=load_image,
        media_key_from_url=media_key_from_url,
    )
    pages = _page_by_outline_id(project)
    if getattr(project.outline, "narrative", None):
        for issue in report.issues:
            if issue.code == "thin_content":
                issue.message = (
                    "本页内容较简洁，请确认核心观点与必要证据已说明；"
                    "可以保留留白，不必为了填满页面添加数据。"
                )
        sources = slide_sources_map(project, slides)
        for slide in deck.slides:
            report.issues.extend(
                check_unsourced_numbers(slide, sources.get(slide.id, ""), include_quantities=True)
            )
        report.issues.extend(
            review_narrative(
                list(pages.values()),
                duration_minutes=(project.brief or {}).get("duration_minutes", 5),
                slide_id=str(slides[0].id) if slides else "deck",
            )
        )
    for slide in slides:
        page = pages.get(slide.outline_page_id)
        if page is None or slide.status != "ready":
            continue
        evidence = checked_page(page, project).point_evidence
        missing = sum(item.kind == "missing" for item in evidence)
        inferred = sum(item.kind == "inference" for item in evidence)
        if missing or inferred:
            report.issues.append(
                StructureIssue(
                    severity="warning",
                    code="evidence_review",
                    slide_id=str(slide.id),
                    slot_id=None,
                    message=f"本页大纲有 {missing} 条要点待补充依据、{inferred} 条推断需核对",
                )
            )
    return report
