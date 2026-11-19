# `MedecinTraitant` : médecin traitant (MT / MTR)

{{ bloc_resume("MedecinTraitant") }}

## Ce que fait le bloc

Renvoie les **périodes** pendant lesquelles le patient a eu un médecin traitant ipso. Par défaut,
seules les périodes de **médecin traitant renforcé** (MTR) sont prises en compte, et le bloc garde les
patients ayant au moins une période.

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `regular_doctor_history` | `patient_id`, `health_professional_id`, `regular_doctor_is_external`, `regular_doctor_is_mtr`, `regular_doctor_start_date`, `regular_doctor_end_date` |

## Détail du calcul

- Les périodes sans médecin identifié (`health_professional_id` vide) sont ignorées.
- Si `include_external` est faux (défaut), les médecins traitants **externes** à ipso sont ignorés.
- Si `mtr_only` est vrai (défaut), seules les périodes **MTR** sont gardées ; sinon MT classiques et
  MTR sont gardés.
- Une ligne par période ; `x` = `TRUE`. `agg_func = COUNT(x)` compte les périodes.
- `start_date` / `end_date` = début / fin de la période. Une période en cours (sans date de fin) a
  pour `end_date` la date du jour.

## Paramètres

{{ bloc_parametres("MedecinTraitant") }}

## Exemples

=== "Inclusion : en MTR à la date de référence"

    | block_name | block_type | date_sql |
    | --- | --- | --- |
    | `mtr` | `MedecinTraitant` | `start_date <= reference_date AND end_date >= reference_date` |

=== "Inclusion : MT ou MTR ipso, à un moment quelconque"

    | block_name | block_type | supplementary_params |
    | --- | --- | --- |
    | `mt_ipso` | `MedecinTraitant` | `{"mtr_only": false}` |

=== "Tableau : % ayant déclaré un MT (y compris externe)"

    | block_name | block_type | variable_type | post_func | supplementary_params |
    | --- | --- | --- | --- | --- |
    | `a_un_mt` | `MedecinTraitant` | `boolean` | `COALESCE(x, 0) >= 1` | `{"mtr_only": false, "include_external": true}` |

## Points d'attention

- **Sans `date_sql`, le bloc regarde toute l'histoire du patient**, y compris après la date de
  référence. Pour « en MTR à la date de référence », utilisez le filtre ci-dessus.
- La date de début d'un MTR peut servir de date de référence pour la suite
  (`reference_date_block = mtr`, `reference_date_sql = MIN(start_date)` : date d'entrée en MTR).
