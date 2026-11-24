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

## Blocs gustatifs (`processed/blocks.json`)

Le sujet demande des **catégories** et un **score de couverture par bloc**. On définit 5 blocs qui structurent un profil gustatif. Chaque bloc contient 8 à 12 **phrases de référence**, soit 46 au total.

| Bloc | `id` | Phrases | Exemples |
|---|---|---|---|
| Arômes fruités | `fruit` | 8 | fruits rouges, fruits noirs, agrumes, exotiques, confiturés… |
| Épices, boisé et notes évoluées | `spice_oak` | 8 | vanille et toasté, poivre, cuir et tabac, chocolat et café… |
| Floral, végétal et minéral | `floral_mineral` | 8 | fleurs blanches, violette, herbacé, minéral, salin… |
| Structure et style en bouche | `structure` | 10 | léger, corsé, tanins fermes ou soyeux, vif, doux, pétillant… |
| Accords mets et occasions | `pairing` | 12 | viande rouge, fruits de mer, fromages, épicé, apéritif, fête… |

**Choix de conception :**
- **Phrases en anglais**, dans le style des critiques : elles sont comparées par embeddings aux descriptions, qui sont en anglais. Le champ `label_fr` sert à l'affichage dans l'interface (cases à cocher, axes du radar).
- **Ancrées dans le corpus** : les termes ont été choisis parmi les descripteurs fréquents du corpus. Exemples : cerise dans 21 % des descriptions, épices 17 %, boisé 15 %, prune 12,5 %, minéral 8,5 %.
- **Une phrase par famille d'arômes**, et non par mot isolé : un embedding de phrase capte mieux « fruits noirs : mûre, cassis, prune » qu'un mot seul.
- **Poids** : 1,0 pour chaque bloc par défaut (`weight`). Le lot 3 pourra les ajuster selon l'importance déclarée par l'utilisateur dans les questions Likert.
- **Bloc `pairing`** : les plats sont cités dans **moins de 3 %** des descriptions (« steak » 0,7 %, « fish » 0,5 %). Ce bloc est donc mesuré sur la description **enrichie** par la table d'accords (`text_source: description+food_pairing`, voir `src/reference.py:enriched_text`).

## Accords mets-vins (`processed/food_pairing.csv`)

Il y a une ligne pour chacun des 40 cépages du jeu de référence.

| Colonne | Contenu |
|---|---|
| `variety` | Cépage (même libellé que `wines_reference.csv`) |
| `foods_en` | Plats en anglais, séparés par `;`. Utilisés pour l'embedding. |
| `foods_fr` | Mêmes plats en français, pour l'affichage |
| `occasions_en` | Occasions (apéritif, barbecue, dîner élégant…), séparées par `;` |

**Source :** table compilée par le groupe à partir des accords classiques par cépage, tels que les donnent les guides grand public (par exemple Wine Folly) et la littérature œnologique courante. Ce sont des **règles générales par cépage** : elles ne remplacent pas un avis de sommelier sur un vin précis.

**Utilisation** (`src/reference.py`) :
- `pairing_text("Pinot Noir")` renvoie `"Pairs well with salmon, duck, roast chicken, mushrooms, soft cheese. Ideal for elegant dinner, casual dinner."` ;
- `enriched_text(vin)` renvoie la description du vin suivie de cette phrase.

Les tests de cohérence (`tests/test_reference.py`) vérifient trois choses : il y a 5 blocs, les identifiants sont uniques, et chaque cépage de référence a un accord.

## Limites connues

- Les descriptions sont en **anglais** : il faudra un modèle d'embeddings multilingue si le questionnaire est en français.
- Il n'y a **pas d'accords mets-vins** explicites : ils seront à dériver du texte, ou d'une table de règles par cépage.
- Il y a un **biais vers les vins américains**, européens et bien notés (critiques ≥ 80 points uniquement).
- Le prix et la note datent de la critique (2000 à 2017 environ).
