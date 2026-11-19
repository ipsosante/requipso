# Le tableau descriptif

`requipso/descriptive_pipeline.py` (orchestration et upload) et `requipso/stats.py` (statistiques).

## `DescriptivePipeline`

```python
descriptive = DescriptivePipeline(
    data=data,                      # data sur laquelle l'inclusion a déjà tourné
    inclusion_pipeline=inclusion,
    populations=["adultes", "diabete"],
    google_connector=connector,
)
descriptive.add_row(step=Age(params=AgeParams(post_func="x")), variable_type="numerical", subsets=[18, 65])
df = descriptive.run(data)          # run_iter + format_stats + upload_stats
```

À la construction :

- chaque population doit être une étape de l'inclusion ;
- `self.populations[nom]` = patients pour lesquels `all_results[nom]["post"]` est vrai ;
- `self.patient_ids` = union de toutes les populations.

`add_row` refuse un bloc dont le nom est déjà une étape d'inclusion (les résultats s'écraseraient
dans `all_results`).

## `run_iter`

1. Ligne **Total** : effectif de chaque population, et pourcentage par rapport à la **première**
   population.
2. Pour chaque variable :
    - `step.execute(data, patient_ids=self.patient_ids, reference_date=self.reference_date)` : le bloc
      est calculé **une seule fois** sur l'union des populations ;
    - contrôle de cohérence entre `variable_type` et le dtype de la colonne (`numerical` → numérique,
      `boolean` → `pl.Boolean`) ;
    - pour chaque population : jointure interne sur ses patients, puis `compute_stats`.
3. Le générateur renvoie les statistiques de chaque variable (barre de progression de l'application).

## Statistiques : `stats.py`

Chaque fonction renvoie un DataFrame **d'une ligne**, une colonne par statistique formatée.

| Fonction | `variable_type` | Colonnes |
| --- | --- | --- |
| `compute_stats_boolean` | `boolean` | `(n, %)` (somme des vrais / effectif), `missing (n, %)` (nulls). |
| `compute_stats_quantitative` | `numerical` | `(mean ± std)`, `(median, IQR)`, `missing (n, %)` (null ou NaN), puis `[a - b[ (n, %)` par classe. |
| `compute_stats_categories` | `categorical` | `missing (n, %)`, puis une colonne par catégorie ou groupe de catégories. |

Détails :

- les arrondis sont à 2 décimales (`n_digits`) ;
- les pourcentages ont pour dénominateur l'effectif de la population (nulls compris) ;
- `subsets` numériques : bornes inférieures, la dernière classe est ouverte (`a+`) ;
- `subsets` catégoriels : chaque élément est une catégorie ou une liste de catégories regroupées
  (affichée `(a, b)`) ; sans `subsets`, une colonne par valeur distincte ;
- pour `categorical`, `missing` est calculé sur une colonne constante : il vaut toujours 0
  (limite connue).

## Mise en forme : `format_stats`

Chaque DataFrame de statistiques (une ligne, N colonnes) est **transposé** en N lignes ; les
populations sont jointes côte à côte sur le nom de la statistique ; une ligne d'en-tête contenant le
nom du bloc est insérée avant chaque variable. Le résultat est un `pandas.DataFrame` dont la première
colonne (sans nom) contient les libellés.

## Upload : `upload_stats`

1. Vide entièrement l'onglet `🔒 Results` (`updateCells` avec `fields="*"`, ce qui supprime aussi le
   formatage).
2. Écrit le DataFrame à partir de A1 (`gspread_pandas.Spread.df_to_sheet`).
3. Applique la mise en forme avec `gspread_formatting` : texte centré, en-tête en gras, lignes de
   titre de variable (toutes les cellules vides hors libellé) en gras sur fond bleu.

L'onglet `🔒 Results` doit exister dans la feuille (il est fourni par le template).
