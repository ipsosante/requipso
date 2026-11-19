# Erreurs fréquentes

Quand la feuille contient une erreur, l'application affiche un encadré rouge. Le message utile est en
général **la dernière ligne**. Cette page regroupe les messages les plus courants et leur solution.

!!! tip "Retrouver un message"
    Utilisez la recherche de votre navigateur (++ctrl+f++ ou ++cmd+f++) avec un morceau du message
    d'erreur.

## Onglet `Project`

| Message | Cause et solution |
| --- | --- |
| `Reference date not found in 'Project' cell B1` | La cellule B1 est vide. Saisissez la date de référence. |
| `time data '…' does not match format '%d/%m/%Y'` | La date de B1 n'est pas au format `JJ/MM/AAAA`. Corrigez-la (ex. `31/12/2024`). |
| `Expected cell A2 of 'Project' to be 'Populations'` | La cellule A2 doit contenir exactement `Populations`. |
| `No populations found in 'Project' row 2` | Aucune population en B2, C2… Ajoutez au moins un nom d'étape. |
| `Populations {…} not found in inclusion pipeline` | Un nom de population ne correspond à aucun `block_name` de l'onglet `Inclusion` (attention aux majuscules et aux espaces). |

## Structure des onglets

| Message | Cause et solution |
| --- | --- |
| `Missing required pipeline columns: […]` | Une colonne obligatoire a été renommée ou supprimée dans l'onglet `Inclusion`. Reprenez les en-têtes du template. |
| `Missing required descriptive columns: […]` | Idem pour l'onglet `Descriptive_table`. |
| `Sheet is empty` / `Descriptive sheet … is empty` | Aucune ligne n'a de `block_type`. |
| `Spreadsheet … not found` | La feuille n'est plus dans le dossier Drive Requipso. |

## Noms d'étapes et références

| Message | Cause et solution |
| --- | --- |
| `Unknown block type: '…'. Available: […]` | Le `block_type` est mal orthographié. La liste des blocs valides est affichée dans le message (et dans le [catalogue](../blocs/index.md)). |
| `Step … already exists` | Deux étapes portent le même `block_name`. Les noms doivent être uniques. |
| `Step … already exists in inclusion pipeline, use a different name` | Une variable de `Descriptive_table` porte le nom d'une étape d'`Inclusion`. Renommez la variable. |
| `Parent step None not found` | Le `parent_step` ne correspond à aucune étape **située plus haut**. Vérifiez l'orthographe et l'ordre des lignes. |
| `A parent step is not permitted for the first step` | La première étape ne doit pas avoir de `parent_step`. |
| `reference_date_block '…' not found — it must appear earlier in the sheet.` | Le bloc de référence n'existe pas ou est défini plus bas. Déplacez-le au-dessus. |
| `KeyError: 'dates'` | Le `reference_date_block` désigne un bloc **sans dates** (ex. `Genre`), ou un groupe dont aucune ligne n'est cochée dans `expose_date_for_future_references`. |

## Groupes de lignes

| Message | Cause et solution |
| --- | --- |
| `Invalid operator None in block '…'` | Une ligne sans `block_name` est rattachée au groupe précédent mais n'a pas d'`operator`. Soit vous avez oublié le `block_name` d'une nouvelle étape, soit l'opérateur manque. |
| `Invalid operator 'and' in block '…'` | L'opérateur doit être `AND` ou `OR`, en majuscules. |
| `Invalid expose_date_for_future_references … in block '…'` | Sur les lignes 2, 3… d'un groupe, la colonne doit être une case à cocher (`TRUE`/`FALSE`). |

## Paramètres

| Message | Cause et solution |
| --- | --- |
| `Field required` (sur `value`) | Ce bloc exige une `value` (ex. `Biometry` : le libellé de la mesure). |
| `Input should be a valid list` (sur `value`) | La valeur a été lue comme un nombre (ex. code postal seul). Écrivez-la sous forme de liste : `["75011"]`. Voir [value](parametres.md#value-la-valeur-principale). |
| `Extra inputs are not permitted` | Un nom de paramètre de `supplementary_params` n'existe pas pour ce bloc. Vérifiez la fiche du bloc. |
| `Must contain 'start_date' or 'end_date'` | `date_sql` ou `reference_date_sql` ne mentionne aucune date. |
| `cannot compare 'date/datetime/time' to a string value` | Une date fixe est écrite comme un texte. Écrivez `DATE '2024-01-01'`. |
| `unsupported function 'mean'` | Utilisez `AVG(x)`. Voir les [fonctions disponibles](parametres.md#agg_func-resumer-plusieurs-evenements). |
| `SQLSyntaxError` / `SQLInterfaceError` | La formule `agg_func`, `post_func` ou `date_sql` est mal écrite (parenthèse, guillemet ou mot-clé manquant). |
| `Specified edsnlp pipe '…' not found in edsnlp.pipes.` | Le nom après `edsnlp.` ne correspond à aucun pipeline NLP. Voir [Recherche dans le texte libre](../blocs/regex-nlp.md). |

## Tableau descriptif

| Message | Cause et solution |
| --- | --- |
| `Invalid variable_type '…'` | `variable_type` doit valoir `boolean`, `numerical` ou `categorical`. |
| `Column … is not numeric (got Boolean), but variable_type is numerical. Maybe check post_func ?` | La valeur par défaut de `post_func` transforme le nombre en vrai/faux. Écrivez `post_func = x`. |
| `Column … is not boolean (got …), but variable_type is boolean.` | La valeur finale n'est pas vrai/faux. Ajoutez une condition dans `post_func` (ex. `x >= 1`) ou changez `variable_type`. |

## Les effectifs semblent faux

Pas de message d'erreur, mais un résultat surprenant ? Quelques pistes :

- **Une étape à 0 patient** : vérifiez la `value` (codes avec la bonne casse, ex. `E11` et non `e11`),
  et le `date_sql` (une période trop étroite).
- **Un `date_sql` sans effet** : sur un bloc sans dates (`Genre`, `Departement`, `CodePostal`,
  `RegexPatientObservation`), `date_sql` est ignoré sans message d'erreur.
- **Trop de patients exclus après une branche** : un `parent_step` vide désigne l'étape écrite juste
  au-dessus, pas forcément celle de votre branche.
- **Beaucoup de `missing`** dans le tableau : c'est normal pour les blocs qui comptent des événements,
  voir [`COALESCE`](onglet-tableau-descriptif.md#boolean).
- **La date de référence a changé mais pas les effectifs** : rechargez la page de l'application
  (voir [Recalcul automatique](application.md#recalcul-automatique)).
