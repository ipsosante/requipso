# Ajouter un bloc

Ce tutoriel ajoute un bloc `Acte` qui recherche des **actes cotés** (table `act`) par code, datés par
leur consultation.

## 1. Choisir le fichier

Les blocs sont rangés par domaine dans `requipso/pipes/` (`patient.py`, `atcd.py`, `biometry.py`…).
Créez un nouveau module si aucun ne convient, ici `requipso/pipes/act.py`. **Aucun enregistrement
n'est nécessaire** : tout module de `requipso.pipes` est parcouru par `build_block_registry`.

## 2. Écrire la classe de paramètres

Partez de la classe de base la plus proche (voir [Paramètres](parametres-internes.md)) et surchargez les
défauts adaptés au cas « au moins un événement » de l'onglet `Inclusion` :

```python
from pydantic import Field

from .params import MultiStringParam, TransformFunc


class ActeParams(MultiStringParam):
    value: list[str] = Field(
        default=[],
        description="[HELP] Code d'acte / Codes séparés de '|' / Liste de codes (ex. 'JKHD001').",
    )
    agg_func: TransformFunc = Field(default="COUNT(x)", description="Aggregation: count acts.")
    post_func: TransformFunc = Field(default="x>=1", description="Post-transform: True if at least one act.")
    include_mtr_package: bool = Field(
        default=True, description="If False, drop acts included in the MTR package."
    )
```

- La description de `value` commence par `[HELP]` : c'est l'aide affichée dans `🔒 Blocks`.
- Les champs supplémentaires (`include_mtr_package`) deviennent des clés de `supplementary_params`.
- `extra="forbid"` est hérité : une clé inconnue dans le Sheet lèvera une erreur explicite.

## 3. Écrire le bloc

```python
import polars as pl

from .base import BlockConfig, OutputType, TableBlock


class Acte(TableBlock[ActeParams]):
    config = BlockConfig(
        output_type=OutputType.CATEGORY,
        block_type="event",
        date_column=("consultation_start_datetime", "consultation_end_datetime"),
        description="Retourne les actes cotés du patient dont le code commence par les codes spécifiés.",
    )

    def transform(  # type: ignore[override]
        self,
        act: pl.DataFrame,
        consultation: pl.DataFrame,
    ) -> pl.DataFrame:
        acts = act.filter(pl.col("act_value").str.contains(self.params.get_regex(prefix=True)))
        if not self.params.include_mtr_package:
            acts = acts.filter(~pl.col("act_is_in_mtr_package"))

        return acts.join(
            consultation.select(
                "consultation_id", self.start_date_column, self.end_date_column
            ),
            on="consultation_id",
            how="inner",
        ).select(
            "patient_id",
            pl.col("act_value").alias(self.name),
            self.start_date_column,
            self.end_date_column,
        )
```

Le contrat de `transform` :

| Règle | Pourquoi |
| --- | --- |
| Les **noms des arguments** sont des noms de tables RED (`act`, `consultation`). | `execute` charge les tables d'après la signature et les filtre sur les patients d'entrée. |
| Renvoyer `patient_id` et une colonne **`self.name`** (la valeur `x`). | Agrégation, `post_func` et résultats travaillent sur cette colonne. |
| Renvoyer les colonnes de `config.date_column`. | `execute` les copie dans `start_date` / `end_date`. |
| Ne pas agréger, ne pas filtrer sur les dates, ne pas rajouter les patients manquants. | C'est le rôle de `execute`, piloté par `agg_func`, `date_sql` et la jointure finale. |
| Utiliser `self.reference_date` si le calcul dépend de la date de référence. | Il est résolu avant l'appel (voir `Age`). |

Si le bloc a besoin d'un traitement NLP, composez un [`RegexProcessor`](nlp.md) dans `__init__`.

## 4. Vérifier que le bloc est découvert

```bash
uv run python -c "from requipso.pipeline_loader import build_block_registry; print(sorted(build_block_registry()))"
```

`Acte` doit apparaître. Sinon, le module a probablement une erreur d'import (elle est ignorée en
silence par le registre) : importez-le directement pour voir l'erreur.

## 5. Tester sur les données

```python
import datetime
from requipso import Data
from requipso.pipes.act import Acte, ActeParams

data = Data("/chemin/vers/final_data")
block = Acte(name="frottis", params=ActeParams(value="JKHD001", date_sql="start_date <= reference_date"))
block.execute(data, reference_date=datetime.datetime(2024, 12, 31))

data.all_results["frottis"]["post"]    # une ligne par patient
data.all_results["frottis"]["dates"]   # les actes retenus
```

## 6. Mettre à jour les onglets de référence du Sheet

Les onglets `🔒 Blocks` et `🔒 Definitions` du template sont générés depuis le code :

```bash
uv run python scripts/signature_exporter.py            # écrit dans le Sheet de référence (SHEET_ID)
uv run python scripts/signature_exporter.py --json     # affiche aussi les signatures en JSON
```

Voir [Export des signatures de blocs](export-signatures.md) pour le détail.

## 7. Documenter le bloc

1. Créez `requipso/docs/pages/blocs/acte.md` en suivant le plan des autres fiches, avec les macros :

{% raw %}
    ```markdown
    # `Acte` : actes cotés

    {{ bloc_resume("Acte") }}

    ## Paramètres

    {{ bloc_parametres("Acte") }}
    ```
{% endraw %}

2. Ajoutez la page dans `nav` de `requipso/docs/mkdocs.yml`.
3. Ajoutez le bloc dans `FAMILIES` et `PAGES` de `requipso/docs/macros.py` (sinon il apparaît dans une
   famille « Autres », sans lien, dans le catalogue).
4. Vérifiez avec `uv run mkdocs build -f requipso/docs/mkdocs.yml --strict`.

Les tableaux de paramètres et la fiche résumée sont générés : ils restent à jour tant que les
descriptions des `Field` et de `BlockConfig` le sont.
