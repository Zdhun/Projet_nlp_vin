"""
Chargement des données de référence : vins, blocs gustatifs et accords mets-vins.

Ce module est le point d'entrée commun aux autres lots (embeddings, scoring, interface) :
  - load_wines()          -> DataFrame des 600 vins de référence
  - load_blocks()         -> liste des 5 blocs gustatifs (phrases de référence)
  - load_food_pairing()   -> DataFrame cépage -> plats / occasions
  - pairing_text(variety) -> phrase anglaise décrivant les accords d'un cépage
  - enriched_text(wine)   -> description du vin + accords (texte utilisé pour le bloc "pairing")
"""

from functools import lru_cache
from pathlib import Path
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def _split(value: str) -> list[str]:
    """Découpe une cellule 'a; b; c' en liste ['a', 'b', 'c']."""
    return [item.strip() for item in str(value).split(";") if item.strip()]


@lru_cache(maxsize=1)
def load_wines() -> pd.DataFrame:
    """Jeu de référence de 600 vins (voir data/README.md)."""
    return pd.read_csv(PROCESSED / "wines_reference.csv")


@lru_cache(maxsize=1)
def load_blocks() -> list[dict]:
    """Blocs gustatifs : chaque bloc a un id, un nom FR, un poids et des phrases de référence."""
    with open(PROCESSED / "blocks.json", encoding="utf-8") as f:
        return json.load(f)["blocks"]


@lru_cache(maxsize=1)
def load_food_pairing() -> pd.DataFrame:
    """Table cépage -> plats (EN/FR) et occasions, indexée par cépage."""
    df = pd.read_csv(PROCESSED / "food_pairing.csv")
    for col in ["foods_en", "foods_fr", "occasions_en"]:
        df[col] = df[col].map(_split)
    return df.set_index("variety")


def pairing_text(variety: str) -> str:
    """Phrase en anglais décrivant les accords d'un cépage (chaîne vide si cépage inconnu).

    Exemple : "Pairs well with salmon, duck, roast chicken. Ideal for elegant dinner, casual dinner."
    """
    table = load_food_pairing()
    if variety not in table.index:
        return ""
    row = table.loc[variety]
    return (f"Pairs well with {', '.join(row['foods_en'])}. "
            f"Ideal for {', '.join(row['occasions_en'])}.")


def enriched_text(wine: pd.Series | dict) -> str:
    """Description du vin enrichie de ses accords.

    Les critiques citent rarement des plats (< 3 % des descriptions) : on ajoute donc
    les accords du cépage pour que le bloc "Accords mets et occasions" soit mesurable.
    """
    return f"{wine['description']} {pairing_text(wine['variety'])}".strip()
