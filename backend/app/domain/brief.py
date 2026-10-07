"""答辩需求独立于来源材料，不能被当作事实引用。"""

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.narrative import STYLE_GUIDES, AudienceProfile


class PresentationBrief(BaseModel):
    narrative_enabled: bool = False
    audience_profile: AudienceProfile = "custom"
    knowledge_level: Literal["auto", "newcomer", "familiar", "expert"] = "auto"
    narrative_overrides: str = Field(default="", max_length=1500)
    visual_style: Literal["clean", "editorial", "technical"] = "clean"
    scenario: Literal["general", "defense"] = "general"
    duration_minutes: int = Field(default=5, ge=1, le=60)
    focus: str = Field(default="", max_length=1000)


def brief_directive(brief: PresentationBrief) -> str:
    if brief.narrative_enabled:
        return (
            "按已规划的听众叙事组织内容，听众类别只是设计假设；用户明确要求优先。"
            f"总时长 {brief.duration_minutes} 分钟；重点：{brief.focus or '理解核心观点与证据'}。"
            f"听众知识基础：{brief.knowledge_level}；讲述要求：{brief.narrative_overrides}。"
            f"{STYLE_GUIDES[brief.visual_style]}"
            "每页围绕一个问题，用有依据的结论或问题作标题，不强制背景—问题—方案顺序。"
            "仅把来源材料当作事实，叙事方案、需求和大纲不是新增证据。"
            "没有数据不得编造 KPI、效果比例、市场规模或用户反馈；待验证的假设和计划须明确标记。"
            "图表只展示可追溯数值；信息不足时用简短文字或留白。"
            "speaker_notes 根据本页秒数写可口述讲稿，包含前后衔接；不要逐字重复屏幕全文。"
            "新听众先解释术语再给例子，专业听众聚焦机制、证据和边界。"
            "心理学原则用于表达设计，不得把某职业或人群描述为固定心理类型。"
        )
    if brief.scenario != "defense":
        return ""
    return (
        "项目答辩场景：按背景、问题、方案、实现、结果、不足组织叙事，"
        "可合并章节以适应页数。突出个人贡献，严格区分已完成与计划。"
        f"总时长 {brief.duration_minutes} 分钟；重点：{brief.focus or '问题、实现与证据'}。"
        "缺少实验、用户反馈、个人分工或成果数据时写【待补充】并提出具体补充项；"
        "不得虚构提升比例、用户数量或本人贡献。需求设置不属于事实证据。"
        "事实约束优先于字数、块数和版式饱满度：只根据 sections 中明确提供的事实写正文与讲稿；"
        "大纲只是组织提示，不能作为新增事实的依据。不得自行补写接口路径、测试用例数、"
        "功能细节、完成原因或工作先后顺序。资料少时保留简短内容和留白；"
        "缺失信息可写【待补充：具体需要的材料】，不得将建议或推测写成已完成的成果。"
    )
