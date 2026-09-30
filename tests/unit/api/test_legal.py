"""``GET /api/legal/{doc}`` (TASK-089): без авторизации, на выбранном языке."""

from httpx import AsyncClient


async def test_terms_in_georgian_by_default(client: AsyncClient) -> None:
    response = await client.get("/api/legal/terms")
    assert response.status_code == 200
    body = response.json()
    assert body["doc"] == "terms"
    assert body["language"] == "ka"
    assert body["title"].startswith("Bina.ai")
    assert body["version"] == "2026-09-30"
    assert len(body["sections"]) == 7


async def test_privacy_in_english(client: AsyncClient) -> None:
    body = (await client.get("/api/legal/privacy", params={"lang": "en"})).json()
    assert body["title"] == "Bina.ai Privacy Policy"
    assert body["version_label"] == "Version of 30.09.2026"


async def test_unknown_document_or_language(client: AsyncClient) -> None:
    assert (await client.get("/api/legal/cookies")).status_code == 422
    assert (await client.get("/api/legal/terms", params={"lang": "de"})).status_code == 422
