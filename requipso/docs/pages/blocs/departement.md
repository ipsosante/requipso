# `Departement` : département de résidence

{{ bloc_resume("Departement") }}

## Ce que fait le bloc

Garde les patients qui résident dans un ou plusieurs départements, d'après les **deux premiers
caractères** de leur code postal.

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `patient` | `patient_id`, `patient_residence_postal_code` |

## Détail du calcul

- Si `value` est renseignée (ex. `75|92|93|94`), seuls les patients dont le code postal commence par
  l'un de ces numéros sont gardés.
- Si `value` est vide, tous les patients ayant un code postal sont gardés.
- `x` = le **code postal complet** (ex. `75011`), pas le numéro de département.
- Par défaut, `post_func = x IS NOT NULL` : vrai pour les patients du ou des départements demandés.

## Paramètres

{{ bloc_parametres("Departement") }}

## Exemples

=== "Inclusion : Paris et petite couronne"

    | block_name | block_type | value |
    | --- | --- | --- |
    | `idf_centre` | `Departement` | `75|92|93|94` |

=== "Tableau : répartition par département"

    | block_name | block_type | variable_type | post_func |
    | --- | --- | --- | --- |
    | `dept` | `Departement` | `categorical` | `SUBSTR(x, 1, 2)` |

## Points d'attention

- Le filtre porte sur les **2 premiers caractères** : les départements d'outre-mer (`971`, `972`…)
  sont tous regroupés sous `97`. Utilisez [`CodePostal`](code-postal.md) pour plus de précision.
- Pour la Corse, les codes postaux commencent par `20` (pas `2A`/`2B`).
- Pour un département **seul**, écrivez `["75"]` ou `["06"]` plutôt que `75` : un nombre isolé peut
  perdre son zéro ou provoquer l'erreur `Input should be a valid list`.
- Environ 7 % des patients n'ont pas de code postal renseigné.
- Ce bloc n'a pas de date : pas de `date_sql`.
