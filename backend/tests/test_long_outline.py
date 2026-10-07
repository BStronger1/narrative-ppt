import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import httpx
import pytest
from langchain_core.runnables import RunnableLambda
from openai import APIStatusError, APITimeoutError

from app.core.config import Settings
from app.domain.brief import PresentationBrief
from app.domain.narrative import preset_plan
from app.domain.outline import OutlineDraft, OutlinePageDraft
from app.llm.base import OutlineGenerationInput, OutlineSourceSection
from app.llm.client import StructuredChatClient, create_chat_model
from app.llm.deepseek import DeepSeekOutlineGenerator, OutlineHeading, OutlineStructure
from app.llm.errors import (
    InvalidOutlineOutputError,
    LLMAccessError,
    LLMRequestError,
    LLMServiceError,
    LLMTimeoutError,
)
from app.worker.retry import retry_after_failure
from app.worker.tasks import _public_error
from app.workflows.outline import build_outline_workflow, run_outline_workflow


def payload(count):
    brief = PresentationBrief(narrative_enabled=True, duration_minutes=1)
    return OutlineGenerationInput(
        title="长页数验收",
        audience="评审",
        tone="professional",
        page_count=count,
        brief=brief,
        narrative=preset_plan(brief),
        sections=[OutlineSourceSection(ref="S1:1", level=1, text="已完成基础验证", locator="p1")],
    )


class BatchChat:
    def __init__(self, count, fail=False, wrong_count=False, bad_ref=False):
        self.count, self.fail = count, fail
        self.wrong_count, self.bad_ref = wrong_count, bad_ref
        self.active = self.peak = self.cancelled = 0
        self.completed = []
        self.contexts = []
        self.later_done = asyncio.Event()

    async def complete(self, schema, *, system, user, purpose):
        if schema is OutlineStructure:
            return OutlineStructure(
                pages=[
                    OutlineHeading(
                        title=f"主题 {i}",
                        objective="阐述证据边界",
                        page_role="cover"
                        if i == 1
                        else "summary"
                        if i == self.count
                        else "content",
                    )
                    for i in range(1, self.count + 1)
                ]
            )
        context, _ = json.JSONDecoder().raw_decode(user.split("本批页码与全篇上下文：")[1])
        self.contexts.append(context)
        start, end = context["start_page"], context["end_page"]
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            if self.fail and start > 1:
                raise LLMTimeoutError("模型响应超时")
            if start == 1:
                await self.later_done.wait()
            self.completed.append(start)
            if start > 1:
                self.later_done.set()
            return OutlineDraft(
                pages=[
                    OutlinePageDraft(
                        title=f"批内标题 {i}",
                        objective="解释证据",
                        key_points=["已完成基础验证", "其余尚待验证"],
                        layout_id="bullets",
                        source_refs=["invented" if self.bad_ref else "S1:1"],
                        narrative_role="解释证据",
                    )
                    for i in range(start, end + (0 if self.wrong_count else 1))
                ]
            )
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
        finally:
            self.active -= 1


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [6, 10, 15, 20, 21, 40])
async def test_batches_preserve_global_order_count_references_and_time(count):
    chat = BatchChat(count)
    generator = DeepSeekOutlineGenerator(chat=chat, layout_ids=frozenset({"bullets"}))
    # 单独验证生成与公共工作流分配，避免测试桩吞掉 AI 规划错误。
    draft = await generator.generate(payload(count))
    assert [p.title for p in draft.pages] == [f"主题 {i}" for i in range(1, count + 1)]
    assert [p.page_role for p in draft.pages].count("cover") == 1
    assert [p.page_role for p in draft.pages].count("summary") == 1
    assert all(p.source_refs == ["S1:1"] for p in draft.pages)
    assert chat.active == 0 and chat.peak <= 2
    assert all(c["end_page"] - c["start_page"] < 5 for c in chat.contexts)
    assert all(len(c["full_structure"]) == count for c in chat.contexts)
    assert chat.completed[0] != 1  # 即使后批先完成，合并页序仍正确

    class PreparedGenerator:
        async def generate(self, _):
            return draft

    result = await run_outline_workflow(build_outline_workflow(PreparedGenerator()), payload(count))
    assert sum(p.speaker_seconds for p in result.pages) == 60
    assert all(p.speaker_seconds >= 1 for p in result.pages)


