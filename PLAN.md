# Plan de travail — Recommandation de vins par analyse sémantique

Objectif : une application web (React + TypeScript, API Python FastAPI) où l'utilisateur décrit le vin qu'il cherche, en français ou en anglais. Le système compare sa description aux 600 vins de référence par similarité sémantique et propose un **top 3 expliqué**, avec des graphiques.

On reste **simple** : d'abord une version qui marche de bout en bout, ensuite on améliore.

---

## Vue d'ensemble

| # | Lot | Qui | Dépend de | Fichiers |
|---|---|---|---|---|
| 0 | Données | ✅ fait | — | `data/`, `scripts/prepare_data.py` |
| 1 | Blocs gustatifs et accords mets-vins | ✅ fait | 0 | `data/processed/blocks.json`, `data/processed/food_pairing.csv`, `src/reference.py` |
| 2 | Moteur sémantique (embeddings) | ✅ fait | 0 | `src/embeddings.py`, `notebooks/02_embeddings.ipynb` |
| 3 | Score et recommandation | ✅ fait | 1, 2 | `src/scoring.py`, `src/recommender.py` |
| 4 | Questionnaire et interface | ✅ fait | 3 | `web/` (React + TypeScript), `api/main.py` (FastAPI) |
| 5 | Visualisations et explications | ✅ fait | 3 | `src/explain.py`, `src/viz.py` |
| 6 | Évaluation, documentation, slides | Personne F | 3 | `notebooks/05_evaluation.ipynb`, `slides/` |
| 7 | Bonus LLM (facultatif) | Qui a fini en premier | 3 | `src/llm.py` |

> Moins de 6 personnes ? Regroupez 1 et 3, puis 5 et 6.
> Les lots 1, 2 et 4 peuvent démarrer **en même temps** dès le premier jour.

---

## Lot 1 — Blocs gustatifs et accords mets-vins ✅

> **Réalisé** : 5 blocs (Arômes fruités, Épices et boisé, Floral et minéral, Structure et style, Accords et occasions) avec 46 phrases. La table d'accords couvre les 40 cépages. Le chargement se fait par `src/reference.py`, testé dans `tests/test_reference.py`. Le détail est dans `data/README.md`.
> Écart avec le plan initial : « Structure » et « Style » sont fusionnés, et un bloc « Floral et minéral » est ajouté, car ces notes sont fréquentes dans les critiques.

Le sujet demande des **catégories ou blocs** et un **score de couverture**. On définit 5 blocs qui structurent un profil gustatif.

1. Créer `data/processed/blocks.json` avec 5 blocs et 6 à 10 phrases de référence courtes par bloc, **en anglais** comme les descriptions :
   - **Arômes fruités** : « red berries, cherry, raspberry », « citrus, lemon, grapefruit », « tropical fruit, pineapple »…
   - **Arômes épicés et boisés** : « oak, vanilla, toast », « black pepper, spice », « earthy, leather, tobacco »…
   - **Structure** : « light-bodied and fresh », « full-bodied and rich », « firm tannins », « crisp acidity »…
   - **Style et sensation** : « elegant and delicate », « bold and powerful », « mineral », « sweet », « dry »…
   - **Occasion et accord** : « pairs with grilled meat », « with seafood », « aperitif », « with cheese »…
2. Créer `food_pairing.csv` : une table simple qui associe chaque cépage aux plats qui l'accompagnent (`variety, food`), soit environ 40 lignes. Exemple : `Pinot Noir, salmon; duck; mushrooms`. Sources : sites de sommellerie, à citer.
3. Documenter les choix dans `data/README.md`, section « Blocs ».

✅ **Fini quand** : les deux fichiers existent et sont relus par le groupe.

---

## Lot 2 — Moteur sémantique ✅

