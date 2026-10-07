from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.domain.narrative import preset_plan
from app.domain.outline import OutlineDraft
from app.llm.base import OutlineGenerationInput, OutlineGenerator, OutlineSourceSection

# 总预算压住 prompt 体积，单节上限避免某一节吞掉全部配额；
# 按整节追加，超长只截断该节正文，保证 ref 与文本不会错位。
MAX_TOTAL_SOURCE_CHARS = 12_000
MAX_SECTION_CHARS = 2_000


class OutlineWorkflowState(TypedDict, total=False):
    input: OutlineGenerationInput
    prepared: OutlineGenerationInput
    draft: OutlineDraft


def prepare_outline_input(
    payload: OutlineGenerationInput,
    *,
    max_total_chars: int = MAX_TOTAL_SOURCE_CHARS,
    max_section_chars: int = MAX_SECTION_CHARS,
) -> OutlineGenerationInput:
    """清理并裁剪来源小节，供大纲准备流程与单测共用。"""
    prepared_sections: list[OutlineSourceSection] = []
    used_chars = 0

    for section in payload.sections:
        heading = section.heading.strip() if section.heading else None
        text = " ".join(section.text.split())
        locator = section.locator.strip()

        if not text and not heading:
            continue

        if len(text) > max_section_chars:
            text = text[:max_section_chars]

        remaining = max_total_chars - used_chars
        if remaining <= 0:
            break

        heading_len = len(heading or "")
        # 标题本身已超出剩余预算时停止，避免截断 heading 造成语义残缺
        if heading_len > remaining:
            break

        text_budget = min(len(text), remaining - heading_len)
        text = text[:text_budget]
        section_cost = len(text) + heading_len
        if section_cost <= 0:
            break

        prepared_sections.append(
            OutlineSourceSection(
                ref=section.ref,
                heading=heading,
                level=section.level,
                text=text,
                locator=locator,
            )
        )
        used_chars += section_cost
        if used_chars >= max_total_chars:
            break

    return payload.model_copy(update={"sections": prepared_sections})


def build_outline_workflow(
    generator: OutlineGenerator,
    *,
    on_progress: Callable[[int, str], Awaitable[None]] | None = None,
):
    """编译「准备输入 → 调用生成器」的大纲工作流。

    生成器负责长大纲分批，Graph 负责来源准备、叙事与时间分配。
    """

    async def prepare(state: OutlineWorkflowState) -> dict[str, OutlineGenerationInput]:
        return {"prepared": prepare_outline_input(state["input"])}

    async def generate(state: OutlineWorkflowState) -> dict[str, OutlineDraft]:
        if on_progress:
            await on_progress(45, "正在生成逐页大纲，长篇将分批补充内容与来源")
        draft = await generator.generate(state["prepared"])
        payload = state["prepared"]
        if payload.narrative:
            weights = [
                0.5 if page.page_role in ("cover", "toc", "section") else 1 for page in draft.pages
            ]
            total_seconds = payload.brief.duration_minutes * 60
            allocations = [max(1, int(total_seconds * w / sum(weights))) for w in weights]
            for index in range(total_seconds - sum(allocations)):
                allocations[index % len(allocations)] += 1
            draft = draft.model_copy(
                update={
                    "narrative": payload.narrative,
                    "pages": [
                        page.model_copy(update={"speaker_seconds": seconds})
                        for page, seconds in zip(draft.pages, allocations, strict=True)
                    ],
                }
            )
        return {"draft": draft}

    async def plan(state: OutlineWorkflowState) -> dict:
        payload = state["prepared"]
        if not payload.brief.narrative_enabled:
            return {}
        if on_progress:
            await on_progress(25, "正在分析听众需求、规划全篇叙事")
        planner = getattr(generator, "plan", None)
        narrative = (
            await planner(payload) if planner else preset_plan(payload.brief, payload.audience)
        )
        return {"prepared": payload.model_copy(update={"narrative": narrative})}

    graph = StateGraph(OutlineWorkflowState)
    graph.add_node("prepare", prepare)
    graph.add_node("generate", generate)
    graph.add_node("plan", plan)
    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "plan")
    graph.add_edge("plan", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


async def run_outline_workflow(
    workflow,
    payload: OutlineGenerationInput,
) -> OutlineDraft:
    """异步调用封装：输入生成参数，返回校验后的大纲草稿。"""
    result = await workflow.ainvoke({"input": payload})
    draft = result.get("draft")
    if not isinstance(draft, OutlineDraft):
        raise RuntimeError("大纲工作流未产出 OutlineDraft")
    return draft
