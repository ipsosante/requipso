# Combiner des blocs

Une étape (ou une variable) peut combiner **plusieurs blocs** avec `AND` (et) / `OR` (ou). Par exemple :
« diabète codé en CIM10 **OU** en CISP2 **OU** traitement antidiabétique ».

## Comment écrire un groupe

Un groupe est une suite de **lignes consécutives** :

- la **première ligne** porte le `block_name` (et, dans l'onglet `Inclusion`, `parent_step`, `text`
  et `excluded_text`) ;
- les **lignes suivantes** ont un `block_name` vide (ou identique) et un `operator` (`AND` ou `OR`) ;
- **chaque ligne** a son propre `block_type` et ses propres paramètres (`value`, `post_func`, `date_sql`…).

| block_name | operator | text | block_type | value | expose_date_for_future_references |
| --- | --- | --- | --- | --- | --- |
| `diabete` | | Patients diabétiques | `CIM10` | `E11` | ☑ |
| | `OR` | | `CISP2` | `T90` | ☑ |
| | `OR` | | `PrescriptionATC` | `A10` | ☐ |

Cette étape retient les patients qui ont un code CIM10 `E11…`, **ou** un code CISP2 `T90…`, **ou**
une prescription d'un médicament de classe ATC `A10…` (antidiabétiques).

Le groupe s'arrête à la première ligne qui porte un **nouveau** `block_name`.

## Règles de calcul

- Chaque ligne est d'abord évaluée comme un bloc indépendant (vrai/faux), sur les mêmes patients.
  Un patient sans valeur pour une ligne est considéré comme `FALSE` pour cette ligne.
- Les opérateurs sont appliqués **de haut en bas, sans priorité** :
  `A OR B AND C` se lit `(A OR B) AND C`.
- Le résultat du groupe est vrai/faux : un groupe s'utilise donc comme une variable `boolean` dans
  l'onglet `Descriptive_table`.

!!! tip "Exprimer `(A OR B) AND (C OR D)`"
    Un groupe ne permet pas de parenthèses. Dans l'onglet `Inclusion`, utilisez deux étapes
    successives : l'une `A OR B`, puis l'autre `C OR D` (enchaîner deux étapes revient à un `AND`).

## Dates d'un groupe

Un groupe peut lui-même servir de `reference_date_block` à une étape ultérieure (ex. « dans l'année
qui suit le diagnostic de diabète, quelle qu'en soit la source »). La colonne
`expose_date_for_future_references` (case à cocher) choisit **quelles lignes fournissent leurs dates** :

- seules les lignes **cochées** fournissent des dates ;
- pour chaque ligne cochée, seules les dates des patients pour lesquels cette ligne est vraie sont gardées ;
- `reference_date_sql` (ex. `MIN(start_date)`) est ensuite calculé sur l'ensemble de ces dates.

Dans l'exemple ci-dessus, la date de référence « diabète » serait la plus ancienne date de code CIM10
ou CISP2, sans tenir compte des dates de prescription.

!!! warning "Cochez explicitement"
    Dans un groupe, une case vide sur la première ligne signifie « non exposée », et une valeur autre
    que `TRUE`/`FALSE` sur les lignes suivantes provoque une erreur
    (`Invalid expose_date_for_future_references`). Utilisez des cases à cocher.

## Ce que vous verrez dans le flowchart

Un groupe est **une seule boîte** du flowchart, avec le `text` de la première ligne. Les lignes
intermédiaires ne sont pas dessinées : elles sont calculées sous les noms `<block_name>_0`,
`<block_name>_1`, … (utile à savoir si un message d'erreur les mentionne).
