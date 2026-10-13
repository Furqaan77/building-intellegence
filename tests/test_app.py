import json

import pytest
from fastapi.testclient import TestClient

from building_with_rag.config import get_settings
from building_with_rag.main import app
from building_with_rag.registry import MODE_REGISTRY

_SECRET_ENV = [
    "MONGODB_URI",
    "VOYAGE_API_KEY",
    "CAPSTONE_API_KEY",
    "GENERATION_API_KEY",
    "RERANK_API_KEY",
]


@pytest.fixture
def client(monkeypatch):
    for name in _SECRET_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        "building_with_rag.config.Settings.model_config",
        {**get_settings().model_config, "env_file": None},
    )
    get_settings.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()


def test_healthz_is_safe(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert set(response.json()) == {"status", "app_env"}


def test_query_returns_placeholder(client):
    response = client.post("/v1/query", json={"question": "What is murder?", "pattern": "semantic"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_implemented"
    assert body["results"] == []


def test_query_rejects_invalid_input(client):
    response = client.post("/v1/query", json={"question": "", "pattern": "semantic"})
    assert response.status_code == 422


def test_models_lists_six_ids(client):
    ids = [m["id"] for m in client.get("/v1/models").json()["data"]]
    assert ids == list(MODE_REGISTRY.values())
    assert len(ids) == 6


def test_chat_json_and_sse(client):
    payload = {"model": "rag-semantic", "messages": [{"role": "user", "content": "hi"}]}
    plain = client.post("/v1/chat/completions", json=payload)
    assert plain.status_code == 200
    text = plain.json()["choices"][0]["message"]["content"]
    assert "not implemented" in text

    streamed = client.post(
        "/v1/chat/completions",
        json={
            **payload,
            "stream": True,
            "rag_options": {"pattern": "semantic", "filters": {"act": ["BNS"]}, "limit": 5},
        },
    )
    frames = [f for f in streamed.text.split("\n\n") if f]
    assert frames[-1] == "data: [DONE]"
    assert json.loads(frames[0][6:])["choices"][0]["delta"]["role"] == "assistant"
    assert json.loads(frames[-2][6:])["choices"][0]["finish_reason"] == "stop"


def test_chat_rejects_unknown_rag_option_with_openai_envelope(client):
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "rag-semantic",
            "messages": [{"role": "user", "content": "hi"}],
            "rag_options": {"access_level": "admin"},
        },
    )
    assert response.status_code == 400
    assert "error" in response.json()
