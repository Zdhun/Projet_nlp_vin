# Plan de travail — Recommandation de vins par analyse sémantique

Objectif : une app Streamlit où l'utilisateur décrit le vin qu'il cherche, en français ou en anglais. Le système compare sa description aux 600 vins de référence par similarité sémantique et propose un **top 3 expliqué**, avec des graphiques.

On reste **simple** : d'abord une version qui marche de bout en bout, ensuite on améliore.

---

## Vue d'ensemble

| # | Lot | Qui | Dépend de | Fichiers |
|---|---|---|---|---|
| 0 | Données | ✅ fait | — | `data/`, `scripts/prepare_data.py` |
| 1 | Blocs gustatifs et accords mets-vins | Personne A | 0 | `data/processed/blocks.json`, `data/processed/food_pairing.csv` |
| 2 | Moteur sémantique (embeddings) | Personne B | 0 | `src/embeddings.py`, `notebooks/02_embeddings.ipynb` |
| 3 | Score et recommandation | Personne C | 1, 2 | `src/scoring.py`, `src/recommender.py` |
| 4 | Questionnaire et interface | Personne D | 3 (pour brancher) | `app/streamlit_app.py` |
| 5 | Visualisations et explications | Personne E | 3 | `src/explain.py`, `src/viz.py` |
| 6 | Évaluation, documentation, slides | Personne F | 3 | `notebooks/05_evaluation.ipynb`, `slides/` |
| 7 | Bonus LLM (facultatif) | Qui a fini en premier | 3 | `src/llm.py` |

> Moins de 6 personnes ? Regroupez 1 et 3, puis 5 et 6.
> Les lots 1, 2 et 4 peuvent démarrer **en même temps** dès le premier jour.

---

## Lot 1 — Blocs gustatifs et accords mets-vins

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

## Lot 2 — Moteur sémantique

1. Notebook `02_embeddings.ipynb` :
   - prétraitement léger : minuscules, ponctuation, découpage en phrases (le texte de l'utilisateur est découpé avec `nltk` ou `spacy`) ;
   - **SBERT multilingue** : `paraphrase-multilingual-MiniLM-L12-v2`. Il est rapide, tourne sur CPU et compare directement le français et l'anglais ;
   - **fastText ou Word2Vec**, exigé par le sujet : moyenne des vecteurs de mots, en version de base ;
   - **TF-IDF** comme repère « non sémantique ».
2. `src/embeddings.py` : une fonction `encode(texts) -> np.ndarray`, avec un cache des embeddings des 600 vins dans `data/cache/` (on les calcule une seule fois).
3. Mini-test qualitatif : 5 requêtes (« un rouge léger et fruité pour un apéro ») et, pour chacune, le top 5 vu par TF-IDF, fastText et SBERT. **Ce tableau ira dans les slides.**

✅ **Fini quand** : `encode()` fonctionne et le notebook montre la comparaison des 3 méthodes.

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

## Lot 4 — Questionnaire et interface (Streamlit)

1. `app/streamlit_app.py`, sur une page avec des sections :
   - **Texte libre** (au moins 2 questions) : « Décris le vin que tu cherches », « Décris un vin que tu as aimé et pourquoi », « Pour quel plat ou quelle occasion ? » ;
   - **Likert de 1 à 5** : intensité souhaitée, fruité, boisé, sucrosité, acidité ;
   - **Questions guidées** : « As-tu déjà goûté un vin boisé ? Si oui, l'as-tu aimé ? » ;
   - **QCM** : couleur (rouge, blanc, rosé, effervescent, peu importe) ;
   - **Cases à cocher** : arômes préférés, pays ;
   - **Curseur** : budget maximum.
2. Sauvegarder chaque réponse en JSON dans `data/responses/`.
3. Avertissement visible : *« Prototype éducatif, réservé aux adultes. L'abus d'alcool est dangereux pour la santé. »*
4. Commencer avec une fonction `recommend()` factice, puis brancher la vraie dès que le lot 3 est prêt.

✅ **Fini quand** : `streamlit run app/streamlit_app.py` affiche le formulaire et le top 3.

---

## Lot 5 — Visualisations et explications

1. `src/explain.py` : une explication **par modèles de texte**, sans LLM. Exemple :
   > *« Ce Pinot Noir correspond à 84 %. Ta phrase “léger et fruité” est proche de “bright red cherry, light-bodied” (0,78). Points forts : Arômes fruités, Structure. Il est dans ton budget (22 $). »*
2. `src/viz.py`, avec Plotly :
   - un **radar** des 5 blocs, utilisateur et vin recommandé superposés ;
   - un **diagramme en barres** des scores du top 5 ;
   - une **heatmap** des phrases de l'utilisateur face aux blocs ;
   - (option) une **carte 2D** des 600 vins (UMAP ou t-SNE) avec le point de l'utilisateur.

✅ **Fini quand** : les graphiques et le texte s'affichent dans l'app.

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
