"""
src/scoring.py
--------------
Calcul des profils gustatifs par bloc, des similarités sémantiques,
de la normalisation min-max et du score composite d'un vin.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np


def cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Calcule la similarité cosinus entre deux ensembles de vecteurs.

    Parameters
    ----------
    a : np.ndarray
        Tableau de forme (n, d) ou (d,).
    b : np.ndarray
        Tableau de forme (m, d) ou (d,).

    Returns
    -------
    np.ndarray
        Matrice de similarité cosinus de forme (n, m).
    """
    a_2d = np.atleast_2d(np.asarray(a, dtype=np.float32))
    b_2d = np.atleast_2d(np.asarray(b, dtype=np.float32))

    # Évite la division par zéro si un vecteur est nul
    a_norms = np.linalg.norm(a_2d, axis=1, keepdims=True)
    b_norms = np.linalg.norm(b_2d, axis=1, keepdims=True)

    a_unit = np.divide(a_2d, np.maximum(a_norms, 1e-12))
    b_unit = np.divide(b_2d, np.maximum(b_norms, 1e-12))

    return a_unit @ b_unit.T


def normalize_minmax(values: np.ndarray) -> np.ndarray:
    """
    Normalise un tableau 1D sur [0, 1] par min-max scaling.
    Si toutes les valeurs sont identiques, retourne un tableau de zéros.
    """
    arr = np.asarray(values, dtype=np.float32)
    if arr.size == 0:
        return arr

    v_min = float(np.min(arr))
    v_max = float(np.max(arr))
    span = v_max - v_min

    if span < 1e-12:
        return np.zeros_like(arr, dtype=np.float32)

    return (arr - v_min) / span


def extract_blocks_mapping(blocks_data: Any) -> Dict[str, List[str]]:
    """
    Normalise la structure de `blocks.json` vers un dictionnaire
    `{nom_bloc: [phrase_1, phrase_2, ...]}` en extrayant `text_en`
    (ou `text` / `phrase` / chaîne directe) dans chaque entrée.
    """
    mapping: Dict[str, List[str]] = {}

    def _extract_phrases(raw_phrases: Any) -> List[str]:
        result: List[str] = []
        if not isinstance(raw_phrases, list):
            return result
        for p in raw_phrases:
            if isinstance(p, str) and p.strip():
                result.append(p.strip())
            elif isinstance(p, dict):
                txt = (
                    p.get("text_en")
                    or p.get("text")
                    or p.get("phrase")
                    or p.get("label_en")
                    or p.get("label_fr")
                )
                if isinstance(txt, str) and txt.strip():
                    result.append(txt.strip())
        return result

    def _extract_from_entry(entry: Dict[str, Any], fallback_name: str = "") -> None:
        name = (
            entry.get("name_fr")
            or entry.get("name")
            or entry.get("nom")
            or entry.get("label")
            or entry.get("title")
            or entry.get("name_en")
            or entry.get("id")
            or fallback_name
        )
        phrases: List[str] = []
        for key in ("phrases", "examples", "texts", "descriptors", "items", "sentences", "anchors"):
            if key in entry:
                phrases = _extract_phrases(entry[key])
                if phrases:
                    break
        if name and phrases:
            mapping[str(name)] = phrases

    if isinstance(blocks_data, dict):
        for wrapper_key in ("blocks", "blocs", "categories", "data"):
            if wrapper_key in blocks_data and isinstance(blocks_data[wrapper_key], list):
                for idx, item in enumerate(blocks_data[wrapper_key]):
                    if isinstance(item, dict):
                        _extract_from_entry(item, fallback_name=f"Bloc_{idx+1}")
                if mapping:
                    return mapping

        for key, val in blocks_data.items():
            if isinstance(val, list):
                phrases = _extract_phrases(val)
                if phrases:
                    mapping[str(key)] = phrases
            elif isinstance(val, dict):
                _extract_from_entry(val, fallback_name=str(key))
        return mapping

    if isinstance(blocks_data, list):
        for idx, item in enumerate(blocks_data):
            if isinstance(item, dict):
                _extract_from_entry(item, fallback_name=f"Bloc_{idx+1}")

    return mapping


