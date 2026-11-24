from pathlib import Path
from src.recommender import recommend


def main() -> None:
    # Vérifie que les fichiers clés sont bien présents
    blocks_path = Path("data/processed/blocks.json")
    print("blocks.json existe :", blocks_path.exists())

    cache_files = list(Path("data/cache").glob("*")) if Path("data/cache").exists() else []
    print("Fichiers dans data/cache :", [p.name for p in cache_files])

    # Exemple de réponses utilisateur représentatives
    user_answers = {
        "description": "Je cherche un vin rouge fruité et frais, facile à boire",
        "liked_wine_reason": "J'avais beaucoup aimé un vin rouge léger avec des fruits rouges",
        "food_or_occasion": "apéro ou volaille rôtie",
        "color": "rouge",
        "max_price": 30.0,
        "countries": ["France"],
        "aromas": ["cherry"],
        "intensity_likert": 2,
        "fruity_likert": 4,
        "woody_likert": 2,
        "acidity_likert": 4,
    }

    top_3 = recommend(user_answers, k=3)
    print(f"\nNombre de recommandations : {len(top_3)}")

    for rank, item in enumerate(top_3, start=1):
        wine = item["wine"]
        # Adapte ces clés si besoin selon les colonnes exactes du CSV des vins
        nom = (
            wine.get("title")
            or wine.get("name")
            or wine.get("variety")
            or wine.get("wine")
            or f"Vin #{rank}"
        )
        prix = wine.get("price") or wine.get("prix") or "?"
        couleur = wine.get("color") or wine.get("couleur") or "?"

        print(f"\n--- Top {rank} : {nom} ({couleur}, {prix}) | Score : {item['score']:.4f} ---")
        print("Détail des scores :", {k: round(v, 4) for k, v in item["score_breakdown"].items()})
        print("Profil blocs vin :", {k: round(v, 4) for k, v in item["wine_block_profile"].items()})
        print("Meilleures phrases :", item["matching_phrases"])


if __name__ == "__main__":
    main()