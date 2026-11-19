# `Genre` : genre déclaré

{{ bloc_resume("Genre") }}

## Ce que fait le bloc

Renvoie le genre déclaré du patient. Par défaut, il garde les patientes (`x=='féminin'`).

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `patient` | `patient_id`, `patient_gender_label` |

## Détail du calcul

`x` = le libellé du genre, parmi : `féminin`, `masculin`, `non genré`.

## Paramètres

{{ bloc_parametres("Genre") }}

## Exemples

=== "Inclusion : femmes"

    | block_name | block_type | post_func |
    | --- | --- | --- |
    | `femmes` | `Genre` | |

=== "Inclusion : hommes"

    | block_name | block_type | post_func |
    | --- | --- | --- |
    | `hommes` | `Genre` | `x = 'masculin'` |

=== "Tableau : répartition"

    | block_name | block_type | variable_type | post_func | subsets |
    | --- | --- | --- | --- | --- |
    | `genre` | `Genre` | `categorical` | `x` | `["féminin", "masculin", "non genré"]` |

## Points d'attention

- Les libellés sont en minuscules et accentués : `'féminin'`, pas `'Féminin'` ni `'feminin'`.
- Ce bloc n'a pas de date : pas de `date_sql`.
