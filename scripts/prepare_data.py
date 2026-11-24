"""
Préparation des données de référence pour le système de recommandation de vins.

Source : Wine Reviews (Wine Enthusiast / winemag.com), publié sur Kaggle par zackthoutt
         (https://www.kaggle.com/datasets/zynicide/wine-reviews), licence CC BY-NC-SA 4.0.
         Miroir Hugging Face utilisé ici : spawn99/wine-reviews (fusion des versions 130k et 150k).

Étapes :
  1. Téléchargement des fichiers parquet depuis Hugging Face (si absents).
  2. Fusion des splits + suppression des doublons sur le texte de dégustation.
  3. Sauvegarde du corpus complet nettoyé  -> data/raw/winemag_reviews.csv.gz
  4. Ajout d'une colonne "color" (rouge / blanc / rosé / effervescent / doux) dérivée du cépage.
  5. Échantillon stratifié de référence      -> data/processed/wines_reference.csv

Usage : python scripts/prepare_data.py
"""

from pathlib import Path
import urllib.request

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
CACHE_DIR = ROOT / "data" / "cache"  # parquet téléchargés (non versionnés)

HF_BASE = "https://huggingface.co/datasets/spawn99/wine-reviews/resolve/main/data"
SPLITS = ["train", "validation", "test"]

RANDOM_STATE = 42
N_VARIETIES = 40          # nombre de cépages / assemblages retenus
PER_VARIETY = 15          # vins par cépage dans l'échantillon de référence
MIN_DESC_LEN = 150        # longueur minimale de la description (en caractères)

# --- Couleur / type de vin selon le cépage (règle transparente, documentée) ---
COLOR_BY_VARIETY = {
    # Rouges
    "Pinot Noir": "red", "Cabernet Sauvignon": "red", "Red Blend": "red",
    "Bordeaux-style Red Blend": "red", "Syrah": "red", "Merlot": "red",
    "Zinfandel": "red", "Sangiovese": "red", "Malbec": "red", "Nebbiolo": "red",
    "Portuguese Red": "red", "Tempranillo": "red", "Rhône-style Red Blend": "red",
    "Cabernet Franc": "red", "Shiraz": "red", "Grenache": "red", "Petite Sirah": "red",
    "Gamay": "red", "Carmenère": "red", "Barbera": "red", "Tempranillo Blend": "red",
    "Sangiovese Grosso": "red", "Pinotage": "red", "Primitivo": "red",
    "Aglianico": "red", "Nero d'Avola": "red", "Mourvèdre": "red",
    "Corvina, Rondinella, Molinara": "red", "Montepulciano": "red", "Garnacha": "red",
    "Petit Verdot": "red", "Cabernet Blend": "red", "Shiraz-Cabernet Sauvignon": "red",
    "Touriga Nacional": "red", "Dolcetto": "red", "Tannat": "red",
    # Blancs
    "Chardonnay": "white", "Sauvignon Blanc": "white", "Riesling": "white",
    "White Blend": "white", "Pinot Gris": "white", "Grüner Veltliner": "white",
    "Bordeaux-style White Blend": "white", "Pinot Grigio": "white", "Viognier": "white",
    "Gewürztraminer": "white", "Chenin Blanc": "white", "Portuguese White": "white",
    "Albariño": "white", "Pinot Blanc": "white", "Verdejo": "white",
    "Rhône-style White Blend": "white", "Sémillon": "white", "Torrontés": "white",
    "Vermentino": "white", "Garganega": "white", "Melon": "white", "Muscadet": "white",
    "Fiano": "white", "Moscato": "white", "Assyrtiko": "white",
    # Rosés
    "Rosé": "rose",
    # Effervescents
    "Sparkling Blend": "sparkling", "Champagne Blend": "sparkling", "Glera": "sparkling",
    "Prosecco": "sparkling",
    # Vins doux / mutés
    "Port": "dessert", "Sherry": "dessert", "Tokaji": "dessert",
}


def download_parquets() -> list[Path]:
    """Télécharge les splits parquet depuis Hugging Face s'ils ne sont pas déjà en cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for split in SPLITS:
        path = CACHE_DIR / f"{split}.parquet"
        if not path.exists():
            print(f"Téléchargement {split}…")
            urllib.request.urlretrieve(f"{HF_BASE}/{split}-00000-of-00001.parquet", path)
        paths.append(path)
    return paths


def load_and_clean(paths: list[Path]) -> pd.DataFrame:
    """Fusionne les splits, supprime les doublons et normalise les colonnes."""
    df = pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)
    n_before = len(df)

    # Les versions 130k et 150k du dataset se recouvrent : on déduplique sur le texte.
    # On trie pour garder en priorité les lignes qui ont un titre (version 130k plus riche).
    df = (df.assign(_has_title=df["title"].notna())
            .sort_values("_has_title", ascending=False)
            .drop_duplicates(subset=["description"])
            .drop(columns="_has_title"))

    # Nettoyage léger du texte (espaces superflus).
    df["description"] = df["description"].str.strip().str.replace(r"\s+", " ", regex=True)

    # Région la plus précise disponible.
    df["region"] = df["region_1"].fillna(df["province"])

    # Couleur dérivée du cépage, avec repli sur des indices textuels.
    df["color"] = df["variety"].map(COLOR_BY_VARIETY)
    v = df["variety"].str.lower()
    df.loc[df["color"].isna() & v.str.contains("red"), "color"] = "red"
    df.loc[df["color"].isna() & v.str.contains("white"), "color"] = "white"
    df.loc[df["color"].isna() & v.str.contains("sparkling"), "color"] = "sparkling"

    # Identifiant stable.
    df = df.sort_values(["country", "variety", "winery", "description"]).reset_index(drop=True)
    df.insert(0, "wine_id", [f"W{i:06d}" for i in range(len(df))])

    print(f"Lignes : {n_before} -> {len(df)} après déduplication")
    return df


def build_reference(df: pd.DataFrame) -> pd.DataFrame:
    """Échantillon stratifié par cépage : vins complets, descriptions riches, couleur connue."""
    eligible = df[
        df["title"].notna()
        & df["price"].notna()
        & df["color"].notna()
        & (df["description"].str.len() >= MIN_DESC_LEN)
    ]
    top_varieties = eligible["variety"].value_counts().head(N_VARIETIES).index
    ref = (eligible[eligible["variety"].isin(top_varieties)]
           .groupby("variety")
           .sample(n=PER_VARIETY, random_state=RANDOM_STATE))  # chaque cépage retenu a > 15 vins

    cols = ["wine_id", "title", "winery", "variety", "color", "country", "province",
            "region", "price", "points", "description"]
    return ref[cols].sort_values("wine_id").reset_index(drop=True)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df = load_and_clean(download_parquets())

    full_cols = ["wine_id", "title", "winery", "designation", "variety", "color", "country",
                 "province", "region_1", "region_2", "region", "price", "points",
                 "taster_name", "description"]
    df[full_cols].to_csv(RAW_DIR / "winemag_reviews.csv.gz", index=False, compression="gzip")
    print(f"Corpus complet : {len(df)} vins -> data/raw/winemag_reviews.csv.gz")

    ref = build_reference(df)
    ref.to_csv(PROCESSED_DIR / "wines_reference.csv", index=False)
    print(f"Référence : {len(ref)} vins, {ref['variety'].nunique()} cépages, "
          f"{ref['country'].nunique()} pays -> data/processed/wines_reference.csv")
    print(ref["color"].value_counts().to_string())


if __name__ == "__main__":
    main()
