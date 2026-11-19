# `Consultations` : consultations

{{ bloc_resume("Consultations") }}

## Ce que fait le bloc

Renvoie les consultations du patient, éventuellement filtrées par motif, statut, centre ou
professionnel. Par défaut, il compte les consultations **terminées** et garde les patients qui en ont
au moins une.

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `consultation` | `patient_id`, `consultation_id`, `consultation_motive_category_label`, `consultation_status_label`, `consultation_start_datetime`, `consultation_end_datetime`, `medical_center_id`, `health_professional_id` |
| `medical_center` | `medical_center_id`, `medical_center_initials` |
| `health_professional` | `health_professional_id`, `health_professional_first_name`, `health_professional_last_name` |

## Détail du calcul

- Une ligne par consultation ; `x` = `TRUE`. `agg_func = COUNT(x)` compte les consultations.
- `start_date` / `end_date` = date et heure de début / fin de la consultation.
- Les filtres de `supplementary_params` s'additionnent (une consultation doit tous les respecter) :

| Paramètre | Filtre | Valeurs possibles (exemples) |
| --- | --- | --- |
| `consultation_status_label` | Statut. **Par défaut `["Ended"]`.** | `Ended`, `Canceled`, `Planned`, `Waiting`… |
| `consultation_motive_category_label` | Catégorie de motif. | `médecine générale adulte`, `santé de la femme`, `enfant et nourrisson`, `femme enceinte et jeune maman`, `sage-femme`, `programme Médecin Traitant Renforcé`, `addictologie`, `nutrition`… |
| `medical_center_initials` | Centre ipso (initiales). | `StM`, `Nat`, `Our`, `Ita`, `RiL`, `Bro`, `Men`, `StH`, `SMi`, `Bor` |
| `health_professional_names` | Professionnel, au format `Prénom Nom`. | `Marie Dupont` |

La liste complète des valeurs est dans [`RED.dbml`](../technique/donnees.md).

## Paramètres

{{ bloc_parametres("Consultations") }}

## Exemples

=== "Inclusion : consultation dans l'année"

    | block_name | block_type | date_sql |
    | --- | --- | --- |
    | `cs_12m` | `Consultations` | `start_date >= reference_date - INTERVAL '1 year' AND start_date <= reference_date` |

=== "Inclusion : au moins 3 consultations de médecine générale"

    | block_name | block_type | post_func | supplementary_params |
    | --- | --- | --- | --- |
    | `mg_3cs` | `Consultations` | `x >= 3` | `{"consultation_motive_category_label": ["médecine générale adulte"]}` |

=== "Tableau : nombre de consultations sur 12 mois"

    | block_name | block_type | variable_type | post_func | date_sql |
    | --- | --- | --- | --- | --- |
    | `nb_cs` | `Consultations` | `numerical` | `COALESCE(x, 0)` | `start_date >= reference_date - INTERVAL '1 year' AND start_date <= reference_date` |
## Points d'attention

- Les filtres attendent des **listes** : `{"medical_center_initials": ["StM"]}`, pas `"StM"`.
- Pour compter aussi les consultations annulées, remplacez le statut :
  `{"consultation_status_label": ["Ended", "Canceled"]}`.
- Une partie des consultations n'a pas d'heure de début renseignée (surtout les consultations
  annulées) : elles sont éliminées par tout `date_sql` portant sur `start_date`.
- Pour le nombre de consultations dans le tableau descriptif, utilisez `COALESCE(x, 0)` : sans cela,
  les patients sans consultation ont une valeur vide et sont exclus de la moyenne.