def precompute_block_phrase_embeddings(
    blocks_mapping: Dict[str, List[str]],
    encode_fn: Callable[[List[str]], np.ndarray],
) -> Dict[str, Tuple[List[str], np.ndarray]]:
    """
    Calcule et met en mémoire les embeddings de toutes les phrases de référence
    pour chaque bloc gustatif.
    """
    cache: Dict[str, Tuple[List[str], np.ndarray]] = {}
    for block_name, phrases in blocks_mapping.items():
        if not phrases:
            continue
        emb = encode_fn(phrases)
        cache[block_name] = (phrases, np.asarray(emb, dtype=np.float32))
    return cache


def block_profile_from_embedding(
    text_embedding: np.ndarray,
    block_embeddings: Dict[str, Tuple[List[str], np.ndarray]],
) -> Tuple[Dict[str, float], Dict[str, Dict[str, Any]]]:
    """
    Calcule le profil par bloc à partir d'un embedding déjà calculé.

    Pour chaque bloc, le score de couverture est la similarité cosinus maximale
    entre le texte et les phrases de référence du bloc.

    Returns
    -------
    profile : dict[str, float]
        Score par bloc (ex. {"Arômes fruités": 0.42, ...}).
    matches : dict[str, dict]
        Détail de la meilleure phrase correspondante par bloc.
    """
    profile: Dict[str, float] = {}
    matches: Dict[str, Dict[str, Any]] = {}

    for block_name, (phrases, phrase_embs) in block_embeddings.items():
        if phrase_embs.size == 0 or not phrases:
            profile[block_name] = 0.0
            matches[block_name] = {"best_phrase": None, "similarity": 0.0}
            continue

        # Similarités entre le vecteur texte (1, d) et les phrases du bloc (m, d)
        sims = cosine_similarity_matrix(text_embedding, phrase_embs)[0]
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])

        profile[block_name] = best_sim
        matches[block_name] = {
            "best_phrase": phrases[best_idx],
            "similarity": best_sim,
        }

    return profile, matches


def block_profile(
    text: str,
    blocks_data: Any,
    encode_fn: Callable[[List[str]], np.ndarray],
    precomputed_block_embeddings: Optional[Dict[str, Tuple[List[str], np.ndarray]]] = None,
) -> Dict[str, float]:
    """
    Fonction principale demandée dans le Lot 3 : calcule le score de couverture
    de `text` pour chacun des blocs gustatifs (similarité max avec les phrases du bloc).
    """
    cleaned = (text or "").strip()
    blocks_mapping = extract_blocks_mapping(blocks_data)

    if not cleaned:
        return {name: 0.0 for name in blocks_mapping}

    if precomputed_block_embeddings is None:
        precomputed_block_embeddings = precompute_block_phrase_embeddings(blocks_mapping, encode_fn)

    text_emb = np.asarray(encode_fn([cleaned]), dtype=np.float32)[0]
    profile, _ = block_profile_from_embedding(text_emb, precomputed_block_embeddings)
    return profile


def block_affinity(user_profile: Dict[str, float], wine_profile: Dict[str, float]) -> float:
    """
    Mesure l'affinité entre le profil de blocs de l'utilisateur et celui du vin.
    On compare les deux vecteurs de scores par bloc via similarité cosinus (ramenée sur [0, 1]).
    """
    keys = list(user_profile.keys())
    if not keys:
        return 0.0

    u_vec = np.array([float(user_profile.get(k, 0.0)) for k in keys], dtype=np.float32)
    w_vec = np.array([float(wine_profile.get(k, 0.0)) for k in keys], dtype=np.float32)

    if float(np.linalg.norm(u_vec)) < 1e-12 or float(np.linalg.norm(w_vec)) < 1e-12:
        return 0.0

    raw_cos = float(cosine_similarity_matrix(u_vec, w_vec)[0, 0])
    # Sécurité numérique sur [-1, 1] -> [0, 1]
    return float(np.clip((raw_cos + 1.0) / 2.0, 0.0, 1.0))


