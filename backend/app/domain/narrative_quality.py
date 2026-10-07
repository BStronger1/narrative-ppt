"""Editorial review flags, kept separate from structural errors and empirical claims."""

from collections import Counter

from app.domain.validation import StructureIssue


def review_narrative(pages, *, duration_minutes: int, slide_id: str = "deck"):
    issues = []

    def warn(code, message):
        issues.append(
            StructureIssue(
                severity="warning", code=code, message=message, slide_id=slide_id, slot_id=None
            )
        )

    titles = [page.title.strip() for page in pages]
    if len(set(titles)) < len(titles):
        warn("narrative_repeated_title", "存在重复标题，请检查相邻页面是否推进了新的信息。")
    total = sum(page.speaker_seconds or 0 for page in pages)
    if total != duration_minutes * 60:
        warn("narrative_timing", "页面增删或修改后讲述时长与目标不一致，请重新分配时间并排练。")
    content = [page for page in pages if page.page_role == "content"]
    kinds = Counter(page.visual_kind for page in content)
    if len(content) >= 4 and max(kinds.values(), default=0) == len(content):
        warn(
            "narrative_visual_rhythm",
            "内容页采用相同的视觉任务，可检查是否适合穿插对比或过程解释；不要为变化添加无关图表。",
        )
    if any((page.speaker_seconds or 60) < 15 and len(page.key_points) >= 4 for page in content):
        warn("narrative_pacing", "有页面在较短时间内安排了多个要点，建议删减或增加讲述时间。")
    return issues
