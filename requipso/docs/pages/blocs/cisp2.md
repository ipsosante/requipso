# `CISP2` : antécédents codés en CISP2

{{ bloc_resume("CISP2") }}

## Ce que fait le bloc

Recherche dans les **antécédents** du patient les pathologies correspondant à des codes CISP2
(Classification internationale des soins primaires). Il fonctionne exactement comme
[`CIM10`](cim10.md), avec la terminologie CISP2.

## Données utilisées

| Table | Colonnes | Rôle |
| --- | --- | --- |
| `concept` | `concept_id`, `concept_code`, `concept_vocabulary` | Codes CISP2 (`cisp`) et pathologies ipso (`ipso_pathology`). |
| `concept_relationship` | `concept_id_1`, `concept_id_2` | Correspondance CISP2 → pathologie ipso. |
| `patient_condition` | `patient_id`, `patient_condition_id`, `patient_observation_id`, `condition_concept_id`, `condition_concept_type` | Pathologies reconnues dans les antécédents. |
| `patient_observation` | `patient_observation_id`, `patient_observation_label` | Rubrique du dossier où l'antécédent est écrit. |
| `patient_condition_date` | `patient_condition_id`, `patient_condition_date` | Dates associées à chaque antécédent. |

## Détail du calcul

1. Les codes CISP2 qui **commencent par** l'un des codes de `value` sont sélectionnés (`T9` trouve
   `T90`, `T93`…). La recherche respecte les majuscules.
2. Ils sont traduits en pathologies ipso, puis les antécédents correspondants des patients sont gardés
   (type `pathology`, rubriques antécédents médicaux, chirurgicaux ou gynécologiques).
3. `x` = le code CISP2 ; `agg_func = COUNT(x)` compte les antécédents trouvés.
4. `start_date` / `end_date` = plus ancienne / plus récente date associée à l'antécédent.

## Paramètres

{{ bloc_parametres("CISP2") }}

## Exemples

=== "Inclusion : diabète non insulino-dépendant"

    | block_name | block_type | value |
    | --- | --- | --- |
    | `diabete_cisp` | `CISP2` | `T90` |

=== "Inclusion : diabète codé en CIM10 ou CISP2"

    | block_name | operator | block_type | value |
    | --- | --- | --- | --- |
    | `diabete` | | `CIM10` | `E11` |
    | | `OR` | `CISP2` | `T90` |

=== "Tableau : % avec HTA (K86/K87)"

    | block_name | block_type | variable_type | value | post_func |
    | --- | --- | --- | --- | --- |
    | `hta_cisp` | `CISP2` | `boolean` | `K86|K87` | `COALESCE(x, 0) >= 1` |

## Points d'attention

Les mêmes que pour [`CIM10`](cim10.md#points-dattention). Comme chaque pathologie ipso est reliée à
la fois à un code CIM10 et à un code CISP2, les deux blocs trouvent souvent les mêmes patients :
combinez-les en `OR` pour être exhaustif.
