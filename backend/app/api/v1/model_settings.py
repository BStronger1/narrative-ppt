from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_session
from app.llm.client import StructuredChatClient, create_chat_model
from app.llm.errors import LLMNotConfiguredError
from app.models.user import User
from app.services.user_models import close_model, decrypt_key, encrypt_key, validate_base_url

router = APIRouter(prefix="/model-settings", tags=["model-settings"])
CurrentUser = Annotated[User, Depends(get_current_user)]
Session = Annotated[AsyncSession, Depends(get_session)]


class ModelSettingsInput(BaseModel):
    base_url: str = Field(min_length=1, max_length=500)
    model: str = Field(min_length=1, max_length=200)
    api_key: SecretStr | None = None


class ModelSettingsPublic(BaseModel):
    custom: bool
    base_url: str
    model: str
    has_api_key: bool
    default_available: bool
    allowed_hosts: list[str]


def public_settings(user):
    settings = get_settings()
    stored = user.model_settings or {}
    return ModelSettingsPublic(
        custom=bool(stored),
        base_url=stored.get("base_url", settings.llm_base_url),
        model=stored.get("model", settings.llm_model),
        has_api_key=bool(stored.get("encrypted_api_key")),
        default_available=bool(settings.llm_api_key) or settings.demo_mode,
        allowed_hosts=settings.model_api_allowed_hosts,
    )


def credentials(body, user):
    try:
        base_url = validate_base_url(body.base_url)
        model = body.model.strip()
        if not model:
            raise ValueError("请填写模型名称")
        key = body.api_key.get_secret_value().strip() if body.api_key is not None else None
        if key is None:
            stored = user.model_settings or {}
            if stored.get("base_url") != base_url or not stored.get("encrypted_api_key"):
                raise ValueError("首次配置或更换服务地址时，请填写自己的 API Key")
            key = decrypt_key(stored["encrypted_api_key"])
        if not key or len(key) > 4096 or any(char.isspace() for char in key):
            raise ValueError("API Key 不能为空或包含空白字符")
        return base_url, model, key
    except (ValueError, LLMNotConfiguredError) as error:
        raise HTTPException(422, str(error)) from None


@router.get("", response_model=ModelSettingsPublic)
async def read_settings(user: CurrentUser):
    return public_settings(user)


@router.put("", response_model=ModelSettingsPublic)
async def save_settings(body: ModelSettingsInput, user: CurrentUser, session: Session):
    base_url, model, key = credentials(body, user)
    user.model_settings = {
        "base_url": base_url,
        "model": model,
        "encrypted_api_key": encrypt_key(key),
    }
    await session.commit()
    return public_settings(user)


@router.delete("", response_model=ModelSettingsPublic)
async def reset_settings(user: CurrentUser, session: Session):
    user.model_settings = {}
    await session.commit()
    return public_settings(user)


class Probe(BaseModel):
    ok: bool


@router.post("/test")
async def test_settings(body: ModelSettingsInput, user: CurrentUser):
    base_url, model_name, key = credentials(body, user)
    cfg = get_settings().model_copy(
        update={
            "llm_base_url": base_url,
            "llm_model": model_name,
            "llm_api_key": key,
            "llm_thinking_enabled": False,
            "llm_timeout_seconds": 30,
        }
    )
    model = create_chat_model(cfg, restricted=True)
    try:
        result = await StructuredChatClient(model=model, api_key=key).complete(
            Probe,
            system='Return only JSON: {"ok":true}',
            user="Verify JSON output.",
            purpose="测试连接",
        )
        if not result.ok:
            raise ValueError("Probe failed")
        return {"ok": True, "message": "连接成功，模型支持 JSON 输出"}
    except Exception:
        raise HTTPException(422, "连接测试失败，请核对地址、模型权限、密钥和额度") from None
    finally:
        await close_model(model)


@router.post("/models")
async def list_models(body: ModelSettingsInput, user: CurrentUser):
    base_url, _, key = credentials(body, user)
    try:
        async with httpx.AsyncClient(timeout=20, trust_env=False, follow_redirects=False) as client:
            response = await client.get(
                base_url + "/models", headers={"Authorization": f"Bearer {key}"}
            )
            response.raise_for_status()
            models = sorted(
                {
                    item["id"]
                    for item in response.json().get("data", [])
                    if isinstance(item, dict) and isinstance(item.get("id"), str)
                }
            )
        return {"models": models[:500]}
    except Exception:
        raise HTTPException(422, "暂时无法获取模型列表，可以手动填写服务商提供的模型名称") from None
