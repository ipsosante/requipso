# Exemple complet

Cet exemple construit une étude de bout en bout : **les adultes diabétiques de type 2 suivis en
médecin traitant renforcé (MTR) au 31/12/2024**, et leur description.

## 1. Onglet `Project`

|   | A | B | C | D |
| --- | --- | --- | --- | --- |
| **1** | Date de référence | `31/12/2024` | | |
| **2** | `Populations` | `adultes` | `diabete` | `diabete_mtr` |

Les populations sont renseignées en dernier, une fois les étapes d'inclusion nommées.

## 2. Onglet `Inclusion`

| block_name | parent_step | operator | text | excluded_text | block_type | value | date_sql | expose_date_for_future_references |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `vivants` | | | Patients vivants au 31/12/2024 | Décédés | `EstVivant` | | | |
| `adultes` | | | Patients majeurs | Mineurs | `Age` | | | |
| `diabete` | | | Diabète de type 2 | Sans diabète T2 | `CIM10` | `E11` | `start_date <= reference_date` | ☑ |
| | | `OR` | | | `CISP2` | `T90` | `start_date <= reference_date` | ☑ |
| | | `OR` | | | `PrescriptionATC` | `A10B` | `start_date <= reference_date` | ☐ |
| `diabete_mtr` | | | Suivis en MTR au 31/12/2024 | Sans MTR | `MedecinTraitant` | | `start_date <= reference_date AND end_date >= reference_date` | |

Ce qu'il faut remarquer :

- `vivants` et `adultes` utilisent les valeurs par défaut (`post_func` = `x` et `x>=18`), calculées à la
  date de référence.
- `diabete` est un [groupe](combiner-blocs.md) : code CIM10 `E11…` **ou** code CISP2 `T90…` **ou**
  antidiabétique non insulinique (ATC `A10B…`). Seuls les codes fournissent leur date (cases cochées),
  pour pouvoir dater le diagnostic plus loin.
- `diabete_mtr` utilise le paramètre par défaut `mtr_only = true` de `MedecinTraitant` et ne garde que
  les périodes de MTR **en cours** à la date de référence.

Premier lancement : vérifiez le flowchart et les effectifs avant d'aller plus loin.

## 3. Onglet `Descriptive_table`

| block_name | block_type | variable_type | variable_description | value | post_func | date_sql | reference_date_block | subsets |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `age` | `Age` | `numerical` | Âge (années) | | `x` | | | `[18, 45, 65, 75]` |
| `genre` | `Genre` | `categorical` | Genre | | `x` | | | `["féminin", "masculin"]` |
| `imc` | `Biometry` | `numerical` | Dernier IMC connu | `bmi` | | `start_date <= reference_date` | | `[0, 18.5, 25, 30]` |
| `hta` | `CIM10` | `boolean` | Hypertension | `I10` | `COALESCE(x, 0) >= 1` | `start_date <= reference_date` | | |
| `nb_cs_12m` | `Consultations` | `numerical` | Consultations sur 12 mois | | `COALESCE(x, 0)` | `start_date >= reference_date - INTERVAL '1 year' AND start_date <= reference_date` | | |
| `cs_post_diag` | `Consultations` | `boolean` | Consultation dans l'année suivant le diagnostic | | `COALESCE(x, 0) >= 1` | `start_date >= reference_date AND start_date <= reference_date + INTERVAL '1 year'` | `diabete` | |

Ce qu'il faut remarquer :

- `post_func = x` pour garder l'âge et le genre bruts (sinon on obtiendrait `x>=18` et `x='féminin'`).
- `imc` : `Biometry` garde par défaut la **dernière** mesure (`agg_func = LAST(x)`) et la valeur brute
  (`post_func = x`) ; le `date_sql` limite aux mesures antérieures à la date de référence.
- `hta` et `cs_post_diag` utilisent `COALESCE` pour compter comme « non » les patients sans événement.
- `cs_post_diag` prend comme date de référence, pour chaque patient, la **première date** de code
  diabète (CIM10 ou CISP2) de l'étape `diabete`. Pour les patients de la population `adultes` non
  diabétiques, il n'y a pas de date : ils sont comptés comme « non ».

## 4. Lancer et lire les résultats

Cliquez sur **« (re)lancer la pipeline »**. Comme l'onglet `Inclusion` n'a pas changé depuis le
premier lancement, seul le tableau descriptif est recalculé. Le tableau apparaît dans l'onglet
`🔒 Results` avec trois colonnes (`adultes`, `diabete`, `diabete_mtr`) et, pour chaque variable, les
statistiques décrites dans [Onglet Descriptive_table](onglet-tableau-descriptif.md#les-statistiques-calculees).

Enfin, exportez si besoin la liste des patients de `diabete_mtr` depuis la section
**Liste de patients** de l'application.
