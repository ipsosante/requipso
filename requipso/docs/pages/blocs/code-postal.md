# `CodePostal` : code postal de résidence

{{ bloc_resume("CodePostal") }}

## Ce que fait le bloc

Garde les patients dont le code postal de résidence fait partie d'une liste.

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `patient` | `patient_id`, `patient_residence_postal_code` |

## Détail du calcul

- Si `value` est renseignée (ex. `75011|75012`), seuls les patients dont le code postal est
  **exactement** l'un de ces codes sont gardés.
- Si `value` est vide, tous les patients ayant un code postal sont gardés.
- `x` = le code postal. Par défaut, `post_func = x IS NOT NULL`.

## Paramètres

{{ bloc_parametres("CodePostal") }}

## Exemples

=== "Inclusion : deux arrondissements"

    | block_name | block_type | value |
    | --- | --- | --- |
    | `paris_11_12` | `CodePostal` | `75011|75012` |

=== "Tableau : codes postaux"

    | block_name | block_type | variable_type | post_func |
    | --- | --- | --- | --- |
    | `cp` | `CodePostal` | `categorical` | `x` |

## Points d'attention

- La correspondance est exacte : `7501` ne trouve pas `75011`. Pour un préfixe, utilisez
  [`Departement`](departement.md) ou `post_func = x LIKE '750%'` avec `value` vide.
- Écrivez les codes avec leur zéro initial (`06000`, pas `6000`). Pour un code **seul**, préférez
  la forme liste `["06000"]` : un nombre isolé peut perdre son zéro ou provoquer l'erreur
  `Input should be a valid list` (voir [value](../guide/parametres.md#value-la-valeur-principale)).
- Ce bloc n'a pas de date : pas de `date_sql`.