- [x] Le [notebook](notebooks/02_embeddings.ipynb) découpe les requêtes en phrases avec NLTK et compare TF-IDF, Word2Vec par moyenne des vecteurs de mots et SBERT multilingue (`paraphrase-multilingual-MiniLM-L12-v2`).
- [x] Le [module d'embeddings](src/embeddings.py) fournit `encode(texts) -> np.ndarray` sur CPU pour les textes français et anglais. Les vecteurs des 600 vins sont réutilisés depuis `data/cache/`.
- [x] Le mini-test qualitatif affiche les cinq premiers vins selon chaque méthode pour chacune des cinq requêtes, soit 75 résultats disponibles pour les slides.

Le notebook a été exécuté intégralement et la réutilisation du cache a été vérifiée.

---

## Lot 3 — Score et recommandation

**Formule (à justifier dans le notebook) :**

```
score_vin = 0.6 × sim(description utilisateur, description du vin)   # sémantique global
          + 0.3 × affinité_blocs                                      # profil par bloc
          + 0.1 × bonus_préférences                                   # couleur, pays (Likert, QCM)
puis filtre dur : prix <= budget, couleur si imposée
```

- `sim` : similarité cosinus SBERT.
- `affinité_blocs` : pour chaque bloc, on compare le profil de l'utilisateur et celui du vin. Chaque profil est la similarité maximale du texte avec les phrases du bloc. On en tire **un score de couverture par bloc**, qui sert au radar.
- On normalise les scores entre 0 et 1, par min-max sur les 600 vins : les similarités brutes de MiniLM dépassent rarement 0,7.

**Étapes :**

1. `src/scoring.py` : `block_profile(text)`, `wine_score(user, wine)`.
2. `src/recommender.py` : `recommend(user_answers, k=3)`, qui renvoie une liste de vins avec leur score total, le score de chaque bloc et les phrases qui correspondent le mieux.
3. Calculer les profils par bloc des 600 vins une fois pour toutes, et les mettre en cache.

✅ **Fini quand** : `recommend({...})` renvoie un top 3 cohérent dans un notebook.

---

## Lot 4 — Questionnaire et interface ✅

> **Choix** : une vraie application web plutôt que Streamlit, pour une interface plus soignée et une démo plus marquante.

- [x] **API** `api/main.py` (FastAPI) : expose `recommend()` du lot 3 (`POST /api/recommend`), les listes du questionnaire (`GET /api/options`) et enregistre chaque réponse en JSON dans `data/responses/`.
- [x] **Application** `web/` (Vite + React + TypeScript) : accueil, questionnaire en 9 étapes, écran d'analyse, top 3 détaillé, gestion des erreurs.
- [x] Types de questions demandés par le sujet :
  - **texte libre** (3 questions) : l'envie, un vin marquant, le plat ou l'occasion ;
  - **Likert de 1 à 5** : intensité, fruité, boisé, douceur, vivacité ;
  - **question guidée** : « Déjà goûté un vin boisé ? » puis, si oui, « L'avez-vous aimé ? » ;
  - **QCM** : couleur ;
  - **cases à cocher** : arômes, pays ;
  - **curseur** : budget.
- [x] Avertissement « prototype éducatif, réservé aux adultes » visible sur toutes les pages, confirmation de l'âge au démarrage.
- [x] Correction de performance dans `src/recommender.py` : les phrases explicatives ne sont plus calculées que pour le top 3. On passe de 8 s à 0,3 s par recommandation, avec le même classement.
- [x] Interface responsive (mobile compris), navigation au clavier, animations désactivées si le système le demande.

Lancement : voir le README.

## Lot 5 — Visualisations et explications ✅

- [x] [Explications par modèles de texte](src/explain.py) pour les trois vins affichés. Chaque fiche présente le score, une phrase de l'utilisateur rapprochée d'un repère gustatif, les familles communes et le prix par rapport au budget.
- [x] [Radar Plotly](src/viz.py) qui superpose le profil utilisateur et celui du premier vin sur les cinq blocs gustatifs.
- [x] Diagramme en barres des scores des cinq premiers vins éligibles.
- [x] Heatmap des similarités entre les phrases saisies et les cinq blocs.
- [ ] Carte 2D facultative des 600 vins (UMAP ou t-SNE) avec le point de l'utilisateur.

Les trois graphiques et les explications s'affichent dans la page de résultats. Le parcours a été vérifié sur ordinateur et sur mobile.

---

## Lot 6 — Évaluation, documentation, slides

1. Écrire **20 requêtes de test** avec la réponse attendue : couleur et cépage plausibles. Exemple : « un blanc vif pour des huîtres » doit donner un Muscadet, un Sauvignon Blanc ou un Albariño.
2. `05_evaluation.ipynb` : taux de bonnes couleurs ou bons cépages dans le top 3, pour TF-IDF, fastText et SBERT. Cela prouve l'apport du sémantique.
3. Compléter le `README.md` : installation, lancement, choix techniques.
4. Slides, environ 12 :
   - contexte ;
   - données ;
   - pipeline ;
   - **démonstration du sémantique (comparaison TF-IDF / SBERT)** ;
   - score ;
   - démo ;
   - résultats ;
   - difficultés ;
   - perspectives.
5. Préparer une démo en direct avec 3 scénarios testés à l'avance.

✅ **Fini quand** : le notebook d'évaluation tourne et les slides sont prêtes.

---

## Lot 7 — Bonus LLM (facultatif, en dernier)

L'app doit fonctionner **sans** ce lot.

- **Bonus A** : un bouton « Explication détaillée ». On envoie le profil, les scores et le top 3 à un LLM, Gemini en offre gratuite ou Ollama en local, qui rédige une explication en français.
- **Bonus E** : un LLM reformule une description courte (« un truc pas trop fort ») avant l'analyse.

---

## Planning indicatif (4 semaines)

| Semaine | Objectif |
|---|---|
| **S1** | Lots 1, 2 et 4 en parallèle (l'app tourne avec un faux moteur) |
| **S2** | Lot 3 : version de bout en bout qui marche (**jalon important**) |
| **S3** | Lots 5 et 6 : visualisations, explications, évaluation |
| **S4** | Corrections, slides, répétition de la démo, bonus si le temps le permet |

## Règles du groupe

- Une branche par lot (`lot2-embeddings`…), puis une pull request vers `main`.
- Des commentaires à chaque étape du code : c'est exigé dans le barème.
- Ne pas versionner `.venv/` ni `data/cache/` (déjà dans le `.gitignore`).
- Toute nouvelle dépendance va dans `requirements.txt`.
- **Chaque membre doit pouvoir présenter sa partie** : la note de démo est individuelle.
