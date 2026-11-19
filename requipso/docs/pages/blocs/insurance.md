# `Insurance` : couverture d'assurance maladie

{{ bloc_resume("Insurance") }}

## Ce que fait le bloc

Renvoie les droits d'assurance maladie du patient (AMO, complémentaire, C2S, AME…) correspondant aux
types demandés. Par défaut, il garde les patients ayant au moins un de ces droits.

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `patient_insurance` | `patient_id`, `patient_insurance_type_label`, `patient_insurance_start_date`, `patient_insurance_end_date` |

## Détail du calcul

- Les types de `value` sont comparés **exactement** au libellé du droit.
- Une ligne par droit ; `x` = le libellé. `agg_func = COUNT(x)` compte les droits.
- `start_date` / `end_date` = début / fin du droit (fin vide = droit en cours, date du jour).

Libellés disponibles : `AMO`, `Complémentaire santé`, `ALD`, `C2S`, `Accident du travail`,
`Maternité`, `CMU`, `AME`, `Autre droit 100%`, `ACS`, `SMG`.

## Paramètres

{{ bloc_parametres("Insurance") }}

## Exemples

=== "Inclusion : bénéficiaires C2S ou AME"

    | block_name | block_type | value |
    | --- | --- | --- |
    | `precarite` | `Insurance` | `C2S|AME` |

=== "Inclusion : droit en cours à la date de référence"

    | block_name | block_type | value | date_sql |
    | --- | --- | --- | --- |
    | `c2s_active` | `Insurance` | `C2S` | `start_date <= reference_date AND end_date >= reference_date` |

=== "Tableau : % avec complémentaire santé"

    | block_name | block_type | variable_type | value | post_func |
    | --- | --- | --- | --- | --- |
    | `complementaire` | `Insurance` | `boolean` | `Complémentaire santé` | `COALESCE(x, 0) >= 1` |

## Points d'attention

- `value` est **obligatoire en pratique** : vide, le bloc ne trouve aucun droit.
- Respectez exactement les libellés (majuscules, accents) : `Complémentaire santé`, pas
  `complementaire sante`.
- Une petite partie des droits n'a pas de date de début : ils sont éliminés par un `date_sql` portant
  sur `start_date`.
