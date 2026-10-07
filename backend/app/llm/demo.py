"""显式演示模式：确定性摘录材料，绝不冒充真实模型生成。"""

import re

from app.domain.evidence import PointEvidence
from app.domain.flex_layout import FlexContainer, FlexLeaf
from app.domain.outline import OutlineDraft, OutlinePageDraft
from app.domain.slide_draft import (
    BulletsContent,
    FlexBulletsContent,
    FlexSlideDraft,
    FlexTextContent,
    SlideDraft,
    TextContent,
)


class DemoOutlineGenerator:
    async def generate(self, payload):
        headings = ["背景与目标", "问题与需求", "方案设计", "实现与分工", "验证结果", "不足与计划"]
        if payload.narrative:
            headings = payload.narrative.arc
        sections = [s for s in payload.sections if s.locator != "主题"]
        if len(sections) > payload.page_count and not re.search(r"[:：]", sections[0].text):
            sections = sections[1:]
        pages = []
        for index in range(payload.page_count):
            source = sections[index] if index < len(sections) else None
            sentences = (
                []
                if source is None
                else [
                    text.strip()
                    for text in re.split(r"[。\n]", source.text)
                    if len(text.strip()) >= 4
                ]
            )
            points = [text[:100] for text in sentences[:3]]
            evidence = [
                PointEvidence(point=point, kind="source", ref=source.ref, quote=point)
                for point in points
            ]
            while len(points) < 2:
                point = f"【待补充】{headings[index % len(headings)]}的" + (
                    "具体材料" if not points else "验证依据与边界"
                )
                points.append(point)
                evidence.append(PointEvidence(point=point))
            pages.append(
                OutlinePageDraft(
                    narrative_role=headings[
                        min(index * len(headings) // payload.page_count, len(headings) - 1)
                    ]
                    if payload.narrative
                    else "",
                    visual_kind="claim" if payload.narrative else "auto",
                    title=(source.heading or re.split(r"[:：]", source.text)[0][:30])
                    if source
                    else headings[index % len(headings)],
                    objective="根据原始材料陈述项目进展，明确尚未验证的内容",
                    key_points=points,
                    point_evidence=evidence,
                    source_refs=[source.ref] if source else [],
                    layout_id="bullets",
                    page_role="summary" if index == payload.page_count - 1 else "content",
                )
            )
        return OutlineDraft(pages=pages)


class DemoSlideGenerator:
    async def generate(self, payload):
        seconds = payload.speaker_seconds or max(
            1, round(payload.brief.duration_minutes * 60 / payload.total_pages)
        )
        notes = (
            "演示模式：本页由规则摘录生成，未调用语言模型。"
            f"建议讲述约 {seconds} 秒。"
            "讲解材料中的事实，并明确待补充内容。"
        )
        if payload.layout_mode == "fixed":
            return SlideDraft(
                blocks=[
                    TextContent(slot_id="title", text=payload.page_title),
                    BulletsContent(slot_id="body", items=payload.key_points),
                ],
                speaker_notes=notes,
            )
        return FlexSlideDraft(
            blocks=[
                FlexTextContent(id="title", text=payload.page_title),
                FlexBulletsContent(id="body", items=payload.key_points),
            ],
            layout_tree=FlexContainer(
                type="column",
                id="root",
                children=[
                    FlexLeaf(id="title-leaf", block_id="title", grow=0.45, text_style="title"),
                    FlexLeaf(id="body-leaf", block_id="body", grow=1.5, text_style="bullet"),
                ],
            ),
            speaker_notes=notes,
        )
