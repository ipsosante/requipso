# `EstVivant` : patient vivant

{{ bloc_resume("EstVivant") }}

## Ce que fait le bloc

Indique si le patient est **vivant à la date de référence**. C'est en général la première étape d'un
flowchart d'inclusion.

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `patient` | `patient_id`, `patient_death_date` |

## Détail du calcul

- `x` = `TRUE` si le patient n'a pas de date de décès, ou si la date de référence est **antérieure** à
  sa date de décès ; `FALSE` sinon.
- La date de décès est exposée comme `start_date` = `end_date` (vide pour les patients vivants).

## Paramètres

{{ bloc_parametres("EstVivant") }}

## Exemples

=== "Inclusion : vivants"

    | block_name | text | excluded_text | block_type |
    | --- | --- | --- | --- |
    | `vivants` | Patients vivants | Décédés | `EstVivant` |

=== "Tableau : % de décès"

    | block_name | block_type | variable_type | post_func |
    | --- | --- | --- | --- |
    | `deces` | `EstVivant` | `boolean` | `NOT x` |

## Points d'attention

- **N'utilisez pas `date_sql` avec ce bloc** : il filtrerait sur la date de décès, ce qui éliminerait
  tous les patients vivants (qui n'en ont pas).
- Le statut vital dépend de la qualité de la saisie de la date de décès dans le dossier médical.
