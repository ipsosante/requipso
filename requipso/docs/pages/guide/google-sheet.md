# Le Google Sheet

Toute la définition d'une étude tient dans un Google Sheet copié depuis le **template**. Requipso lit
certains onglets et en écrit d'autres. Les onglets dont le nom commence par 🔒 sont remplis
automatiquement : **ne les modifiez pas à la main**.

| Onglet | Vous le remplissez ? | Rôle |
| --- | --- | --- |
| `Project` | Oui | Date de référence de l'étude et liste des populations à décrire. Voir [Onglet Project](onglet-projet.md). |
| `Explications` | Non (à lire) | Aide-mémoire intégré au template. |
| `Inclusion` | Oui | Les étapes du flowchart d'inclusion. Voir [Onglet Inclusion](onglet-inclusion.md). |
| `Descriptive_table` | Oui | Les variables du tableau descriptif. Voir [Onglet Descriptive_table](onglet-tableau-descriptif.md). |
| `🔒 Results` | Non | Le tableau descriptif calculé, réécrit à chaque exécution. |
| `🔒 Blocks` | Non | Référence : la liste des blocs disponibles, leur description et leurs valeurs par défaut. |
| `🔒 Definitions` | Non | Référence : les paramètres spécifiques de chaque bloc (à mettre dans `supplementary_params`). |


## Règles générales de saisie

Ces règles valent pour les onglets `Inclusion` et `Descriptive_table`.

**La première ligne contient les noms de colonnes.** Ne les renommez pas : Requipso les recherche par
leur nom exact (`block_name`, `block_type`, `value`…). L'ordre des colonnes n'a en revanche pas
d'importance.

**Une ligne sans `block_type` est ignorée.** Vous pouvez donc laisser des lignes vides, ou écrire des
notes dans une ligne sans bloc.

**Une cellule vide signifie « valeur par défaut du bloc ».** Par exemple, le bloc `Age` a par défaut
`post_func = x>=18` : si vous laissez `post_func` vide, Requipso garde les patients majeurs.
Pour obtenir la valeur brute (l'âge lui-même), il faut écrire explicitement `x`. Les valeurs par
défaut de chaque bloc sont indiquées dans le [catalogue des blocs](../blocs/index.md) et dans l'onglet
`🔒 Blocks`.

**Les listes de valeurs** s'écrivent au choix :

- en séparant par une barre verticale : `E11|E10|E14` ;
- au format liste : `["E11", "E10", "E14"]`.

**Les cases à cocher** (colonne `expose_date_for_future_references`) doivent être de vraies cases à
cocher Google Sheet (valeurs `TRUE` / `FALSE`).

**Les dates** s'écrivent `JJ/MM/AAAA` dans l'onglet `Project`. Dans les formules SQL, on écrit
`DATE 'AAAA-MM-JJ'` (voir [Paramètres](parametres.md)).

## Ce que Requipso écrit dans votre feuille et votre Drive

- L'onglet `🔒 Results` est **entièrement effacé puis réécrit** à chaque calcul du tableau descriptif.
- Le flowchart est déposé dans le dossier Drive sous le nom `<nom de votre feuille>.png`.
  S'il existe déjà, il est remplacé.
