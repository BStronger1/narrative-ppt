from fastapi import APIRouter

from app.domain.narrative import PROFILES, STYLE_GUIDES, THEORIES

router = APIRouter(tags=["presentation"])


@router.get("/presentation-presets")
async def presentation_presets():
    return {
        "profiles": [{"id": key, **value} for key, value in PROFILES.items()],
        "principles": THEORIES,
        "styles": STYLE_GUIDES,
        "note": "听众预设和心理学原则用于表达设计，不能预测个人偏好或保证说服效果。",
    }
