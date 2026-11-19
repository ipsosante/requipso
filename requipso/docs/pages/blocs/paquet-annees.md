# `PaquetAnnees` : tabagisme en paquets-années

{{ bloc_resume("PaquetAnnees") }}

## Ce que fait le bloc

Estime la consommation de tabac du patient en **paquets-années** (PA). Par défaut, il garde les
patients ayant fumé (`x>0`).

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `smoking` | `patient_id`, `smoking_product`, `smoking_cigarettes_per_day`, `smoking_start_date`, `smoking_end_date` |
| `patient_observation` | `patient_id`, `patient_observation_label` (`lifestyle_data`), `patient_observation_value` (texte libre) |

## Détail du calcul

Le bloc combine deux sources :

**1. Les données structurées** (table `smoking`, saisie structurée du tabac dans le dossier) :

- seules les périodes de consommation de **cigarettes** commençant avant la date de calcul sont
  gardées ;
- une période sans date de fin (tabagisme en cours) court jusqu'à la date de calcul ;
- PA d'une période = (cigarettes par jour / 20) × durée en années ;
- `x` = somme des PA de toutes les périodes, arrondie à 1 décimale ;
- un patient présent dans la table `smoking` sans période de cigarette (ex. non-fumeur déclaré,
  e-cigarette) a `x = 0`.

**2. Le texte libre** (si `use_nlp` est vrai, ce qui est le cas par défaut) : les notes « mode de vie »
(`lifestyle_data`) sont analysées par le pipeline NLP `tobacco` d'edsnlp, qui repère les mentions
du type « tabac 20 PA ». La valeur extraite est utilisée **uniquement pour les patients sans donnée
structurée**.

Avec `use_nlp`, la date de calcul est la **date du jour** (les notes ne sont pas datées) ; sans NLP,
c'est la date de référence.

## Paramètres

{{ bloc_parametres("PaquetAnnees") }}

## Exemples

=== "Inclusion : fumeurs ou ex-fumeurs"

    | block_name | block_type |
    | --- | --- |
    | `fumeurs` | `PaquetAnnees` |

=== "Inclusion : au moins 20 PA"

    | block_name | block_type | post_func |
    | --- | --- | --- |
    | `gros_fumeurs` | `PaquetAnnees` | `x >= 20` |

=== "Tableau : PA en classes"

    | block_name | block_type | variable_type | post_func | subsets |
    | --- | --- | --- | --- | --- |
    | `pa` | `PaquetAnnees` | `numerical` | `x` | `[0, 10, 20, 40]` |

## Points d'attention

- Les patients sans aucune information tabac (ni structurée, ni dans le texte) ont une valeur vide :
  ils sont **exclus** de l'inclusion et comptés en `missing` dans le tableau.
- Avec `use_nlp` (défaut), le calcul n'est pas « à la date de référence » mais à la date du jour, et
  les valeurs issues du texte n'ont pas de date : évitez `date_sql` avec ce bloc.
- L'analyse NLP de toutes les notes « mode de vie » est **lente** : placez ce bloc après des étapes qui
  réduisent la population.
