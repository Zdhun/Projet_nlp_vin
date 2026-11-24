# Données — Wine Reviews

## Origine

| | |
|---|---|
| **Source** | Critiques de dégustation de *Wine Enthusiast* (winemag.com), collectées par zackthoutt |
| **Publication** | Kaggle : [zynicide/wine-reviews](https://www.kaggle.com/datasets/zynicide/wine-reviews) |
| **Miroir utilisé** | Hugging Face : [spawn99/wine-reviews](https://huggingface.co/datasets/spawn99/wine-reviews) (fusion des versions 130k et 150k) |
| **Licence** | [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) : usage non commercial, attribution, partage dans les mêmes conditions |
| **Langue** | Anglais |

Les données sont utilisées uniquement dans un cadre **pédagogique** (projet ECE ING5 « Analyse sémantique et systèmes intelligents de recommandation contextuelle »).

## Fichiers

| Fichier | Lignes | Description |
|---|---|---|
| `raw/winemag_reviews.csv.gz` | 169 430 | Corpus complet nettoyé (doublons retirés) |
| `processed/wines_reference.csv` | 600 | **Jeu de référence** du système de recommandation : 40 cépages × 15 vins |

Le fichier `cache/` (parquet bruts téléchargés) n'est pas versionné. Tout est régénérable avec :

```bash
python scripts/prepare_data.py
```

## Prétraitement (`scripts/prepare_data.py`)

1. **Fusion** des splits train / validation / test : 280 901 lignes.
2. **Déduplication** sur le texte `description`, car les versions 130k et 150k se recouvrent : **169 430 vins uniques**. Les lignes qui ont un `title` sont gardées en priorité.
3. **Normalisation** des espaces dans les descriptions.
4. **`region`** = `region_1`, sinon `province`.
5. **`color`** (red / white / rose / sparkling / dessert) dérivée du cépage par une table de correspondance explicite, avec repli sur les mots « red », « white » et « sparkling » dans le nom du cépage.
6. **Jeu de référence** : vins ayant titre, prix, couleur connue et une description d'au moins 150 caractères. On retient les 40 cépages les plus fréquents et on tire 15 vins par cépage (`random_state=42`).

## Colonnes du jeu de référence

| Colonne | Type | Exemple | Rôle prévu |
|---|---|---|---|
| `wine_id` | str | `W000205` | Identifiant |
| `title` | str | `Dieter Meier 2010 Puro Corte d'Oro Red (Mendoza)` | Affichage |
| `winery` | str | `Dieter Meier` | Affichage |
| `variety` | str | `Bordeaux-style Red Blend` | Catégorie, critère |
| `color` | str | `red` | Filtre ou critère |
| `country`, `province`, `region` | str | `Argentina`, `Mendoza` | Critère « origine » |
| `price` | float (USD) | `37.0` | Contrainte budget |
| `points` | int (80-100) | `87` | Note du critique |
| `description` | str | *« Generic berry aromas come with herbal, earthy accents… »* | **Texte principal pour l'analyse sémantique** |

**Répartition du jeu de référence :**
- couleurs : 345 rouges, 180 blancs, 45 effervescents, 15 rosés, 15 doux ;
- 17 pays, dont US 194, France 118, Italie 110 ;
- prix médian 25 $, de 7 $ à 320 $.

## Limites connues

- Les descriptions sont en **anglais** : il faudra un modèle d'embeddings multilingue si le questionnaire est en français.
- Il n'y a **pas d'accords mets-vins** explicites : ils seront à dériver du texte, ou d'une table de règles par cépage.
- Il y a un **biais vers les vins américains**, européens et bien notés (critiques ≥ 80 points uniquement).
- Le prix et la note datent de la critique (2000 à 2017 environ).
