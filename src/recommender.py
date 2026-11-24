"""
src/recommender.py
------------------
Orchestration de la recommandation de vins par analyse sémantique :
- Chargement des données, embeddings et profils de blocs (avec cache disque)
- Application des filtres durs (budget max, couleur imposée)
- Calcul des scores (normalisation min-max + formule 0.6 / 0.3 / 0.1)
- Retour du top k expliqué par blocs et phrases correspondantes
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.scoring import (
    block_affinity,
    block_profile_from_embedding,
    compute_preferences_bonus,
    cosine_similarity_matrix,
    extract_blocks_mapping,
    normalize_minmax,
    precompute_block_phrase_embeddings,
    wine_score,
)


DEFAULT_WEIGHTS: Tuple[float, float, float] = (0.6, 0.3, 0.1)


def _project_root() -> Path:
    """Retourne la racine du dépôt (parent de `src/`)."""
    return Path(__file__).resolve().parent.parent


def _load_blocks_fallback(blocks_path: Path) -> Dict[str, List[str]]:
    """Charge `data/processed/blocks.json` si `src.reference` n'expose pas de helper."""
    with blocks_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return extract_blocks_mapping(raw)


def _load_wines_fallback(data_dir: Path) -> pd.DataFrame:
    """Charge le jeu de données des vins depuis `data/processed/` ou `data/`."""
    candidates = [
        data_dir / "processed" / "wines_600.csv",
        data_dir / "processed" / "wines.csv",
        data_dir / "wines_600.csv",
        data_dir / "wines.csv",
    ]
    for path in candidates:
        if path.exists():
            return pd.read_csv(path)

    for csv_path in data_dir.rglob("*.csv"):
        if "food_pairing" not in csv_path.name:
            return pd.read_csv(csv_path)

    raise FileNotFoundError(f"Aucun fichier CSV de vins trouvé dans {data_dir}")


def _load_wine_embeddings_fallback(
    cache_dir: Path,
    wines_df: pd.DataFrame,
    encode_fn: Callable[[List[str]], np.ndarray],
) -> np.ndarray:
    """
    Charge les embeddings des vins depuis `data/cache/` si présents,
    sinon les calcule à partir de la colonne textuelle et les met en cache.
    """
    cache_file = cache_dir / "wine_embeddings.npy"
    if cache_file.exists():
        emb = np.load(cache_file)
        if len(emb) == len(wines_df):
            return np.asarray(emb, dtype=np.float32)

    # Recherche d'autres fichiers .npy plausibles dans data/cache
    for npy_path in sorted(cache_dir.glob("*.npy")):
        if "block" in npy_path.name:
            continue
        arr = np.load(npy_path)
        if arr.ndim == 2 and len(arr) == len(wines_df):
            return np.asarray(arr, dtype=np.float32)

    text_col = next(
        (c for c in ("description", "text", "review", "full_text", "title") if c in wines_df.columns),
        None,
    )
    if text_col is None:
        raise ValueError("Impossible de trouver une colonne de description pour encoder les vins.")

    texts = wines_df[text_col].fillna("").astype(str).tolist()
    emb = np.asarray(encode_fn(texts), dtype=np.float32)
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache_file, emb)
    return emb


def get_or_compute_wine_block_profiles(
    wine_embeddings: np.ndarray,
    blocks_mapping: Dict[str, List[str]],
    encode_fn: Callable[[List[str]], np.ndarray],
    cache_dir: Optional[Path] = None,
    force_recompute: bool = False,
) -> Tuple[List[Dict[str, float]], Dict[str, Tuple[List[str], np.ndarray]]]:
    """
    Calcule une fois pour toutes les profils par bloc des 600 vins et les met en cache
    dans `data/cache/wine_block_profiles.json`.
    """
    root = _project_root()
    cache_path = (cache_dir or (root / "data" / "cache")) / "wine_block_profiles.json"

    block_phrase_embs = precompute_block_phrase_embeddings(blocks_mapping, encode_fn)
    block_names = list(block_phrase_embs.keys())

    if not force_recompute and cache_path.exists():
        with cache_path.open("r", encoding="utf-8") as f:
            cached = json.load(f)
        if (
            isinstance(cached, dict)
            and cached.get("block_names") == block_names
            and isinstance(cached.get("profiles"), list)
            and len(cached["profiles"]) == len(wine_embeddings)
        ):
            profiles = [
                {k: float(v) for k, v in p.items()} for p in cached["profiles"]
            ]
            return profiles, block_phrase_embs

    profiles: List[Dict[str, float]] = []
    for idx in range(len(wine_embeddings)):
        prof, _ = block_profile_from_embedding(wine_embeddings[idx], block_phrase_embs)
        profiles.append(prof)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "block_names": block_names,
                "profiles": profiles,
            },
            f,
            ensure_ascii=False,
        )

    return profiles, block_phrase_embs


