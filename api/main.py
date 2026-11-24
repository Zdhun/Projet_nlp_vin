"""
API HTTP du système de recommandation (lot 4).

Expose le moteur sémantique Python (lots 1 à 3) à l'application web TypeScript (dossier web/).

  GET  /api/health      -> état du service
  GET  /api/options     -> listes du questionnaire (blocs, arômes, pays, couleurs, prix)
  POST /api/recommend   -> enregistre les réponses et renvoie le top 3 avec ses graphiques

Lancement : uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.embeddings import load_wine_embeddings
from src.explain import analyze_sentences, explain_recommendation
from src.recommender import recommend
from src.reference import ROOT, load_blocks, load_food_pairing, load_wines
from src.viz import radar_chart, ranking_chart, sentence_heatmap

RESPONSES_DIR = ROOT / "data" / "responses"

# --- Libellés affichés dans l'interface -------------------------------------------------

# Arômes proposés en cases à cocher : libellé FR -> mot-clé anglais présent dans les critiques
# (le bonus de préférences du lot 3 cherche ces mots dans la description du vin).
AROMAS = [
    {"id": "cherry", "label": "Cerise"}, {"id": "raspberry", "label": "Framboise"},
    {"id": "blackberry", "label": "Mûre"}, {"id": "plum", "label": "Prune"},
    {"id": "citrus", "label": "Agrumes"}, {"id": "apple", "label": "Pomme"},
    {"id": "peach", "label": "Pêche"}, {"id": "pineapple", "label": "Ananas"},
    {"id": "honey", "label": "Miel"}, {"id": "floral", "label": "Fleurs"},
    {"id": "herbal", "label": "Herbes"}, {"id": "mineral", "label": "Minéral"},
    {"id": "vanilla", "label": "Vanille"}, {"id": "pepper", "label": "Poivre"},
    {"id": "chocolate", "label": "Chocolat"}, {"id": "leather", "label": "Cuir"},
]

COUNTRY_FR = {
    "US": "États-Unis", "France": "France", "Italy": "Italie", "Portugal": "Portugal",
    "Spain": "Espagne", "Chile": "Chili", "Austria": "Autriche", "Australia": "Australie",
    "Argentina": "Argentine", "Germany": "Allemagne", "New Zealand": "Nouvelle-Zélande",
    "South Africa": "Afrique du Sud", "Israel": "Israël", "Greece": "Grèce",
    "Canada": "Canada", "Hungary": "Hongrie", "Bulgaria": "Bulgarie", "Romania": "Roumanie",
    "Uruguay": "Uruguay", "Mexico": "Mexique", "Slovenia": "Slovénie",
}

# Valeurs de couleur attendues par le filtre du lot 3 (src/recommender.py)
COLORS = [
    {"id": "peu importe", "label": "Peu importe", "key": "any"},
    {"id": "rouge", "label": "Rouge", "key": "red"},
    {"id": "blanc", "label": "Blanc", "key": "white"},
    {"id": "rosé", "label": "Rosé", "key": "rose"},
    {"id": "effervescent", "label": "Effervescent", "key": "sparkling"},
    {"id": "dessert", "label": "Doux", "key": "dessert"},
]


# --- Schéma des réponses du questionnaire ----------------------------------------------

Likert = Field(default=None, ge=1, le=5)


class Answers(BaseModel):
    """Réponses envoyées par le questionnaire web (mêmes clés que recommend() du lot 3)."""

    description: str = Field(min_length=3, max_length=1000)
    liked_wine_reason: str = Field(default="", max_length=1000)
    food_or_occasion: str = Field(default="", max_length=500)
    color: str = "peu importe"
    intensity_likert: int | None = Likert
    fruity_likert: int | None = Likert
    woody_likert: int | None = Likert
    sweetness_likert: int | None = Likert
    acidity_likert: int | None = Likert
    oak_tasted: Literal["yes", "no"] | None = None
    oak_liked: Literal["yes", "no"] | None = None
    aromas: list[str] = Field(default_factory=list, max_length=20)
    countries: list[str] = Field(default_factory=list, max_length=25)
    max_price: float = Field(default=50, gt=0, le=1000)


def to_engine_answers(a: Answers) -> dict:
    """Traduit les réponses web vers le format attendu par src.recommender.recommend()."""
    answers = a.model_dump(exclude={"oak_tasted", "oak_liked"})
    # Question guidée sur le boisé : le lot 3 lit "oui" / "non" dans ce texte libre,
    # et le texte rejoint aussi la requête sémantique.
    if a.oak_tasted == "yes" and a.oak_liked == "yes":
        answers["oaky_experience"] = "Oui, j'ai aimé les vins boisés."
    elif a.oak_tasted == "yes" and a.oak_liked == "no":
        answers["oaky_experience"] = "Non, je n'ai pas aimé les vins boisés."
    return answers


# --- Mise en forme des résultats -------------------------------------------------------

def _clean(value):
    """Remplace NaN par None et convertit les types numpy pour la sérialisation JSON."""
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        return _clean(value.item())
    return value


def _block_lookup() -> tuple[dict, dict]:
    """Correspondances nom FR du bloc -> id, et phrase anglaise -> (id bloc, libellé FR)."""
    by_name = {b["name_fr"]: b["id"] for b in load_blocks()}
    by_phrase = {p["text_en"]: (b["id"], p["label_fr"])
                 for b in load_blocks() for p in b["phrases"]}
    return by_name, by_phrase


def format_result(rank: int, item: dict) -> dict:
    """Résultat du moteur -> objet JSON consommé par l'interface."""
    by_name, by_phrase = _block_lookup()
    wine = {k: _clean(v) for k, v in item["wine"].items() if not k.startswith("_")}
    pairing = load_food_pairing()
    foods = pairing.loc[wine["variety"], "foods_fr"] if wine["variety"] in pairing.index else []

    reasons = []
    for match in item.get("matching_phrases", []):
        block_id, label = by_phrase.get(match["phrase"], (None, match["phrase"]))
        reasons.append({"block": block_id, "label": label,
                        "similarity": round(float(match["user_similarity"]), 3)})

    return {
        "rank": rank,
        "score": round(float(item["score"]), 4),
        "breakdown": {k: round(float(v), 4) for k, v in item["score_breakdown"].items()},
        "wine": {**wine, "country_fr": COUNTRY_FR.get(wine.get("country"), wine.get("country")),
                 "foods_fr": list(foods)},
        "user_blocks": {by_name.get(k, k): round(float(v), 4)
                        for k, v in item["user_block_profile"].items()},
        "wine_blocks": {by_name.get(k, k): round(float(v), 4)
                        for k, v in item["wine_block_profile"].items()},
        "reasons": reasons,
    }


