# `ALD` : affections de longue durée

{{ bloc_resume("ALD") }}

## Ce que fait le bloc

Renvoie les ALD (affections de longue durée) du patient correspondant aux codes demandés. Par défaut,
il garde les patients ayant au moins une de ces ALD.

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `patient_ald` | `patient_id`, `patient_ald_code`, `patient_ald_start_date`, `patient_ald_end_date` |

## Détail du calcul

- Les codes de `value` sont comparés **exactement** au code ALD (`08` ne trouve pas `08.1`).
- Les codes à un chiffre sont complétés par un zéro : `8` devient `08`, `6.1` devient `06.1`.
- Une ligne par ALD trouvée ; `x` = le code ALD. `agg_func = COUNT(x)` compte les ALD.
- `start_date` / `end_date` = début / fin de l'ALD (fin vide = ALD en cours, date du jour).

Codes ALD présents dans les données : `01` à `30`, avec des sous-codes pour certaines (ex. `06.1`,
`14.2`, `21.1`, `30.17`…). L'ALD 30 regroupe les cancers.

## Paramètres

{{ bloc_parametres("ALD") }}

## Exemples

=== "Inclusion : ALD diabète"

    | block_name | block_type | value |
    | --- | --- | --- |
    | `ald_diabete` | `ALD` | `08` |

=== "Inclusion : ALD 30 et tous ses sous-codes"

    | block_name | block_type | value |
    | --- | --- | --- |
    | `ald_cancer` | `ALD` | `30.*` |

=== "Inclusion : ALD en cours à la date de référence"

    | block_name | block_type | value | date_sql |
    | --- | --- | --- | --- |
    | `ald_diab_active` | `ALD` | `["08"]` | `start_date <= reference_date AND end_date >= reference_date` |

=== "Tableau : nombre d'ALD"

    | block_name | block_type | variable_type | post_func |
    | --- | --- | --- | --- |
    | `nb_ald` | `ALD` | `numerical` | `COALESCE(x, 0)` |

## Points d'attention

- Avec `value` vide, le bloc ne trouve **aucune** ALD. Pour « au moins une ALD quelle qu'elle soit »,
  utilisez `value = .*` ou le bloc [`Insurance`](insurance.md) avec `value = ALD`.
- Les codes sont interprétés comme des expressions régulières : `30.*` signifie « `30` suivi de
  n'importe quoi » (donc `30`, `30.1`, `30.17`…).
- Une grande partie des lignes de `patient_ald` n'a pas de code renseigné : ces ALD ne sont jamais
  trouvées par ce bloc.
- Un code seul comme `08` peut être lu comme un nombre par Google Sheet : écrivez `["08"]` en cas
  d'erreur `Input should be a valid list`.
