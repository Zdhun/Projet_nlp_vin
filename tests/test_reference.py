"""Tests de cohérence des données de référence (lot 1). Lancer : pytest tests/"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reference import (enriched_text, load_blocks, load_food_pairing, load_wines,
                           pairing_text)


def test_five_blocks_with_enough_phrases():
    blocks = load_blocks()
    assert [b["id"] for b in blocks] == ["fruit", "spice_oak", "floral_mineral",
                                         "structure", "pairing"]
    for block in blocks:
        assert 6 <= len(block["phrases"]) <= 12, block["id"]
        assert block["weight"] > 0


def test_phrase_ids_unique_and_texts_filled():
    phrases = [p for b in load_blocks() for p in b["phrases"]]
    ids = [p["id"] for p in phrases]
    assert len(ids) == len(set(ids))
    assert all(p["text_en"].strip() and p["label_fr"].strip() for p in phrases)


def test_every_reference_variety_has_a_pairing():
    missing = set(load_wines()["variety"]) - set(load_food_pairing().index)
    assert not missing, f"Cépages sans accord : {missing}"


def test_pairing_lists_are_parsed():
    row = load_food_pairing().loc["Corvina, Rondinella, Molinara"]  # cépage avec virgules
    assert len(row["foods_en"]) == len(row["foods_fr"]) >= 3
    assert row["occasions_en"]


def test_pairing_and_enriched_text():
    assert pairing_text("Pinot Noir").startswith("Pairs well with salmon")
    assert pairing_text("Cépage inconnu") == ""
    wine = load_wines().iloc[0]
    text = enriched_text(wine)
    assert text.startswith(wine["description"]) and "Pairs well with" in text
