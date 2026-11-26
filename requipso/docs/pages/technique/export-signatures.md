# Export des signatures de blocs

`requipso/signature_exporter.py` inspecte le code pour lister **tous les blocs disponibles** avec
leur description et leurs paramètres (`scripts/signature_exporter.py` le lance en ligne de commande).
Il sert à deux choses :

- remplir les onglets de référence `🔒 Blocks` et `🔒 Definitions` du Google Sheet template, que
  les utilisateurs consultent pour savoir quels blocs et paramètres utiliser ;
- alimenter cette documentation : `requipso/docs/macros.py` s'en sert pour générer les fiches résumées et
  les tableaux de paramètres des pages [Blocs](../blocs/index.md).

Il n'y a donc rien à maintenir à la main : il suffit que les `Field(description=…)` et la
`BlockConfig` des blocs soient à jour.

## Quand le lancer

Après toute modification visible par les utilisateurs d'un bloc : ajout ou suppression d'un bloc,
changement de description, de valeur par défaut ou de paramètre spécifique. La documentation, elle,
se met à jour toute seule au prochain `mkdocs build` / `mkdocs serve`.

## Utilisation

```bash
uv run python scripts/signature_exporter.py                   # met à jour le Sheet template
uv run python scripts/signature_exporter.py --json            # idem + affiche le JSON
uv run python scripts/signature_exporter.py --json --gsheet "" # JSON seul, sans toucher au Sheet
uv run python scripts/signature_exporter.py --gsheet <ID>     # écrit dans une autre feuille
```

| Option | Effet |
| --- | --- |
| `--gsheet ID` | Identifiant de la feuille à mettre à jour (la longue chaîne de l'URL). **Par défaut, `SHEET_ID`** défini en tête du script : le script écrit donc dans le Sheet même sans option. `--gsheet ""` désactive l'écriture. |
| `--json` | Affiche toutes les signatures en JSON sur la sortie standard. |
| `--output-dir` | Sans effet actuellement : l'écriture des CSV est commentée dans `main()`. |

Dans tous les cas, le script termine en affichant une ligne par bloc découvert :

```text
requipso.pipes.patient.Departement [patient] -> DepartementParams
```

L'écriture dans le Sheet utilise le compte Google de l'utilisateur (même connexion que
l'application, voir [Développement](developpement.md#installation)) : il faut avoir les droits
d'édition sur la feuille.

!!! warning "Les onglets sont effacés puis réécrits"
    `🔒 Blocks` et `🔒 Definitions` sont vidés à chaque exécution. Toute modification manuelle de ces
    onglets est perdue. Ils sont créés s'ils n'existent pas.

## Comment les blocs sont découverts

`BlockExporter()` fait toute la découverte à sa construction :

1. Il importe tous les modules de `requipso.pipes` (`pkgutil.walk_packages`). Un module qui ne
   s'importe pas est ignoré avec un message `[warn] Could not import …` : **ses blocs disparaissent
   alors de l'export**, surveillez ce message.
2. Il garde les classes qui héritent de `TableBlock` et sont définies dans `requipso.pipes`.
3. Pour chacune, il lit :
    - la classe de paramètres, depuis la base générique `TableBlock[XxxParams]` : un bloc qui
      n'hérite pas directement de `TableBlock[…]` n'a donc aucun paramètre spécifique détecté ;
    - `config.description`, `config.block_type` et la présence de `config.date_column` (`has_date`) ;
    - les champs Pydantic de la classe de paramètres, séparés en **communs** (ceux de
      `BlockParams`, avec les valeurs par défaut propres au bloc) et **spécifiques** (tous les
      autres).
4. Il ajoute la signature de `Negation` (`_negation_signature`), qui n'est pas un `TableBlock` mais
   doit apparaître dans `🔒 Blocks`. Elle n'a que `value` (aide tirée de `Negation.value_help`), et
   sa description vient de `Negation.description`.
5. Les signatures sont triées par module puis par nom de bloc.

Chaque bloc donne un `BlockSignature` :

```json
{
  "module": "requipso.pipes.patient",
  "block_name": "Departement",
  "block_type": "patient",
  "params_name": "DepartementParams",
  "params_module": "requipso.pipes.patient",
  "description": "Retourne le département du patient.",
  "common_parameters": {
    "value": {
      "type": "list[str]",
      "default": "[HELP] Département / Départements séparés de '|' / Liste de départements.",
      "description": "[HELP] Département / Départements séparés de '|' / Liste de départements."
    },
    "...": {}
  },
  "specific_parameters": {},
  "has_date": false
}
```

Particularités du format :

- Pour `value`, le champ `default` contient la **description** du paramètre (l'aide `[HELP] …`),
  pas sa valeur par défaut : c'est ce texte qui s'affiche dans `🔒 Blocks`.
- Un paramètre obligatoire a `default: null`.
- Les types sont rendus en texte (`str | None` devient `str`). Les fonctions (`agg_func`,
  `post_func`…) donnent un type peu lisible (`Callable[[<class 'polars.expr.expr.Expr'>], Expr]`).
- Une valeur par défaut non sérialisable en JSON est remplacée par son `repr`.

## Contenu des onglets générés

**`🔒 Blocks`**: une ligne par bloc.

| Colonne | Contenu |
| --- | --- |
| `block`, `type`, `description` | Nom de la classe, `patient` / `event`, `BlockConfig.description`. |
| une colonne par paramètre commun | Valeur par défaut du bloc (aide `[HELP]` pour `value`), vide si aucune. |
| `has_date` | `True` si le bloc fournit des dates (utilisable avec `date_sql`). |
| `supplementary_params` | Les paramètres spécifiques et leurs valeurs par défaut, en JSON : un modèle à copier dans la colonne `supplementary_params` du Sheet. |

**`🔒 Definitions`**: une ligne par couple (bloc, paramètre spécifique), avec `parameter_name`,
`parameter_type`, `default_value` et `description`.

## Utilisation depuis Python

```python
from pathlib import Path

from requipso.signature_exporter import BlockExporter

exporter = BlockExporter()
for sig in exporter.signatures:
    print(sig.block_name, sig.params_name, sig.has_date)

exporter.to_json()                      # chaîne JSON
exporter.to_csv(Path("out"))            # blocks_common_parameters.csv + blocks_specific_parameters.csv
exporter.to_gsheet("<spreadsheet_key>") # onglets 🔒 Blocks / 🔒 Definitions
```

`to_csv` écrit deux fichiers au format proche des onglets, sans les descriptions des paramètres
spécifiques ni la colonne `supplementary_params`. Les fichiers `blocks_*.csv` présents à la racine du
dépôt viennent d'anciennes exécutions et ne sont plus à jour.