def build_user_query_text(user_answers: Dict[str, Any]) -> str:
    """
    Assemble les réponses libres et guidées de l'utilisateur en un texte riche
    pour l'encodage sémantique global et le profil par bloc.
    """
    parts: List[str] = []

    free_text_keys = [
        "description",
        "free_text",
        "wine_description",
        "liked_wine",
        "liked_wine_reason",
        "food_or_occasion",
        "occasion",
        "pairing",
        "oaky_experience",
        "woody_taste",
    ]
    for key in free_text_keys:
        val = user_answers.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())

    # Intègre aussi les sélections explicites (arômes, pays, couleur) si présentes
    for list_key in ("aromas", "preferred_aromas", "countries", "preferred_countries"):
        val = user_answers.get(list_key)
        if isinstance(val, (list, tuple)) and val:
            parts.append(", ".join(str(x) for x in val if x))

    return " . ".join(parts).strip()


def _apply_hard_filters(wines_df: pd.DataFrame, user_answers: Dict[str, Any]) -> pd.Index:
    """
    Applique les filtres durs :
    - budget maximum (`price <= budget`)
    - couleur imposée (si différente de 'peu importe' / 'any' / vide)
    """
    mask = pd.Series(True, index=wines_df.index)

    # 1. Filtre budget maximum
    budget = user_answers.get("max_price")
    if budget is None:
        budget = user_answers.get("budget")

    price_col = next((c for c in ("price", "prix") if c in wines_df.columns), None)
    if budget is not None and price_col is not None:
        try:
            max_b = float(budget)
            prices = pd.to_numeric(wines_df[price_col], errors="coerce")
            # Conserve les lignes dont le prix est inférieur ou égal au budget
            mask &= prices.notna() & (prices <= max_b)
        except (TypeError, ValueError):
            pass

    # 2. Filtre couleur imposée
    color_choice = user_answers.get("color") or user_answers.get("couleur")
    color_col = next((c for c in ("color", "couleur", "wine_color", "type") if c in wines_df.columns), None)

    if color_choice and color_col is not None:
        c_norm = str(color_choice).strip().lower()
        ignored_values = {"peu importe", "any", "all", "toutes", "indifférent", "indifferent", ""}
        if c_norm not in ignored_values:
            # Mapping FR <-> EN courant
            aliases = {
                "rouge": ["red", "rouge"],
                "red": ["red", "rouge"],
                "blanc": ["white", "blanc"],
                "white": ["white", "blanc"],
                "rosé": ["rose", "rosé", "pink"],
                "rose": ["rose", "rosé", "pink"],
                "effervescent": ["sparkling", "effervescent", "champagne", "crémant"],
                "sparkling": ["sparkling", "effervescent", "champagne", "crémant"],
            }
            targets = aliases.get(c_norm, [c_norm])
            col_series = wines_df[color_col].fillna("").astype(str).str.lower()
            color_mask = pd.Series(False, index=wines_df.index)
            for t in targets:
                color_mask |= col_series.str.contains(t, regex=False)
            mask &= color_mask

    return wines_df.index[mask]


def _top_matching_phrases(
    query_text: str,
    wine_dict: Dict[str, Any],
    block_phrase_embs: Dict[str, Tuple[List[str], np.ndarray]],
    encode_fn: Callable[[List[str]], np.ndarray],
    top_n: int = 3,
) -> List[Dict[str, Any]]:
    """
    Identifie les phrases de référence des blocs qui correspondent le mieux
    au besoin de l'utilisateur et au profil textuel du vin.
    """
    if not query_text or not block_phrase_embs:
        return []

    query_emb = np.asarray(encode_fn([query_text]), dtype=np.float32)[0]
    wine_desc = str(
        wine_dict.get("description")
        or wine_dict.get("text")
        or wine_dict.get("title")
        or ""
    ).strip()
    wine_emb = np.asarray(encode_fn([wine_desc]), dtype=np.float32)[0] if wine_desc else None

    candidates: List[Dict[str, Any]] = []
    for block_name, (phrases, phrase_embs) in block_phrase_embs.items():
        if phrase_embs.size == 0:
            continue
        u_sims = cosine_similarity_matrix(query_emb, phrase_embs)[0]
        if wine_emb is not None:
            w_sims = cosine_similarity_matrix(wine_emb, phrase_embs)[0]
            combined_sims = 0.5 * u_sims + 0.5 * w_sims
        else:
            combined_sims = u_sims

        for idx, phrase in enumerate(phrases):
            candidates.append(
                {
                    "block": block_name,
                    "phrase": phrase,
                    "user_similarity": float(u_sims[idx]),
                    "score": float(combined_sims[idx]),
                }
            )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:top_n]


