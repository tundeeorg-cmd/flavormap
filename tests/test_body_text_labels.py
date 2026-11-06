"""scripts/apply_body_text_labels.py: HD-37 rule 3, region labels from body text read by
hand. Pure planning only; synthetic rows."""

from __future__ import annotations

import pytest

from scripts.apply_body_text_labels import OWNED, BodyLabel, confirmed_labels


def _row(page: str, region: str, ids: str, verdict: str) -> dict[str, str]:
    return {"page_id": page, "region": region, "region_term": "อีสาน",
            "loaded_recipe_ids": ids, "genuine_dish_claim": verdict}


def test_only_confirmed_pages_label_their_loaded_recipes() -> None:
    labels = confirmed_labels([_row("v1", "Northeast", "10 11", "yes"),
                               _row("v2", "South", "12", "no"),
                               _row("v3", "North", "", "yes"),
                               _row("v4", "North", "13", "")])
    assert labels == [BodyLabel(10, "Northeast", "v1", "อีสาน"),
                      BodyLabel(11, "Northeast", "v1", "อีสาน")]


def test_a_recipe_two_confirmed_pages_disagree_on_gets_no_label() -> None:
    labels = confirmed_labels([_row("v1", "Northeast", "10", "yes"),
                               _row("v2", "South", "10 11", "yes")])
    assert [lab.recipe_id for lab in labels] == [11]


def test_an_unknown_region_is_refused() -> None:
    with pytest.raises(ValueError, match="not one of"):
        confirmed_labels([_row("v1", "Isan", "10", "yes")])


def test_owned_prefix_does_not_collide_with_the_title_rules() -> None:
    from scripts.apply_labels import OWNED as TITLE_OWNED
    assert not OWNED.startswith(TITLE_OWNED) and not TITLE_OWNED.startswith(OWNED)