def compute_preferences_bonus(user_answers: Dict[str, Any], wine: Dict[str, Any]) -> float:
    """
    Calcule un score de bonus préférences dans [0, 1] à partir des réponses structurées :
    - QCM couleur / cépage / pays
    - Cases à cocher (arômes préférés, pays)
    - Échelles Likert (1 à 5) et question guidée sur le boisé
    """
    criteria_scores: List[float] = []

    wine_text = " ".join(
        str(wine.get(col, "") or "")
        for col in ("title", "name", "variety", "grape", "country", "region", "description", "color")
    ).lower()

    # 1. Pays préférés (cases à cocher ou champ unique)
    preferred_countries = user_answers.get("countries") or user_answers.get("preferred_countries") or []
    if isinstance(preferred_countries, str):
        preferred_countries = [preferred_countries]
    preferred_countries = [c.strip().lower() for c in preferred_countries if c and str(c).strip()]

    wine_country = str(wine.get("country") or "").strip().lower()
    if preferred_countries:
        if wine_country and any(c in wine_country or wine_country in c for c in preferred_countries):
            criteria_scores.append(1.0)
        else:
            criteria_scores.append(0.0)

    # 2. Arômes préférés (cases à cocher)
    preferred_aromas = user_answers.get("aromas") or user_answers.get("preferred_aromas") or []
    if isinstance(preferred_aromas, str):
        preferred_aromas = [preferred_aromas]
    preferred_aromas = [a.strip().lower() for a in preferred_aromas if a and str(a).strip()]

    if preferred_aromas:
        matched = sum(1 for a in preferred_aromas if a in wine_text)
        criteria_scores.append(min(1.0, matched / max(1, len(preferred_aromas))))

    # 3. Question guidée / Likert sur le boisé ("oak", "oaky", "boisé")
    oaky_likert = user_answers.get("woody_likert") or user_answers.get("oak_likert")
    oaky_guided = str(user_answers.get("oaky_experience") or user_answers.get("woody_taste") or "").lower()
    wine_has_oak = any(tok in wine_text for tok in ("oak", "oaky", "barrel", "vanilla", "toast", "boisé", "fût"))

    if oaky_likert is not None:
        # Likert 1..5 -> cible élevée si >= 4, faible si <= 2
        likert_val = float(oaky_likert)
        target_oak = (likert_val - 1.0) / 4.0  # 0.0 à 1.0
        criteria_scores.append(1.0 - abs(target_oak - (1.0 if wine_has_oak else 0.0)))
    elif oaky_guided:
        if "non" in oaky_guided or "dislike" in oaky_guided or "pas aimé" in oaky_guided:
            criteria_scores.append(0.0 if wine_has_oak else 1.0)
        elif "oui" in oaky_guided or "aimé" in oaky_guided or "like" in oaky_guided:
            criteria_scores.append(1.0 if wine_has_oak else 0.4)

    # 4. Autres échelles Likert (1 à 5) : intensité, fruité, sucrosité, acidité
    likert_keywords: Dict[str, List[str]] = {
        "intensity_likert": ["full-bodied", "bold", "intense", "rich", "powerful"],
        "fruity_likert": ["fruit", "fruity", "berry", "berries", "cherry", "citrus", "tropical"],
        "sweetness_likert": ["sweet", "off-dry", "honey", "ripe"],
        "acidity_likert": ["acidity", "acidic", "crisp", "fresh", "bright", "zesty"],
    }

    for key, keywords in likert_keywords.items():
        if key in user_answers and user_answers[key] is not None:
            val = float(user_answers[key])
            desired_strength = (val - 1.0) / 4.0  # [0, 1]
            present = 1.0 if any(kw in wine_text for kw in keywords) else 0.0
            criteria_scores.append(1.0 - abs(desired_strength - present))

    if not criteria_scores:
        return 0.5  # Neutre si aucune préférence structurée n'est renseignée

    return float(np.mean(criteria_scores))


def wine_score(
    user_sim_norm: float,
    user_affinity_norm: float,
    user_pref_bonus_norm: float,
    weights: Tuple[float, float, float] = (0.6, 0.3, 0.1),
) -> float:
    """
    Calcule le score composite final d'un vin à partir des composantes normalisées :
        score_vin = 0.6 * sim_norm + 0.3 * affinite_blocs_norm + 0.1 * bonus_preferences_norm
    """
    w_sim, w_aff, w_pref = weights
    total_w = w_sim + w_aff + w_pref
    if total_w > 0:
        w_sim, w_aff, w_pref = w_sim / total_w, w_aff / total_w, w_pref / total_w

    return float(
        w_sim * float(user_sim_norm)
        + w_aff * float(user_affinity_norm)
        + w_pref * float(user_pref_bonus_norm)
    )