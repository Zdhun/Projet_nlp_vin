# Recommandation de vins par analyse sémantique

Projet NLP — ECE ING5 Data & IA (2026-27) : *Analyse sémantique et systèmes intelligents de recommandation contextuelle*, thème 5 « Recommandation de vins fondée sur des profils gustatifs sémantiques ».

> ⚠️ Prototype **éducatif** destiné à des utilisateurs adultes. Aucun achat ni incitation à la consommation. L'abus d'alcool est dangereux pour la santé.

## Installation

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/prepare_data.py   # régénère les données (déjà versionnées)
```

## Structure

```
data/
  raw/winemag_reviews.csv.gz       corpus complet (169k critiques)
  processed/wines_reference.csv    jeu de référence (600 vins, 40 cépages)
  README.md                        origine, licence, prétraitement
scripts/prepare_data.py            pipeline de préparation des données
```

Détail des données : [data/README.md](data/README.md).
