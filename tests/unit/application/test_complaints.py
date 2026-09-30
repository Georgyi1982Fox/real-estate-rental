"""Причины жалоб (TASK-106) на трёх языках."""

from bina.application.complaints import REASONS, Reason
from bina.application.localization import script_of


def test_reasons_in_every_language() -> None:
    assert set(REASONS) == set(Reason)
    for labels in REASONS.values():
        for language in ("ka", "ru", "en"):
            assert script_of(labels[language]) == language
