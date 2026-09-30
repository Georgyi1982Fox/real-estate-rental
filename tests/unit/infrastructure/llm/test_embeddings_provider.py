"""OpenAI-совместимый API embeddings (TASK-012)."""

import json

import httpx
import pytest
from tenacity import wait_none

from bina.application.ports.embeddings import EmbeddingsError
from bina.application.semantic_search import EMBEDDING_DIM
from bina.infrastructure.llm.providers.openai_embeddings_provider import OpenAIEmbeddingsProvider


def provider(
    handler: httpx.MockTransport, model: str = "text-embedding-3-small"
) -> OpenAIEmbeddingsProvider:
    client = httpx.AsyncClient(transport=handler)
    return OpenAIEmbeddingsProvider(
        "key", model=model, base_url="https://ai.test/v1/", client=client
    )


def answer(count: int) -> dict[str, object]:
    # Сервис вправе вернуть векторы не по порядку — порядок задаёт index
    return {
        "data": [
            {"index": index, "embedding": [float(index)] * EMBEDDING_DIM}
            for index in reversed(range(count))
        ]
    }


@pytest.fixture(autouse=True)
def no_retry_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(OpenAIEmbeddingsProvider._request.retry, "wait", wait_none())  # type: ignore[attr-defined]


async def test_batch_in_order() -> None:
    requests: list[dict[str, object]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://ai.test/v1/embeddings"
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(200, json=answer(len(body["input"])))

    vectors = await provider(httpx.MockTransport(handle)).embed(["a", "b", "c"])

    assert [vector[0] for vector in vectors] == [0.0, 1.0, 2.0]
    assert requests == [
        {"model": "text-embedding-3-small", "input": ["a", "b", "c"], "dimensions": EMBEDDING_DIM}
    ]


async def test_empty_input_makes_no_request() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request expected")

    assert await provider(httpx.MockTransport(handle)).embed([]) == []


async def test_retries_server_errors() -> None:
    attempts = []

    def handle(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) < 3:
            return httpx.Response(503)
        return httpx.Response(200, json=answer(1))

    assert len(await provider(httpx.MockTransport(handle)).embed(["a"])) == 1
    assert len(attempts) == 3


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401, json={"error": "bad key"}),
        httpx.Response(200, json={"data": []}),
        httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0, 2.0]}]}),
        httpx.Response(200, text="not json"),
        httpx.Response(500),
    ],
)
async def test_errors(response: httpx.Response) -> None:
    with pytest.raises(EmbeddingsError):
        await provider(httpx.MockTransport(lambda request: response)).embed(["a"])


async def test_other_models_get_no_dimensions() -> None:
    bodies: list[dict[str, object]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=answer(1))

    await provider(httpx.MockTransport(handle), model="custom").embed(["a"])
    assert "dimensions" not in bodies[0]


def test_factory_uses_translation_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from bina.infrastructure.llm.llm_factory import LLMFactory, embeddings_configured

    for name in ("EMBEDDINGS_API_KEY", "EMBEDDINGS_BASE_URL", "EMBEDDINGS_MODEL", "LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert not embeddings_configured()
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.aitunnel.ru/v1")
    assert embeddings_configured()
    embedder = LLMFactory.create_embeddings_provider()
    assert (embedder.base_url, embedder.model) == (
        "https://api.aitunnel.ru/v1",
        "text-embedding-3-small",
    )
    monkeypatch.setenv("EMBEDDINGS_MODEL", "text-embedding-3-large")
    assert LLMFactory.create_embeddings_provider().model == "text-embedding-3-large"
