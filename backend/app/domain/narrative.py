"""Audience expectations are editable design hypotheses, never psychological diagnoses."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.domain.quality import extract_numbers

AudienceProfile = Literal["academic", "executive", "technical", "investor", "learner", "custom"]
VisualKind = Literal["auto", "claim", "comparison", "process", "data", "image"]
Principle = Literal["cognitive_load", "signaling", "elaboration"]
ShortText = Annotated[str, Field(min_length=1, max_length=300)]

THEORIES = {
    "cognitive_load": {
        "label": "认知负荷",
        "application": "根据已有知识分段讲解；新术语先解释，每页围绕一个核心问题。",
        "citation": "Sweller (1988)",
        "url": "https://doi.org/10.1207/s15516709cog1202_4",
    },
    "signaling": {
        "label": "多媒体学习与重点提示",
        "application": "标题提示重点，图和解释就近对应；装饰不挤占证据的空间。",
        "citation": "Mayer & Moreno (2003)",
        "url": "https://doi.org/10.1207/S15326985EP3801_6",
    },
    "elaboration": {
        "label": "精细加工可能性",
        "application": "结合听众投入程度和知识基础安排论据深度；重要决策展示证据和反例。",
        "citation": "Petty & Cacioppo (1986)",
        "url": "https://doi.org/10.1016/S0065-2601(08)60214-2",
    },
}

PROFILES = {
    "academic": {
        "label": "学术评审",
        "description": "研究汇报、课程答辩、组会",
        "needs": ["问题是否清楚", "方法与证据是否可靠", "贡献和局限在哪里"],
        "arc": ["研究问题", "已有认识与缺口", "方法与取舍", "结果与证据", "贡献、局限与讨论"],
        "opening": "从明确的研究问题和重要性切入",
        "closing": "总结可支持的结论并提出讨论问题",
    },
    "executive": {
        "label": "管理者",
        "description": "工作汇报、资源申请、决策会议",
        "needs": ["需要做什么决定", "选项的收益、成本和风险", "负责人和下一步"],
        "arc": ["建议与待决事项", "关键事实", "方案对比", "风险和资源", "行动与验收"],
        "opening": "先呈现建议和需要决定的事项",
        "closing": "提出具体决策请求和下一步",
    },
    "technical": {
        "label": "技术同行",
        "description": "方案评审、工程分享、架构讨论",
        "needs": ["约束和失败条件", "架构取舍及替代方案", "可复现的验证方法"],
        "arc": ["约束与目标", "方案及替代方案", "关键机制", "验证与故障边界", "落地与开放问题"],
        "opening": "提出具体约束与技术难点",
        "closing": "明确适用边界和需要同行评审的决定",
    },
    "investor": {
        "label": "投资 / 业务评审",
        "description": "项目路演、商业提案、合作评审",
        "needs": ["谁有真实需求", "方案价值和验证程度", "商业假设、风险与资源需求"],
        "arc": ["具体需求场景", "价值主张", "验证证据", "商业假设与风险", "里程碑与合作请求"],
        "opening": "从有材料支持的需求场景切入",
        "closing": "区分已验证与待验证假设，提出合作请求",
    },
    "learner": {
        "label": "科普 / 教学听众",
        "description": "入门分享、培训、公众讲解",
        "needs": ["为什么与我有关", "关键概念是什么意思", "如何用一个例子理解或应用"],
        "arc": ["熟悉情境与问题", "必要概念", "分步解释", "例子与边界", "回顾与小练习"],
        "opening": "用熟悉的情境提出一个问题",
        "closing": "回顾要点并给出可尝试的问题或行动",
    },
    "custom": {
        "label": "自定义听众",
        "description": "混合听众或其他演讲情境",
        "needs": ["本次希望解决的问题", "判断所需的证据", "明确的下一步"],
        "arc": ["核心问题", "关键观点", "依据与限制", "下一步"],
        "opening": "根据用户的听众描述和目标选择切入点",
        "closing": "回到用户希望听众理解或采取的行动",
    },
}

STYLE_GUIDES = {
    "clean": "清晰简洁：统一对齐轴；一页一个重点；对比用两栏，流程用步骤，强调色只标识重点。",
    "editorial": "故事讲述：核心观点页和证据页形成节奏；允许大标题与留白，图文有明确关系。",
    "technical": "结构分析：用对照表和分步机制表达关系，保留必要术语、条件、数据单位与来源。",
}


class NarrativePlan(BaseModel):
    source: Literal["ai", "preset"] = "preset"
    audience_summary: str = Field(min_length=1, max_length=240)
    audience_needs: list[ShortText] = Field(min_length=1, max_length=5)
    throughline: str = Field(min_length=1, max_length=300)
    opening: str = Field(min_length=1, max_length=300)
    arc: list[ShortText] = Field(min_length=3, max_length=7)
    closing_action: str = Field(min_length=1, max_length=300)
    principles: list[Principle] = Field(default_factory=list, max_length=3)
    rationale: str = Field(min_length=1, max_length=600)
    assumptions: list[ShortText] = Field(default_factory=list, max_length=4)
    visual_strategy: str = Field(min_length=1, max_length=400)


def preset_plan(brief, audience: str | None = None) -> NarrativePlan:
    profile = PROFILES[brief.audience_profile]
    return NarrativePlan(
        audience_summary=audience or profile["label"],
        audience_needs=profile["needs"],
        throughline=brief.focus or "围绕本次目标组织已有事实，并保留证据与限制",
        opening=profile["opening"],
        arc=profile["arc"],
        closing_action=profile["closing"],
        principles=["cognitive_load", "signaling", "elaboration"],
        rationale="按演讲任务安排信息顺序；知识基础和用户补充要求优先于听众预设。",
        assumptions=["听众期望是可调整的设计假设，不代表对个体心理的测量。"],
        visual_strategy=STYLE_GUIDES[brief.visual_style],
    )


def semantic_skeleton(kind: VisualKind, *, has_data: bool, position: int) -> str:
    if kind == "data" and has_data:
        return "数据证据页：仅用来源中可追溯的数据形成 chart/table，标题给结论，注明单位和限制。"
    if kind == "comparison":
        return "对比页：row 两栏或 table；对齐相同评价维度，不补造未经提供的优劣评分。"
    if kind == "process":
        return "过程页：按来源顺序用 cards 或有序要点解释 2–4 步，讲清相邻步骤的关系。"
    # No numeric quota: lacking data must not cause an invented KPI or chart.
    if kind == "claim" or position % 2 == 0:
        return "观点页：column；一个重点标题与少量支撑要点，保持留白；无数据不生成 KPI 或图表。"
    return "证据解释页：row 两栏，一边结论，另一边材料依据或限制；无需为填满页面增加内容。"


def guard_plan_numbers(
    plan: NarrativePlan, baseline: NarrativePlan, source_text: str
) -> NarrativePlan:
    """Conservative guard for novel numeric targets; this is not semantic fact-checking."""
    allowed = set(extract_numbers(source_text, include_quantities=True))
    replacements = {}
    for field in (
        "audience_summary",
        "audience_needs",
        "throughline",
        "opening",
        "arc",
        "closing_action",
        "rationale",
        "assumptions",
        "visual_strategy",
    ):
        value = getattr(plan, field)
        texts = value if isinstance(value, list) else [value]
        if any(set(extract_numbers(text, include_quantities=True)) - allowed for text in texts):
            replacements[field] = getattr(baseline, field)
    if replacements:
        assumptions = replacements.get("assumptions", plan.assumptions)
        replacements["assumptions"] = assumptions[:3] + [
            "部分规划含材料未提供的数值，已改为预设建议；具体指标需由你确认。"
        ]
    return plan.model_copy(update=replacements)
