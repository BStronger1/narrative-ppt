import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.db import async_session_factory
from app.main import app
from app.models.user import User
from app.services.user_models import decrypt_key, project_generator, validate_base_url

BASE = "/api/v1/model-settings"
KEY = "test-private-key-not-for-output"
CONFIG = {"base_url": "https://api.deepseek.com/v1", "model": "test-model", "api_key": KEY}


async def account(client):
    email = f"model-{uuid.uuid4().hex}@example.com"
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "test-password"}
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}, email


@pytest.mark.parametrize(
    "url",
    [
        "http://api.deepseek.com/v1",
        "https://127.0.0.1/v1",
        "https://api.deepseek.com.evil.test/v1",
        "https://evil@api.deepseek.com/v1",
        "https://api.deepseek.com:123/v1",
        "https://api.deepseek.com/v1?key=secret",
        "https://api.deepseek.com/v1#fragment",
    ],
)
def test_reject_untrusted_endpoints(url):
    with pytest.raises(ValueError):
        validate_base_url(url)


async def test_encrypted_account_isolation_and_key_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get(BASE)).status_code == 401
        owner, email = await account(client)
        other, _ = await account(client)
        payload = {k: v for k, v in CONFIG.items() if k != "api_key"}
        assert (await client.put(BASE, headers=owner, json=payload)).status_code == 422
        response = await client.put(BASE, headers=owner, json=CONFIG)
        assert response.status_code == 200
        assert KEY not in response.text and "encrypted_api_key" not in response.text
        assert response.json()["custom"]
        assert not (await client.get(BASE, headers=other)).json()["custom"]
        async with async_session_factory() as session:
            stored = (await session.scalar(select(User).where(User.email == email))).model_settings
            assert KEY not in str(stored)
            assert decrypt_key(stored["encrypted_api_key"]) == KEY
        payload["model"] = "another-model"
        assert (await client.put(BASE, headers=owner, json=payload)).status_code == 200
        payload["base_url"] = "https://api.openai.com/v1"
        assert (await client.put(BASE, headers=owner, json=payload)).status_code == 422
        assert not (await client.delete(BASE, headers=owner)).json()["has_api_key"]
        assert not (await client.get(BASE, headers=owner)).json()["custom"]


async def test_project_owner_controls_model_and_clients_close(monkeypatch):
    import app.services.user_models as service

    model = SimpleNamespace(
        root_async_client=SimpleNamespace(close=AsyncMock()),
        root_client=SimpleNamespace(close=Mock()),
    )
    build = Mock(return_value=model)
    monkeypatch.setattr(service, "create_chat_model", build)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        owner, _ = await account(client)
        other, _ = await account(client)
        await client.put(BASE, headers=owner, json=CONFIG)
        project = await client.post(
            "/api/v1/projects", headers=owner, json={"title": "Personal model"}
        )
        project_id = uuid.UUID(project.json()["id"])
        default_project = await client.post(
            "/api/v1/projects", headers=other, json={"title": "Default model"}
        )
        factory = Mock(return_value="personal-generator")
        async with project_generator(project_id, factory, "global-generator") as generator:
            assert generator == "personal-generator"
            cfg = factory.call_args.kwargs["settings"]
            assert cfg.llm_api_key == KEY and cfg.llm_model == "test-model"
            assert not cfg.demo_mode
        assert build.call_args.kwargs["restricted"] is True
        model.root_async_client.close.assert_awaited_once()
        model.root_client.close.assert_called_once()
        async with project_generator(
            uuid.UUID(default_project.json()["id"]), factory, "global-generator"
        ) as generator:
            assert generator == "global-generator"
        assert factory.call_count == 1


async def test_provider_errors_never_echo_credentials(monkeypatch):
    import app.api.v1.model_settings as routes

    model = SimpleNamespace(
        root_async_client=SimpleNamespace(close=AsyncMock()),
        root_client=SimpleNamespace(close=Mock()),
    )
    monkeypatch.setattr(routes, "create_chat_model", lambda *args, **kwargs: model)
    monkeypatch.setattr(
        routes.StructuredChatClient, "complete", AsyncMock(side_effect=RuntimeError(KEY))
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        owner, _ = await account(client)
        response = await client.post(BASE + "/test", headers=owner, json=CONFIG)
        assert response.status_code == 422 and KEY not in response.text
    model.root_async_client.close.assert_awaited_once()