@pytest.mark.asyncio
async def test_failed_batch_cancels_other_requests_and_preserves_timeout_type():
    chat = BatchChat(20, fail=True)
    with pytest.raises(LLMTimeoutError):
        await DeepSeekOutlineGenerator(chat=chat).generate(payload(20))
    assert chat.active == 0 and chat.cancelled >= 1


@pytest.mark.asyncio
@pytest.mark.parametrize("option", ["wrong_count", "bad_ref"])
async def test_invalid_batch_is_rejected_before_merge(option):
    chat = BatchChat(10, **{option: True})
    with pytest.raises(InvalidOutlineOutputError):
        await DeepSeekOutlineGenerator(chat=chat).generate(payload(10))
    assert chat.active == 0


@pytest.mark.asyncio
async def test_only_invalid_batch_is_regenerated_once():
    class RecoverableChat(BatchChat):
        async def complete(self, schema, *, system, user, purpose):
            result = await super().complete(schema, system=system, user=user, purpose=purpose)
            if schema is OutlineDraft and self.completed.count(6) == 1 and self.completed[-1] == 6:
                return OutlineDraft(pages=result.pages[:-1])
            return result

    chat = RecoverableChat(10)
    result = await DeepSeekOutlineGenerator(chat=chat).generate(payload(10))
    assert len(result.pages) == 10
    assert chat.completed.count(1) == 1
    assert chat.completed.count(6) == 2


class FailingModel:
    def __init__(self, error):
        self.error = error

    def with_structured_output(self, *args, **kwargs):
        async def fail(_):
            raise self.error

        return RunnableLambda(fail)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,expected,retryable",
    [
        (None, LLMTimeoutError, True),
        (401, LLMAccessError, False),
        (403, LLMAccessError, False),
        (400, LLMRequestError, False),
        (429, LLMServiceError, True),
        (503, LLMServiceError, True),
    ],
)
async def test_transport_errors_are_not_mislabeled_as_json_or_leaked(status, expected, retryable):
    request = httpx.Request("POST", "https://example.com/v1/chat/completions")
    error = (
        APITimeoutError(request=request)
        if status is None
        else APIStatusError(
            "private-key-and-body",
            response=httpx.Response(status, request=request),
            body={"private": "input"},
        )
    )
    chat = StructuredChatClient(model=FailingModel(error), api_key="private-key")
    with pytest.raises(expected) as caught:
        await chat.complete(OutlineDraft, system="system", user="user", purpose="生成大纲")
    assert "private" not in _public_error(caught.value)
    assert "JSON" not in _public_error(caught.value)
    assert (retry_after_failure({"job_try": 1}, caught.value) is not None) == retryable
    assert retry_after_failure({"job_try": 2}, caught.value) is None


def test_timeout_and_retry_budget_apply_to_custom_model_clients():
    model = create_chat_model(
        Settings(llm_api_key="test-key", llm_timeout_seconds=180), restricted=True
    )
    assert model.root_async_client.timeout.read == 180
    assert model.root_async_client.timeout.connect == 10
    assert model.max_retries == 1


@pytest.mark.asyncio
async def test_outline_deadline_settles_failed_state(monkeypatch):
    from app.worker import tasks

    @asynccontextmanager
    async def generator(*args):
        yield object()

    async def deadline(coro, timeout):
        assert timeout < 900
        coro.close()
        raise TimeoutError

    saved = AsyncMock()
    monkeypatch.setattr(
        tasks, "_load_generation_input", AsyncMock(return_value=(payload(20), "sig", 0))
    )
    monkeypatch.setattr(tasks, "_progress", AsyncMock())
    monkeypatch.setattr(tasks, "project_generator", generator)
    monkeypatch.setattr(tasks, "_save_failed", saved)
    monkeypatch.setattr(tasks.asyncio, "wait_for", deadline)
    await tasks.generate_outline({"job_try": 2}, str(uuid.uuid4()), "deadline-job")
    assert "超时" in saved.call_args.args[2]
