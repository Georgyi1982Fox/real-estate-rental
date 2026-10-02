"""AI-анализ фото квартиры (TASK-114): запрос с картинками и разбор ответа."""

import json
from pathlib import Path

import httpx
import pytest

from bina.application.ports.photo_analyzer import PhotoAnalysisError
from bina.infrastructure.llm.photo_analyzer import LLMPhotoAnalyzer, image_url, parse_report

GOOD = {
    "level": "needs_repair",
    "issues": ["mold", "cracks", "mold", "spaceship"],
    "summary": {"ru": "Старый ремонт.", "en": "Old renovation.", "ka": "ძველი რემონტი."},
}


def reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_parse_report_keeps_known_codes_once() -> None:
    report = parse_report("Here: " + json.dumps(GOOD))
    assert report.level == "needs_repair"
    assert report.issues == ("mold", "cracks")
    assert report.summary["ka"] == "ძველი რემონტი."


@pytest.mark.parametrize("raw", ["no json", json.dumps({**GOOD, "level": "perfect"})])
def test_parse_report_rejects_bad_answers(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_report(raw)


def test_image_url(tmp_path: Path) -> None:
    (tmp_path / "abc").mkdir()
    (tmp_path / "abc" / "1.jpg").write_bytes(b"\xff\xd8jpeg")
    assert image_url("https://cdn.ss.ge/1.jpg", tmp_path) == "https://cdn.ss.ge/1.jpg"
    assert image_url("/api/media/abc/1.jpg", tmp_path) == "data:image/jpeg;base64,/9hqcGVn"
    assert image_url("/api/media/../../etc/passwd", tmp_path) is None
    assert image_url("/api/media/abc/none.jpg", tmp_path) is None


async def test_sends_up_to_four_low_detail_photos_and_retries_bad_reply() -> None:
    bodies: list[dict[str, object]] = []
    replies = iter([reply("not json"), reply(json.dumps(GOOD))])

    def handle(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return next(replies)

    analyzer = LLMPhotoAnalyzer(
        "key",
        base_url="https://ai.test/v1",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
    )
    images = [f"https://cdn.test/{n}.jpg" for n in range(9)]
    report = await analyzer.analyze(images)

    assert report.level == "needs_repair"
    assert len(bodies) == 2
    content = bodies[0]["messages"][0]["content"]  # type: ignore[index]
    pictures = [part for part in content if part["type"] == "image_url"]
    assert [p["image_url"]["url"] for p in pictures] == images[:4]
    assert {p["image_url"]["detail"] for p in pictures} == {"low"}
    assert bodies[0]["model"] == "gpt-4o-mini"


async def test_service_error_and_no_photos() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="down")

    analyzer = LLMPhotoAnalyzer(
        "key", client=httpx.AsyncClient(transport=httpx.MockTransport(down))
    )
    with pytest.raises(PhotoAnalysisError):
        await analyzer.analyze(["https://cdn.test/1.jpg"])
    with pytest.raises(PhotoAnalysisError):
        await analyzer.analyze(["relative.jpg"])
