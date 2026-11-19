# Catalogue des blocs

Un **bloc** est une brique de requête : il lit une ou plusieurs tables de la base RED et calcule une
valeur par patient. Le nom du bloc est ce que l'on écrit dans la colonne `block_type` du Google Sheet.

Le tableau ci-dessous est généré automatiquement à partir du code : il liste toujours les blocs
réellement disponibles.

{{ blocs_tableau() }}

## Deux familles de blocs

**Les blocs « patient »** lisent une information unique par patient (date de naissance, genre,
code postal…). Ils n'ont pas besoin d'`agg_func`.

**Les blocs « événement »** lisent des données qui peuvent apparaître plusieurs fois par patient
(consultations, prescriptions, antécédents, mesures…). Ils produisent une ligne par événement, puis
`agg_func` les résume en une valeur par patient (par défaut, souvent `COUNT(x)` : le nombre
d'événements).

La colonne **Daté** indique si le bloc fournit des dates (`start_date` / `end_date`) : seuls ces blocs
acceptent un `date_sql` et peuvent servir de `reference_date_block`.

## Lire une fiche de bloc

Chaque fiche suit le même plan :

1. **Fiche du bloc** (encadré généré depuis le code) : nom exact, niveau patient/événement, type de la
   valeur produite, dates fournies.
2. **Ce que fait le bloc**, en une phrase.
3. **Données utilisées** : les tables et colonnes de la base RED lues par le bloc.
4. **Détail du calcul** : ce que contient `x` et comment les lignes sont filtrées.
5. **Paramètres** (tableaux générés depuis le code) : valeurs par défaut des colonnes communes et
   paramètres spécifiques à mettre dans `supplementary_params`.
6. **Exemples** de lignes à copier dans le Google Sheet.
7. **Points d'attention**.

Pour le fonctionnement général des colonnes `value`, `agg_func`, `post_func` et `date_sql`, voir
[Paramètres des blocs](../guide/parametres.md). Les blocs qui recherchent dans le texte libre partagent
une page commune : [Recherche dans le texte libre](regex-nlp.md).
