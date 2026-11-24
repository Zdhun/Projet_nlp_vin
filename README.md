# Recommandation de vins par analyse sémantique

Projet NLP — ECE ING5 Data & IA (2026-27) : *Analyse sémantique et systèmes intelligents de recommandation contextuelle*, thème 5 « Recommandation de vins fondée sur des profils gustatifs sémantiques ».

> ⚠️ Prototype **éducatif** destiné à des utilisateurs adultes. Aucun achat ni incitation à la consommation. L'abus d'alcool est dangereux pour la santé.

## Installation

Prérequis : Python 3.12, Node.js 20 ou plus.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd web && npm install && cd ..
```

## Lancer l'application

Dans deux terminaux, depuis la racine du projet :

```bash
uvicorn api.main:app --port 8000
```

```bash
cd web && npm run dev
```

Puis ouvrir http://localhost:5173. Au premier lancement, l'API télécharge le modèle SBERT (~470 Mo) et calcule les embeddings des 600 vins (environ 1 minute). Ensuite, une recommandation prend environ 0,3 s.

## Structure

```
api/main.py                        API FastAPI : options du questionnaire, recommandation, sauvegarde des réponses
web/                               application React + TypeScript (Vite)
  src/components/Home.tsx          accueil
  src/components/Questionnaire.tsx questionnaire en 9 étapes + relecture
  src/components/Results.tsx       top 3 expliqué
  src/components/Glass.tsx         verre SVG animé (progression, score)
src/
  reference.py                     chargement des vins, blocs et accords (lot 1)
  embeddings.py                    encodage SBERT multilingue (lot 2)
  scoring.py, recommender.py       score et recommandation (lot 3)
data/
  raw/winemag_reviews.csv.gz       corpus complet (169k critiques)
  processed/                       jeu de référence (600 vins), blocs, accords
  responses/                       réponses enregistrées (non versionnées)
notebooks/                         documentation et expériences
scripts/prepare_data.py            pipeline de préparation des données
tests/                             tests (pytest)
```

Détail des données : [data/README.md](data/README.md). Répartition du travail : [PLAN.md](PLAN.md).
