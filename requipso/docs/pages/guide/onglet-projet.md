# Onglet `Project`

L'onglet `Project` contient deux informations, à des emplacements **fixes** :

|   | A | B | C | D |
| --- | --- | --- | --- | --- |
| **1** | **Date de référence (double-click sur B1 pour choisir la date)** | `01/01/2024` | | |
| **2** | **`Populations`** | `Adultes` | `Diabétiques` | `Diabétiques_suivis` |

## La date de référence (cellule B1)

C'est la date « à laquelle on regarde » les patients. Elle sert par défaut à tous les blocs :

- `Age` calcule l'âge **à cette date** ;
- `EstVivant` vérifie que le patient est vivant **à cette date** ;
- les filtres temporels (`date_sql`) peuvent la comparer aux dates des événements, par exemple
  « consultation dans l'année précédant la date de référence ».

Format obligatoire : `JJ/MM/AAAA` (ex. `31/12/2023`).

!!! tip "Une date de référence par patient"
    Il est aussi possible d'utiliser une date propre à chaque patient (par exemple la date de son
    premier diagnostic de diabète) pour certains blocs. C'est le rôle de la colonne
    `reference_date_block` : voir [Paramètres](parametres.md#date-de-reference-par-patient).

## Les populations (ligne 2)

La cellule **A2 doit contenir exactement** le mot `Populations`. Les cellules suivantes (B2, C2, …)
contiennent chacune le nom d'une population, à renseigner via une liste déroulante.

Une population est simplement le **nom d'une étape** de l'onglet `Inclusion` (sa colonne
`block_name`). Les patients ayant franchi cette étape forment une colonne du tableau descriptif.

- Les noms doivent correspondre **exactement** (majuscules, accents, espaces) à un `block_name` de
  l'onglet `Inclusion` (utilisez directement la liste déroulante pour être sûr).
- L'ordre des cellules donne l'ordre des colonnes du tableau descriptif.
- La **première** population sert de dénominateur pour la ligne `Total` du tableau : les pourcentages
  de cette ligne sont exprimés par rapport à elle. Placez donc en premier la population la plus large.

!!! info "Quand remplir les populations ?"
    Les populations ne sont utilisées que pour le tableau descriptif. Vous pouvez commencer par
    construire et vérifier votre flowchart, puis renseigner les populations une fois les noms
    d'étapes stabilisés.

!!! warning "Changer la date de référence"
    L'application ne recalcule l'inclusion que si l'onglet `Inclusion` a changé. Si vous modifiez
    **uniquement** la date de référence, rechargez la page de l'application (ou relancez-la) pour
    forcer un recalcul complet. Voir [Utiliser l'application](application.md#recalcul-automatique).
