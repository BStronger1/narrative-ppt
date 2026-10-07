"""Account-scoped model selection. Credentials never enter queue payloads or responses."""

import base64
import hashlib
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import async_session_factory
from app.llm.client import create_chat_model
from app.llm.errors import LLMNotConfiguredError
from app.models.project import Project
from app.models.user import User


def validate_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    try:
        url = urlsplit(value)
        valid = (
            url.scheme == "https"
            and url.hostname in get_settings().model_api_allowed_hosts
            and url.port in (None, 443)
            and not url.username
            and not url.password
            and not url.query
            and not url.fragment
            and "\\" not in value
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("请使用支持的 HTTPS 服务地址；其他服务需由管理员添加支持")
    return value


def cipher():
    settings = get_settings()
    secret = settings.model_config_secret or settings.jwt_secret
    key = hashlib.sha256(("aippt-user-model-v1:" + secret).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_key(value: str) -> str:
    return cipher().encrypt(value.encode()).decode()


def decrypt_key(value: str) -> str:
    try:
        return cipher().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError, UnicodeError) as error:
        raise LLMNotConfiguredError("个人密钥已失效，请到模型设置重新填写") from error


def resolve_settings(stored: dict):
    try:
        base_url = validate_base_url(stored["base_url"])
        key = decrypt_key(stored["encrypted_api_key"])
        model = stored["model"]
    except (KeyError, ValueError) as error:
        raise LLMNotConfiguredError("个人模型配置不可用，请到模型设置重新保存") from error
    return get_settings().model_copy(
        update={
            "llm_api_key": key,
            "llm_base_url": base_url,
            "llm_model": model,
            "demo_mode": False,
            "llm_thinking_enabled": False,
        }
    )


async def close_model(model):
    async_client = getattr(model, "root_async_client", None)
    if async_client is not None:
        await async_client.close()
    sync_client = getattr(model, "root_client", None)
    if sync_client is not None:
        sync_client.close()


@asynccontextmanager
async def project_generator(project_id, factory, fallback=None):
    async with async_session_factory() as session:
        stored = await session.scalar(
            select(User.model_settings)
            .join(Project, Project.user_id == User.id)
            .where(Project.id == project_id)
        )
    if not stored:
        yield fallback if fallback is not None else factory()
        return
    cfg = resolve_settings(stored)
    model = create_chat_model(cfg, restricted=True)
    try:
        yield factory(model=model, settings=cfg)
    finally:
        await close_model(model)
