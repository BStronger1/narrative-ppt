import logging
from typing import TypeVar

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from openai import APIConnectionError, APIStatusError, APITimeoutError
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings
from app.llm.errors import (
    InvalidModelOutputError,
    LLMAccessError,
    LLMNotConfiguredError,
    LLMRequestError,
    LLMServiceError,
    LLMTimeoutError,
)

T = TypeVar("T", bound=BaseModel)

# LCEL 负责一次结构化调用；有状态的校验/修复放在 LangGraph。
_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "{system}"),
        ("human", "{user}"),
    ]
)


def create_chat_model(settings: Settings | None = None, *, restricted: bool = False) -> ChatOpenAI:
    """用 ChatOpenAI 对接 DeepSeek 兼容接口，业务层不再持有 OpenAI SDK。"""
    cfg = settings or get_settings()
    kwargs: dict = {
        "model": cfg.llm_model,
        "api_key": cfg.llm_api_key or "not-configured",
        "base_url": cfg.llm_base_url,
        "timeout": httpx.Timeout(cfg.llm_timeout_seconds, connect=10),
        # 单次失败最多再请求一次，避免 SDK 与后台双层重试放大等待。
        "max_retries": 1,
    }
    if restricted:
        kwargs["http_client"] = httpx.Client(trust_env=False, follow_redirects=False)
        kwargs["http_async_client"] = httpx.AsyncClient(trust_env=False, follow_redirects=False)
    # 思考模式默认关闭；关闭时不要传 thinking，避免无谓地拉长延迟
    if cfg.llm_thinking_enabled:
        kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
    return ChatOpenAI(**kwargs)


class StructuredChatClient:
    """prompt | ChatOpenAI.with_structured_output(json_mode) 的薄封装。"""

    def __init__(self, *, model: BaseChatModel, api_key: str) -> None:
        self._model = model
        self._api_key = api_key

    async def complete(
        self,
        schema: type[T],
        *,
        system: str,
        user: str,
        purpose: str,
    ) -> T:
        if not self._api_key.strip():
            raise LLMNotConfiguredError(f"未配置 LLM API Key，无法{purpose}")

        chain = _PROMPT | self._model.with_structured_output(schema, method="json_mode")
        try:
            result = await chain.ainvoke({"system": system, "user": user})
        except (APITimeoutError, httpx.TimeoutException) as error:
            raise LLMTimeoutError("模型响应超时，请稍后重试或减少生成页数") from error
        except (APIConnectionError, httpx.NetworkError) as error:
            raise LLMServiceError("无法连接模型服务，请检查服务地址或稍后重试") from error
        except APIStatusError as error:
            if error.status_code in (401, 403):
                raise LLMAccessError("模型鉴权失败，请检查 API Key 和模型访问权限") from error
            if error.status_code == 429:
                raise LLMServiceError("模型服务限流或额度不足，请检查额度后重试") from error
            if error.status_code >= 500:
                raise LLMServiceError("模型服务暂时不可用，请稍后重试") from error
            raise LLMRequestError("模型服务拒绝请求，请检查模型名称和接口兼容性") from error
        except Exception as error:
            cause = error
            for _ in range(8):
                if isinstance(cause, ValidationError):
                    logging.getLogger(__name__).warning(
                        "Structured output validation: %s",
                        [
                            (item["loc"], item["type"])
                            for item in cause.errors(
                                include_input=False, include_context=False, include_url=False
                            )
                        ][:12],
                    )
                    break
                cause = cause.__cause__
                if cause is None:
                    break
            raise InvalidModelOutputError("模型返回内容不符合约定结构") from error

        if isinstance(result, schema):
            return result
        if isinstance(result, BaseModel):
            try:
                return schema.model_validate(result.model_dump())
            except ValidationError as error:
                raise InvalidModelOutputError("模型返回内容不符合约定结构") from error
        if isinstance(result, dict):
            try:
                return schema.model_validate(result)
            except ValidationError as error:
                raise InvalidModelOutputError("模型返回内容不符合约定结构") from error
        raise InvalidModelOutputError("模型返回内容不符合约定结构")
