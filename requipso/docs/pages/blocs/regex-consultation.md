# `RegexConsultation` : recherche dans les notes de consultation

{{ bloc_resume("RegexConsultation") }}

## Ce que fait le bloc

Recherche des mots ou expressions dans les **notes de consultation** (observation et conclusion
rédigées par le praticien). Par défaut, il garde les patients ayant au moins une mention, hors
négations et hypothèses.

Le fonctionnement des motifs, des pipelines `edsnlp.xxx` et des qualificatifs est décrit dans
[Recherche dans le texte libre](regex-nlp.md).

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `consultation` | `patient_id`, `consultation_id`, `consultation_observation`, `consultation_conclusion`, `consultation_start_datetime`, `consultation_end_datetime` |

## Détail du calcul

- Pour chaque consultation, le texte analysé est l'observation suivie de la conclusion.
- Une ligne par mention trouvée (hors qualificatifs écartés) ; `x` = le texte trouvé.
- `start_date` / `end_date` = début / fin de la consultation : on peut donc filtrer dans le temps
  (« mention dans l'année précédente »).

## Paramètres

{{ bloc_parametres("RegexConsultation") }}

## Exemples

=== "Inclusion : douleur thoracique mentionnée"

    | block_name | block_type | value |
    | --- | --- | --- |
    | `douleur_thoracique` | `RegexConsultation` | `douleurs? thoraciques?` |

=== "Inclusion : diabète (pipeline edsnlp) dans l'année"

    | block_name | block_type | value | date_sql |
    | --- | --- | --- | --- |
    | `diab_cs_12m` | `RegexConsultation` | `edsnlp.diabetes` | `start_date >= reference_date - INTERVAL '1 year' AND start_date <= reference_date` |

=== "Inclusion : en écartant aussi les antécédents familiaux"

    | block_name | block_type | value | supplementary_params |
    | --- | --- | --- | --- |
    | `cancer_sein` | `RegexConsultation` | `cancer du sein` | `{"qualifiers": ["negation", "hypothesis", "family"]}` |

=== "Tableau : nombre de mentions d'asthme"

    | block_name | block_type | variable_type | value | post_func |
    | --- | --- | --- | --- | --- |
    | `nb_mentions_asthme` | `RegexConsultation` | `numerical` | `asthme` | `COALESCE(x, 0)` |

## Points d'attention

- Si l'observation ou la conclusion est vide, seule l'autre partie est analysée ; les consultations
  sans aucun texte sont ignorées.
- Écrivez les motifs **sans accents** (voir [Recherche dans le texte libre](regex-nlp.md#1-des-motifs-expressions-regulieres)).
- `COUNT(x)` compte les **mentions**, pas les consultations : une note qui cite trois fois
  « asthme » compte pour 3.
- Les consultations annulées ne sont pas filtrées : leur texte est analysé s'il existe.
