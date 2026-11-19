# `RegexPrescription` : recherche textuelle dans les prescriptions

{{ bloc_resume("RegexPrescription") }}

## Ce que fait le bloc

Recherche des médicaments par leur **nom** dans les prescriptions (nom commercial ou dénomination
commune). C'est utile quand on ne connaît pas le code ATC ou qu'on veut cibler une spécialité
précise ; sinon, [`PrescriptionATC`](prescription-atc.md) est plus fiable et plus rapide.

Le fonctionnement des motifs, des pipelines `edsnlp.xxx` et des qualificatifs est décrit dans
[Recherche dans le texte libre](regex-nlp.md).

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `drug_prescription` | `patient_id`, `drug_prescription_id`, `drug_prescription_name`, `drug_prescription_common_name` |
| `drug_posology` | `drug_prescription_id`, `drug_posology_start_date`, `drug_posology_end_date` |

## Détail du calcul

- Pour chaque prescription, le texte analysé est le nom commercial suivi de la dénomination commune
  (une partie manquante est simplement ignorée).
- Une ligne par mention trouvée **et par ligne de posologie** ; `x` = le texte trouvé
  (ex. `DOLIPRANE`).
- `start_date` / `end_date` = début / fin de la posologie : on peut filtrer dans le temps
  (« traitement en cours à la date de référence »). Une fin vide (traitement en cours) vaut la date
  du jour.

## Paramètres

{{ bloc_parametres("RegexPrescription") }}

## Exemples

=== "Inclusion : paracétamol (nom commercial ou DCI)"

    | block_name | block_type | value |
    | --- | --- | --- |
    | `paracetamol` | `RegexPrescription` | `["doliprane", "dafalgan", "efferalgan", "paracetamol"]` |

=== "Inclusion : traitement en cours à la date de référence"

    | block_name | block_type | value | date_sql |
    | --- | --- | --- | --- |
    | `levothyrox_en_cours` | `RegexPrescription` | `levothyrox` | `start_date <= reference_date AND end_date >= reference_date` |

=== "Tableau : patients ayant eu de la metformine"

    | block_name | block_type | variable_type | value | post_func |
    | --- | --- | --- | --- | --- |
    | `metformine` | `RegexPrescription` | `boolean` | `metformine` | `COALESCE(x, 0) >= 1` |

## Points d'attention

- Écrivez les motifs **sans accents** ; la casse n'a pas d'importance (`doliprane` trouve
  `DOLIPRANE`). Voir [Recherche dans le texte libre](regex-nlp.md#1-des-motifs-expressions-regulieres).
- Les prescriptions **sans posologie** sont ignorées.
- `COUNT(x)` compte les mentions × lignes de posologie, pas les prescriptions : une prescription
  renouvelée avec deux posologies compte pour 2. Préférez un critère « au moins une »
  (`x >= 1`).
- Les qualificatifs (négation, hypothèse…) ont peu de sens sur un nom de médicament ; ils restent
  appliqués par défaut mais n'écartent en pratique rien.
