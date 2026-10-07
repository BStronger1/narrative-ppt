"""按当前来源重算证据状态，供 API 和导出讲稿共用。"""

from app.domain.evidence import sanitize_evidence
from app.domain.outline import OutlinePage
from app.llm.base import OutlineSourceSection


def source_index(project):
    return {
        f"S{i}:{j}": {
            "ref": f"S{i}:{j}",
            "filename": source.filename or "粘贴材料",
            "kind": source.kind,
            **section,
        }
        for i, source in enumerate(project.sources, 1)
        for j, section in enumerate(source.sections, 1)
    }


def checked_page(page, project):
    sources = source_index(project)
    sections = {ref: OutlineSourceSection(**value) for ref, value in sources.items()}
    return sanitize_evidence(
        page,
        sections,
        topic_refs={ref for ref, value in sources.items() if value["kind"] == "topic"},
    )


def page_evidence(page, project):
    sources = source_index(project)
    checked = checked_page(page, project)
    return [
        {
            **item.model_dump(),
            "source": sources.get(item.ref) if item.ref else None,
        }
        for item in checked.point_evidence
    ]


def evidence_notes(project, outline_page_id):
    if not project.outline:
        return ""
    page = next((p for p in project.outline.pages if str(p["id"]) == str(outline_page_id)), None)
    if page is None:
        return ""
    items = page_evidence(OutlinePage.model_validate(page), project)
    lines = ["大纲要点来源（摘录匹配不代表结论已核验，正文编辑后请重新核对）："]
    for item in items:
        if item["source"]:
            source = item["source"]
            lines.append(
                f"{item['point']}\n[{item['ref']}] {source['filename']} "
                f"{source['locator']}：{item['quote']}"
            )
        else:
            label = "AI 推断，需核对" if item["kind"] == "inference" else "待补充依据"
            lines.append(f"{item['point']} — {label}")
    narrative = getattr(project.outline, "narrative", None)
    if narrative:
        lines.extend(
            [
                "",
                "讲述提示（设计建议，不是事实来源）：",
                f"听众：{narrative['audience_summary']}",
                f"全篇主线：{narrative['throughline']}",
                f"本页作用：{page.get('narrative_role') or page['objective']}",
            ]
        )
        if page.get("speaker_seconds"):
            lines.append(f"建议用时：{page['speaker_seconds']} 秒（需实际排练校准）")
        if page.get("transition"):
            lines.append(f"衔接：{page['transition']}")
    return "\n".join(lines)
