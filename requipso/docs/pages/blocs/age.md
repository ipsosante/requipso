# `Age` : âge du patient

{{ bloc_resume("Age") }}

## Ce que fait le bloc

Calcule l'âge de chaque patient, en années, **à la date de référence**. Par défaut, il garde les
patients majeurs (`x>=18`).

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `patient` | `patient_id`, `patient_birth_date` |

## Détail du calcul

- `x` = (date de référence − date de naissance) en jours / 365, arrondi à 1 décimale
  (ex. `47.3`).
- La date de référence est celle de l'onglet `Project`, ou celle de chaque patient si
  `reference_date_block` est renseigné (ex. « âge au diagnostic »).
- La date de naissance est exposée comme `start_date` = `end_date`.

## Paramètres

{{ bloc_parametres("Age") }}

## Exemples

=== "Inclusion : patients majeurs"

    | block_name | block_type | post_func |
    | --- | --- | --- |
    | `adultes` | `Age` | |

=== "Inclusion : 40-75 ans"

    | block_name | block_type | post_func |
    | --- | --- | --- |
    | `age_40_75` | `Age` | `x >= 40 AND x < 75` |

=== "Tableau : âge en classes"

    | block_name | block_type | variable_type | post_func | subsets |
    | --- | --- | --- | --- | --- |
    | `age` | `Age` | `numerical` | `x` | `[18, 45, 65, 75]` |

=== "Tableau : âge au diagnostic"

    | block_name | block_type | variable_type | post_func | reference_date_block |
    | --- | --- | --- | --- | --- |
    | `age_diag` | `Age` | `numerical` | `x` | `diabete` |

## Points d'attention

- Pour une variable numérique, **écrivez `post_func = x`**, sinon vous obtenez un vrai/faux « majeur ».
- Avec `reference_date_block`, un patient sans date dans le bloc référencé n'a pas d'âge (valeur vide).
- L'âge est calculé sur 365 jours par an : à quelques jours de l'anniversaire, il peut y avoir un
  léger décalage dû aux années bissextiles.
- Un `date_sql` porterait sur la **date de naissance** (ex. `start_date >= DATE '2000-01-01'` pour les
  patients nés depuis 2000).
