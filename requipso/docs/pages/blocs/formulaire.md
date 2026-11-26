# `Formulaire` : score d'un formulaire

{{ bloc_resume("Formulaire") }}

## Ce que fait le bloc

Renvoie la **réponse principale** (le score final) d'un formulaire rempli par le patient (PHQ-9,
GAD-7, EPWORTH…). Par défaut, il renvoie le score du **dernier** formulaire rempli, tel quel.

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `form` | `form_id`, `patient_id`, `form_name`, `form_completed_at` |
| `form_answer` | `form_id`, `form_answer_label`, `form_answer_value` |

## Détail du calcul

- `value` = le nom du formulaire (obligatoire), tel qu'il apparaît dans `form_name` (ex. `PHQ-9`).
  La comparaison est **exacte** (casse et tirets compris).
- Seule la réponse de libellé `score` est gardée : c'est la réponse principale de la plupart des
  formulaires. Un formulaire sans réponse `score` est ignoré.
- Une ligne par formulaire rempli ; `x` = le score ; `start_date` = `end_date` = date de complétion.
- `agg_func = LAST(x)` garde le formulaire **le plus récent** (après `date_sql`).

Formulaires présents dans RED : `PRECAR`, `GAD-7`, `PHQ-9`, `GDS-15`, `IADL`, `TFEQ R21`, `DUKE`,
`EPWORTH`, `ACT`, `MBI`, `EPDS`, `BERLIN`, `FTCD`, `MAC ISAAC`, `MMS`, `COPD`, `FACE`, `GENÈVE`,
`SPPB`, `FGS`.

## Paramètres

{{ bloc_parametres("Formulaire") }}

## Exemples

=== "Inclusion : dépression modérée ou plus (dernier PHQ-9)"

    | block_name | block_type | value | post_func | date_sql |
    | --- | --- | --- | --- | --- |
    | `phq9_10` | `Formulaire` | `PHQ-9` | `x >= 10` | `start_date <= reference_date` |

=== "Inclusion : au moins un GAD-7 rempli dans l'année"

    | block_name | block_type | value | agg_func | post_func | date_sql |
    | --- | --- | --- | --- | --- | --- |
    | `gad7_12m` | `Formulaire` | `GAD-7` | `COUNT(x)` | `x >= 1` | `start_date >= reference_date - INTERVAL '1 year' AND start_date <= reference_date` |

=== "Tableau : score EPWORTH maximal"

    | block_name | block_type | variable_type | value | agg_func |
    | --- | --- | --- | --- | --- |
    | `epworth_max` | `Formulaire` | `numerical` | `EPWORTH` | `MAX(x)` |

## Points d'attention

- Sans `date_sql`, « le dernier formulaire » peut être **postérieur** à la date de référence.
  Ajoutez `start_date <= reference_date` pour le dernier score connu à cette date.
- Ici `post_func = x` par défaut : pour l'inclusion, il faut écrire une condition (ex. `x >= 10`),
  sinon l'étape ne renvoie pas un vrai/faux.
- Certains formulaires (`DUKE`, `MBI`, `TFEQ R21`, `BERLIN`…) exposent surtout des sous-scores
  (`depression`, `anxiete`…) que ce bloc ne renvoie pas.
