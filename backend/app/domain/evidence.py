"""引用校验只证明摘录存在，不把词句匹配描述为事实核验。"""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PointEvidence(BaseModel):
    point: str = Field(min_length=1, max_length=2000)
    kind: Literal["source", "inference", "missing"] = "missing"
    ref: str | None = Field(default=None, max_length=32)
    quote: str = Field(default="", max_length=800)

    @field_validator("quote", mode="before")
    @classmethod
    def empty_quote(cls, value):
        return "" if value is None else value


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", text)


def quote_exists(quote: str, text: str) -> bool:
    needle = normalized(quote)
    return len(needle) >= 4 and needle in normalized(text)


def sanitize_evidence(page, sections: dict, *, topic_refs: set[str] | None = None):
    """逐条要点绑定；旧大纲或无效引用保守地标为待补充。"""
    candidates = {item.point: item for item in page.point_evidence}
    evidence = []
    for point in page.key_points:
        item = candidates.get(point, PointEvidence(point=point))
        if item.kind == "source":
            source = sections.get(item.ref)
            if (
                source is None
                or item.ref in (topic_refs or set())
                or not quote_exists(item.quote, source.text)
            ):
                item = PointEvidence(point=point)
        if item.kind != "source":
            item = item.model_copy(update={"ref": None, "quote": ""})
        evidence.append(item)
    return page.model_copy(
        update={
            "point_evidence": evidence,
            "source_refs": list(
                dict.fromkeys(
                    [
                        *[ref for ref in page.source_refs if ref in sections],
                        *[item.ref for item in evidence if item.kind == "source" and item.ref],
                    ]
                )
            )[:10],
        }
    )
