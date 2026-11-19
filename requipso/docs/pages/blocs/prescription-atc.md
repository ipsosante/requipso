# `PrescriptionATC` : prescriptions par classe ATC

{{ bloc_resume("PrescriptionATC") }}

## Ce que fait le bloc

Recherche les **prescriptions médicamenteuses** du patient dont le code ATC commence par l'un des
codes demandés. Par défaut, il garde les patients ayant au moins une telle prescription.

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `drug_prescription` | `patient_id`, `drug_prescription_id`, `drug_prescription_atc` |
| `drug_posology` | `drug_prescription_id`, `drug_posology_start_date`, `drug_posology_end_date` |

## Détail du calcul

- Les prescriptions dont le code ATC **commence par** l'un des codes de `value` sont gardées
  (`A10` trouve `A10BA02`…). La recherche respecte les majuscules.
- Chaque prescription est associée à ses **posologies** : une ligne par posologie, avec ses dates.
- `x` = le code ATC ; `agg_func = COUNT(x)` compte les lignes de posologie.
- `start_date` / `end_date` = début / fin de la posologie.

La classification ATC est hiérarchique : plus le code est long, plus il est précis.

| Niveau | Exemple | Signification |
| --- | --- | --- |
| 1 | `A` | Voies digestives et métabolisme |
| 2 | `A10` | Médicaments du diabète |
| 3 | `A10B` | Hypoglycémiants, insulines exclues |
| 5 | `A10BA02` | Metformine |

## Paramètres

{{ bloc_parametres("PrescriptionATC") }}

## Exemples

=== "Inclusion : traitement antidiabétique"

    | block_name | block_type | value |
    | --- | --- | --- |
    | `antidiab` | `PrescriptionATC` | `A10` |

=== "Inclusion : statine en cours à la date de référence"

    | block_name | block_type | value | date_sql |
    | --- | --- | --- | --- |
    | `statine` | `PrescriptionATC` | `C10AA` | `start_date <= reference_date AND end_date >= reference_date` |

=== "Inclusion : metformine prescrite dans l'année"

    | block_name | block_type | value | date_sql |
    | --- | --- | --- | --- |
    | `metformine_12m` | `PrescriptionATC` | `A10BA02` | `start_date >= reference_date - INTERVAL '1 year' AND start_date <= reference_date` |

=== "Tableau : nombre de classes d'antihypertenseurs"

    | block_name | block_type | variable_type | value | agg_func | post_func |
    | --- | --- | --- | --- | --- | --- |
    | `nb_antihta` | `PrescriptionATC` | `numerical` | `C02|C03|C07|C08|C09` | `COUNT(DISTINCT x)` | `COALESCE(x, 0)` |

## Points d'attention

- `COUNT(x)` compte des **lignes de posologie**, pas des ordonnances : une même prescription peut en
  avoir plusieurs. Pour un nombre de médicaments différents, utilisez `COUNT(DISTINCT x)`.
- Les codes doivent être en **majuscules** (`C10`, pas `c10`).
- Une prescription sans posologie n'est pas trouvée (elle n'a pas de date).
