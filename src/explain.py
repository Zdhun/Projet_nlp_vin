"""Explications déterministes et analyse des phrases du questionnaire."""

from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from math import floor, isfinite

from nltk.tokenize import PunktSentenceTokenizer
import numpy as np

from .embeddings import encode
from .reference import load_blocks
from .scoring import (
    cosine_similarity_matrix,
    extract_blocks_mapping,
    precompute_block_phrase_embeddings,
)


@dataclass
class SentenceAnalysis:
    """Similarités de chaque phrase, dans l'ordre des réponses saisies."""

    sentences: list[str]
    block_scores: dict[str, np.ndarray]
    descriptor_scores: dict[str, np.ndarray]


@lru_cache(maxsize=1)
def _reference_embeddings() -> dict[str, tuple[list[str], np.ndarray]]:
    """Réutilise les mêmes phrases de référence que le score par bloc."""
    return precompute_block_phrase_embeddings(extract_blocks_mapping(load_blocks()), encode)


def analyze_sentences(texts: Iterable[str]) -> SentenceAnalysis:
    """Découpe les textes effectivement saisis et mesure leur couverture par bloc."""
    # Punkt repère la ponctuation finale dans les réponses françaises et anglaises.
    tokenizer = PunktSentenceTokenizer()
    sentences = [
        sentence.strip()
        for text in texts
        for line in text.splitlines()
        for sentence in tokenizer.tokenize(line.strip())
        if any(char.isalnum() for char in sentence)
    ]
    if not sentences:
        return SentenceAnalysis([], {}, {})

    # Un encodage groupé suffit pour la heatmap et les explications des trois vins.
    embeddings = encode(sentences)
    coverage = {}
    descriptors = {}
    for name, (phrases, reference_vectors) in _reference_embeddings().items():
        similarities = cosine_similarity_matrix(embeddings, reference_vectors).clip(-1, 1)
        coverage[name] = similarities.max(axis=1)
        descriptors.update(zip(phrases, similarities.T))
    return SentenceAnalysis(sentences, coverage, descriptors)


def explain_recommendation(
    item: dict,
    analysis: SentenceAnalysis,
    max_price: float | None = None,
) -> str:
    """Décrit le score relatif, les goûts communs et le prix d'un vin classé."""
    score = floor(round(item["score"], 4) * 100 + 0.5)
    parts = [f"Ce vin obtient {score} sur 100 parmi les vins retenus."]

    # Une phrase saisie est comparée à un repère gustatif, avec son propre cosinus.
    labels = {
        phrase["text_en"]: phrase["label_fr"]
        for block in load_blocks()
        for phrase in block["phrases"]
    }
    for match in item.get("matching_phrases", []):
        descriptor = match["phrase"]
        similarities = analysis.descriptor_scores.get(descriptor)
        if similarities is None:
            continue
        best = int(np.argmax(similarities))
        similarity = float(similarities[best])
        if similarity <= 0:
            continue
        sentence = analysis.sentences[best]
        if len(sentence) > 150:
            sentence = sentence[:149].rstrip() + "…"
        value = f"{similarity:.2f}".replace(".", ",")
        parts.append(
            f"Votre phrase « {sentence} » se rapproche du repère gustatif "
            f"« {labels.get(descriptor, descriptor)} » (similarité de {value})."
        )
        break

    # Le minimum des deux couvertures privilégie les familles présentes des deux côtés.
    user_profile = item["user_block_profile"]
    wine_profile = item["wine_block_profile"]
    shared = {
        name: min(user_value, wine_profile.get(name, 0.0))
        for name, user_value in user_profile.items()
    }
    strengths = [name for name in sorted(shared, key=shared.__getitem__, reverse=True)
                 if shared[name] > 0][:2]
    if strengths:
        named_strengths = " et ".join(f"« {name} »" for name in strengths)
        parts.append(f"Votre profil et celui de ce vin se rejoignent surtout sur {named_strengths}.")

    price = item["wine"].get("price")
    if price is not None and isfinite(price) and max_price is not None and price <= max_price:
        amount = f"{price:g}".replace(".", ",")
        parts.append(f"Son prix de référence de {amount} $ respecte votre budget.")

    return " ".join(parts)