# --- Application -----------------------------------------------------------------------

STATE: dict = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Préchargement : vins, embeddings en cache et modèle SBERT (premier appel lent).
    STATE["wines"] = load_wines()
    STATE["embeddings"] = load_wine_embeddings()
    recommend({"description": "warm-up"}, k=1, wines_df=STATE["wines"],
              wine_embeddings=STATE["embeddings"])
    yield


app = FastAPI(title="Recommandation de vins", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "wines": len(STATE.get("wines", []))}


@app.get("/api/options")
def options() -> dict:
    wines = load_wines()
    countries = wines["country"].value_counts()
    return {
        "blocks": [{"id": b["id"], "name": b["name_fr"]} for b in load_blocks()],
        "aromas": AROMAS,
        "colors": COLORS,
        "countries": [{"id": c, "label": COUNTRY_FR.get(c, c), "count": int(n)}
                      for c, n in countries.items()],
        "price": {"min": float(wines["price"].min()), "max": float(wines["price"].max()),
                  "median": float(wines["price"].median())},
        "wine_count": len(wines),
    }


@app.post("/api/recommend")
def recommend_endpoint(answers: Answers) -> dict:
    engine_answers = to_engine_answers(answers)
    # Un seul classement alimente les trois fiches et le graphique des cinq premiers.
    results = recommend(engine_answers, k=5, wines_df=STATE["wines"],
                        wine_embeddings=STATE["embeddings"])

    # Sauvegarde structurée de chaque réponse (exigence du sujet), sans donnée personnelle.
    response_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}_{uuid4().hex[:6]}"
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    formatted = [format_result(i + 1, r) for i, r in enumerate(results[:3])]
    record = {"id": response_id, "answers": answers.model_dump(),
              "results": [{"wine_id": r["wine"]["wine_id"], "score": r["score"]}
                          for r in formatted]}
    (RESPONSES_DIR / f"{response_id}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    if not formatted:
        raise HTTPException(status_code=404, detail="no_match")

    # Les explications et la heatmap partagent les mêmes similarités par phrase.
    analysis = analyze_sentences((
        answers.description,
        answers.liked_wine_reason,
        answers.food_or_occasion,
    ))
    for result, item in zip(formatted, results):
        result["explanation"] = explain_recommendation(item, analysis, answers.max_price)

    heatmap = sentence_heatmap(analysis)
    blocks = load_blocks()
    return {
        "id": response_id,
        "results": formatted,
        "analysis": {
            "radar": radar_chart(results[0]).to_plotly_json(),
            "ranking": ranking_chart(results).to_plotly_json(),
            "heatmap": heatmap.to_plotly_json() if heatmap is not None else None,
            "ranked_wines": [
                {"title": item["wine"]["title"], "score": round(float(item["score"]), 4)}
                for item in results
            ],
            "sentences": [
                {
                    "text": sentence,
                    "scores": {
                        block["id"]: round(float(analysis.block_scores[block["name_fr"]][i]), 4)
                        for block in blocks
                    },
                }
                for i, sentence in enumerate(analysis.sentences)
            ],
        },
    }
