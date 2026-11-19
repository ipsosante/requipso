# `RegexPatientObservation` : recherche dans les observations patient

{{ bloc_resume("RegexPatientObservation") }}

## Ce que fait le bloc

Recherche des mots ou expressions dans les **observations patient** du dossier : antécédents
médicaux et chirurgicaux, mode de vie, allergies, prévention… Par défaut, il garde les patients ayant
au moins une mention, hors négations et hypothèses.

Le fonctionnement des motifs, des pipelines `edsnlp.xxx` et des qualificatifs est décrit dans
[Recherche dans le texte libre](regex-nlp.md).

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `patient_observation` | `patient_id`, `patient_observation_id`, `patient_observation_label`, `patient_observation_value` |

## Détail du calcul

- Seules les observations des rubriques listées dans `patient_observation_label` sont analysées.
- Une ligne par mention trouvée (hors qualificatifs écartés) ; `x` = le texte trouvé.
- Les observations ne sont **pas datées** : ce bloc n'a pas de `start_date` / `end_date`.

Rubriques disponibles pour `patient_observation_label` :

| Rubrique | Contenu | Analysée par défaut |
| --- | --- | --- |
| `medical_background_data` | Antécédents médicaux | Oui |
| `chirurgical_background_data` | Antécédents chirurgicaux | Oui |
| `lifestyle_data` | Mode de vie | Oui |
| `allergies_data` | Allergies | Oui |
| `prevention_data` | Prévention (vaccins, dépistages) | Oui |
| `family_background_data` | Antécédents familiaux | Non |
| `gynecologic_background_data` | Antécédents gynécologiques | Non |
| `gynecologic_monitoring_data` | Suivi gynécologique | Non |
| `pregnancies_data` | Grossesses | Non |
| `birth_data` | Naissance | Non |
| `smoking_pack_years` | Paquets-années (voir [`PaquetAnnees`](paquet-annees.md)) | Non |

## Paramètres

{{ bloc_parametres("RegexPatientObservation") }}

## Exemples

=== "Inclusion : apnée du sommeil dans les antécédents"

    | block_name | block_type | value | supplementary_params |
    | --- | --- | --- | --- |
    | `saos` | `RegexPatientObservation` | `apnee\w* du sommeil|saos` | `{"patient_observation_label": ["medical_background_data"]}` |

=== "Inclusion : diabète (pipeline edsnlp)"

    | block_name | block_type | value |
    | --- | --- | --- |
    | `diabete_texte` | `RegexPatientObservation` | `edsnlp.diabetes` |

=== "Inclusion : allergie à la pénicilline"

    | block_name | block_type | value | supplementary_params |
    | --- | --- | --- | --- |
    | `allergie_peni` | `RegexPatientObservation` | `penicilline|amoxicilline` | `{"patient_observation_label": ["allergies_data"]}` |

=== "Tableau : antécédents familiaux de cancer du sein"

    | block_name | block_type | variable_type | value | post_func | supplementary_params |
    | --- | --- | --- | --- | --- | --- |
    | `atcd_fam_sein` | `RegexPatientObservation` | `boolean` | `cancer du sein` | `COALESCE(x, 0) >= 1` | `{"patient_observation_label": ["family_background_data"], "qualifiers": ["negation", "hypothesis"]}` |

## Points d'attention

- **Pas de `date_sql`** avec ce bloc : les observations n'ont pas de date. Il ne peut pas non plus
  servir de `reference_date_block`.
- Le bloc ne tient pas compte de la date de référence : il lit l'état actuel du dossier, y compris des
  informations ajoutées après cette date.
- Pour chercher dans les antécédents familiaux, ajoutez `family_background_data` **et** ne mettez pas
  `family` dans `qualifiers` (sinon les mentions familiales sont écartées).
- Écrivez les motifs **sans accents**.
- Un `patient_observation_label` seul peut s'écrire comme un texte : `{"patient_observation_label": "lifestyle_data"}`.
