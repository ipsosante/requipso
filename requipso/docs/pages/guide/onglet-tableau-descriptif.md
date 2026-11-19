# Onglet `Descriptive_table`

L'onglet `Descriptive_table` décrit les **variables** du tableau descriptif. Chaque variable est
calculée pour chacune des [populations](onglet-projet.md#les-populations-ligne-2) déclarées dans
l'onglet `Project`. Le résultat est écrit dans l'onglet `🔒 Results`.  

La struture de cet onglet est très proche de l'onglet `Inclusion`

## Le principe

- Une ligne (ou un [groupe de lignes](combiner-blocs.md)) = une variable du tableau.
- On utilise les **mêmes blocs** que dans l'onglet `Inclusion`, mais leur résultat n'a pas à être
  vrai/faux : ce peut être un nombre (âge, IMC), une catégorie (genre) ou un booléen (diabétique ou non).
- La colonne `variable_type` indique comment résumer la variable.

## Les colonnes

| Colonne | Obligatoire | Description |
| --- | --- | --- |
| `block_name` | Oui | Nom unique de la variable. **Il doit être différent de tous les noms de l'onglet `Inclusion`.** C'est ce nom qui apparaît comme titre dans `🔒 Results`. |
| `block_type` | Oui | Le bloc à utiliser (voir le [catalogue](../blocs/index.md)). |
| `variable_type` | Oui | `boolean`, `numerical` ou `categorical` (voir ci-dessous). |
| `variable_description` | Non | Libellé lisible, affiché dans la barre de progression de l'application. |
| `subsets` | Non | Découpage en classes (variables numériques) ou regroupement de catégories (voir ci-dessous). |
| `operator` | Pour les groupes | `AND` / `OR`, comme dans l'onglet `Inclusion`. |
| `value`, `agg_func`, `post_func`, `date_sql`, `reference_date_block`, `reference_date_sql`, `supplementary_params` | Non | Identiques à l'onglet `Inclusion`. Voir [Paramètres](parametres.md). |

!!! tip "Référencer une étape d'inclusion"
    `reference_date_block` peut pointer vers une étape de l'onglet `Inclusion` (ex. la date du premier
    diagnostic) ou vers une variable définie plus haut dans cet onglet.

## Choisir `variable_type` et `post_func`

C'est le point qui demande le plus d'attention. Les valeurs par défaut des blocs sont pensées pour
l'inclusion (elles renvoient vrai/faux). Pour une variable numérique ou catégorielle, il faut donc
**écrire `x` dans `post_func`** pour garder la valeur brute.

| Je veux… | `variable_type` | `post_func` | Exemple |
| --- | --- | --- | --- |
| un pourcentage de patients | `boolean` | une condition, ou vide si la valeur par défaut convient | `CIM10` avec `value = I10` → % d'hypertendus |
| une moyenne / médiane | `numerical` | `x` | `Age` avec `post_func = x` |
| une répartition par catégorie | `categorical` | `x` | `Genre` avec `post_func = x` |
| un nombre d'événements | `numerical` | `x` (ou `COALESCE(x, 0)`) | `Consultations` avec `agg_func = COUNT(x)` |

Si le type ne correspond pas, Requipso s'arrête avec un message du type
`Column age is not numeric (got Boolean), but variable_type is numerical. Maybe check post_func ?`.

## Les statistiques calculées

### `boolean`

| Ligne | Contenu |
| --- | --- |
| `(n, %)` | Nombre et pourcentage de patients pour lesquels la valeur est vraie. |
| `missing (n, %)` | Nombre et pourcentage de patients sans valeur. |

!!! warning "« missing » pour les blocs qui comptent des événements"
    Pour les blocs du type « au moins un événement » (`CIM10`, `Consultations`, `PrescriptionATC`…),
    un patient qui n'a **aucun** événement n'a pas de valeur : il est compté en `missing`, pas en
    « faux ». Le pourcentage `(n, %)` reste juste (il est calculé sur toute la population), mais si
    vous voulez que ces patients soient comptés comme « non », écrivez
    `post_func = COALESCE(x, 0) >= 1`.

### `numerical`

| Ligne | Contenu |
| --- | --- |
| `(mean ± std)` | Moyenne ± écart-type. |
| `(median, IQR)` | Médiane [1er quartile - 3e quartile]. |
| `missing (n, %)` | Patients sans valeur. |
| `[a - b[ (n, %)` | Une ligne par classe si `subsets` est renseigné. |

`subsets` contient les **bornes inférieures** des classes. Par exemple `[0, 18, 45, 65]` donne les
classes `[0 - 18[`, `[18 - 45[`, `[45 - 65[` et `65+`. Les valeurs inférieures à la première borne ne
sont comptées dans aucune classe.

### `categorical`

Une ligne `(n, %)` par catégorie. Sans `subsets`, toutes les valeurs rencontrées sont listées.

`subsets` permet de choisir et d'ordonner les catégories, et d'en **regrouper** certaines :

```text
["féminin", ["masculin", "non genré"]]
```

donne deux lignes : `féminin` et `(masculin, non genré)`.

!!! note "Valeurs manquantes des variables catégorielles"
    La ligne `missing` d'une variable catégorielle affiche actuellement toujours 0. Les patients
    sans valeur ne sont comptés dans aucune catégorie : leur nombre est la différence entre l'effectif
    de la population et la somme des catégories.

## Lire l'onglet `🔒 Results`

Le tableau a une colonne par population, dans l'ordre de l'onglet `Project`. Chaque variable commence
par une ligne de titre (en bleu, avec le `block_name`), suivie de ses statistiques :

| | adultes | diabete |
| --- | --- | --- |
| **Total** | | |
| (n, %) | 52000 (100.0%) | 4100 (7.88%) |
| **age** | | |
| (mean ± std) | 47.2 ± 17.9 | 63.1 ± 12.4 |
| (median, IQR) | 45.0 [33.1 - 60.2] | 64.0 [55.3 - 72.0] |
| missing (n, %) | 0 (0.0%) | 0 (0.0%) |

La ligne `Total` donne l'effectif de chaque population, en pourcentage de la **première** population.
Tous les autres pourcentages sont calculés par rapport à l'effectif de **la population de la colonne**.

Le tableau est aussi affiché dans l'application, en bas de page.

## Exemple

| block_name | block_type | variable_type | variable_description | value | agg_func | post_func | subsets |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `age` | `Age` | `numerical` | Âge (années) | | | `x` | `[18, 45, 65]` |
| `genre` | `Genre` | `categorical` | Genre | | | `x` | `["féminin", "masculin"]` |
| `hta` | `CIM10` | `boolean` | Hypertension artérielle | `I10` | | `COALESCE(x, 0) >= 1` | |
| `imc` | `Biometry` | `numerical` | IMC (dernier connu) | `bmi` | | | `[0, 18.5, 25, 30]` |
| `nb_cs` | `Consultations` | `numerical` | Nombre de consultations sur 1 an | | | `COALESCE(x, 0)` | |

Pour `nb_cs`, on ajoute `date_sql = start_date >= reference_date - INTERVAL '1 year' AND start_date <= reference_date`.
Pour `imc`, `post_func` est vide car la valeur par défaut de `Biometry` est déjà `x`.