def recommend(
    user_answers: Dict[str, Any],
    k: int = 3,
    wines_df: Optional[pd.DataFrame] = None,
    wine_embeddings: Optional[np.ndarray] = None,
    blocks_data: Any = None,
    encode_fn: Optional[Callable[[List[str]], np.ndarray]] = None,
    weights: Tuple[float, float, float] = DEFAULT_WEIGHTS,
) -> List[Dict[str, Any]]:
    """
    Recommande les `k` meilleurs vins selon les réponses de l'utilisateur.

    Retourne une liste de dictionnaires contenant :
    - les métadonnées du vin
    - `score` : score total normalisé dans [0, 1]
    - `score_breakdown` : détail des composantes brutes et normalisées
    - `user_block_profile` : score de couverture par bloc pour l'utilisateur
    - `wine_block_profile` : score de couverture par bloc pour le vin
    - `matching_phrases` : phrases de référence les plus proches
    """
    root = _project_root()
    data_dir = root / "data"
    cache_dir = data_dir / "cache"

    # Chargement par défaut de la fonction d'encodage SBERT du Lot 2
    if encode_fn is None:
        from src.embeddings import encode as default_encode  # type: ignore

        encode_fn = default_encode

    # Chargement des blocs de référence (Lot 1)
    if blocks_data is None:
        blocks_data = _load_blocks_fallback(data_dir / "processed" / "blocks.json")
    blocks_mapping = extract_blocks_mapping(blocks_data)

    # Chargement des vins et embeddings (Lots 0 & 2)
    if wines_df is None:
        wines_df = _load_wines_fallback(data_dir)
    if wine_embeddings is None:
        wine_embeddings = _load_wine_embeddings_fallback(cache_dir, wines_df, encode_fn)

    # Profils par bloc des 600 vins (mis en cache)
    wine_block_profiles, block_phrase_embs = get_or_compute_wine_block_profiles(
        wine_embeddings=wine_embeddings,
        blocks_mapping=blocks_mapping,
        encode_fn=encode_fn,
        cache_dir=cache_dir,
    )

    # Filtres durs (budget et couleur)
    eligible_indices = _apply_hard_filters(wines_df, user_answers)
    if len(eligible_indices) == 0:
        return []

    # Texte et embedding utilisateur
    user_text = build_user_query_text(user_answers)
    if user_text:
        user_emb = np.asarray(encode_fn([user_text]), dtype=np.float32)[0]
        user_profile, _ = block_profile_from_embedding(user_emb, block_phrase_embs)
    else:
        user_emb = np.zeros(wine_embeddings.shape[1], dtype=np.float32)
        user_profile = {b: 0.0 for b in block_phrase_embs}

    # Calcul des métriques brutes sur les vins éligibles
    pos_indices = [wines_df.index.get_loc(idx) for idx in eligible_indices]
    elig_embs = wine_embeddings[pos_indices]
    raw_sims = cosine_similarity_matrix(user_emb, elig_embs)[0] if user_text else np.zeros(len(pos_indices), dtype=np.float32)

    raw_affinities: List[float] = []
    raw_pref_bonuses: List[float] = []
    wine_dicts: List[Dict[str, Any]] = []

    for pos, df_idx in zip(pos_indices, eligible_indices):
        w_dict = wines_df.loc[df_idx].to_dict()
        w_dict["_row_index"] = int(pos)
        wine_dicts.append(w_dict)

        w_prof = wine_block_profiles[pos]
        raw_affinities.append(block_affinity(user_profile, w_prof))
        raw_pref_bonuses.append(compute_preferences_bonus(user_answers, w_dict))

    # Normalisation min-max sur les candidats éligibles
    norm_sims = normalize_minmax(np.asarray(raw_sims, dtype=np.float32))
    norm_affs = normalize_minmax(np.asarray(raw_affinities, dtype=np.float32))
    norm_prefs = normalize_minmax(np.asarray(raw_pref_bonuses, dtype=np.float32))

    scored_results: List[Dict[str, Any]] = []
    for i, (pos, w_dict) in enumerate(zip(pos_indices, wine_dicts)):
        total_score = wine_score(
            user_sim_norm=float(norm_sims[i]),
            user_affinity_norm=float(norm_affs[i]),
            user_pref_bonus_norm=float(norm_prefs[i]),
            weights=weights,
        )
        scored_results.append(
            {
                "wine": w_dict,
                "score": total_score,
                "score_breakdown": {
                    "semantic_raw": float(raw_sims[i]),
                    "semantic_norm": float(norm_sims[i]),
                    "block_affinity_raw": float(raw_affinities[i]),
                    "block_affinity_norm": float(norm_affs[i]),
                    "preferences_raw": float(raw_pref_bonuses[i]),
                    "preferences_norm": float(norm_prefs[i]),
                },
                "user_block_profile": user_profile,
                "wine_block_profile": wine_block_profiles[pos],
                "matching_phrases": _top_matching_phrases(
                    query_text=user_text,
                    wine_dict=w_dict,
                    block_phrase_embs=block_phrase_embs,
                    encode_fn=encode_fn,
                    top_n=3,
                ),
            }
        )

    scored_results.sort(key=lambda item: item["score"], reverse=True)
    return scored_results[: max(1, int(k))]