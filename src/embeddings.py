"""Encodage sémantique français/anglais des requêtes et des critiques."""

from collections.abc import Iterable
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from filelock import FileLock
import numpy as np

from .reference import ROOT, load_wines

MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
EMBEDDING_DIM = 384
CACHE_DIR = ROOT / "data" / "cache"
CACHE_VERSION = 1  # À incrémenter si le calcul des vecteurs change.


@lru_cache(maxsize=1)
def _load_model():
    """Charge le modèle CPU au premier encodage du processus."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_ID, revision=MODEL_REVISION, device="cpu")


def encode(texts: str | Iterable[str]) -> np.ndarray:
    """Renvoie une matrice float32 de forme (nombre de textes, 384).

    Les vecteurs sont normalisés pour calculer le cosinus par produit scalaire.
    Une chaîne seule produit une matrice d'une ligne et l'ordre des textes est conservé.
    """
    if isinstance(texts, str):
        texts = [texts]

    # Uniformise les espaces. Le modèle gère lui-même la casse et la ponctuation.
    sentences = [" ".join(text.split()) for text in texts]
    if not sentences:
        return np.empty((0, EMBEDDING_DIM), dtype=np.float32)

    vectors = _load_model().encode(
        sentences,
        batch_size=32,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype=np.float32)


def load_wine_embeddings() -> np.ndarray:
    """Charge les vecteurs en cache, dans l'ordre des lignes de load_wines()."""
    wines = load_wines()
    # L'empreinte change si les textes, les identifiants ou l'ordre des vins changent.
    rows = wines[["wine_id", "description"]].to_numpy().tolist()
    key = json.dumps([MODEL_ID, MODEL_REVISION, CACHE_VERSION, rows], ensure_ascii=False)
    digest = sha256(key.encode("utf-8")).hexdigest()
    path = CACHE_DIR / f"wine_embeddings_{digest}.npy"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Un seul processus calcule le lot. Le remplacement atomique évite tout fichier partiel.
    with FileLock(str(path) + ".lock"):
        try:
            with path.open("rb") as file:
                vectors = np.lib.format.read_array(file, allow_pickle=False)
        except (FileNotFoundError, ValueError, EOFError):
            vectors = None

        if (
            vectors is not None
            and vectors.shape == (len(wines), EMBEDDING_DIM)
            and vectors.dtype == np.float32
            and np.isfinite(vectors).all()
        ):
            return vectors

        vectors = encode(wines["description"])
        with TemporaryDirectory(dir=CACHE_DIR) as directory:
            temporary_path = Path(directory) / path.name
            np.save(temporary_path, vectors, allow_pickle=False)
            temporary_path.replace(path)
        return vectors
