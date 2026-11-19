# Données et stockage

## La base RED

Les données sont un export de la base **RED** : un fichier parquet par table (`patient.parquet`,
`consultation.parquet`…). Le schéma complet, avec la description de chaque colonne, les valeurs
possibles des énumérations et des statistiques de remplissage, est disponible via (ce site)[https://dbdocs.io/thomas.petitjean/RED]

Les tables utilisées par les blocs actuels :

| Table | Contenu | Blocs |
| --- | --- | --- |
| `patient` | Une ligne par patient : naissance, décès, genre, code postal. | `Age`, `EstVivant`, `Genre`, `Departement`, `CodePostal`, `Biometry` (IMC) |
| `consultation` | Consultations, motifs, statuts, textes libres. | `Consultations`, `RegexConsultation` |
| `medical_center` | Centres ipso. | `Consultations` |
| `health_professional` | Professionnels de santé. | `Consultations` |
| `regular_doctor_history` | Périodes de médecin traitant (MT / MTR). | `MedecinTraitant` |
| `biometry` | Mesures biométriques. | `Biometry` |
| `patient_ald` | Affections de longue durée. | `ALD` |
| `patient_insurance` | Droits d'assurance maladie. | `Insurance` |
| `drug_prescription`, `drug_posology` | Prescriptions et posologies. | `PrescriptionATC` |
| `patient_observation` | Rubriques texte du dossier (antécédents, mode de vie…). | `RegexPatientObservation`, `CIM10`, `CISP2`, `PaquetAnnees` |
| `patient_condition`, `patient_condition_date` | Pathologies reconnues dans les antécédents et leurs dates. | `CIM10`, `CISP2` |
| `concept`, `concept_relationship` | Terminologies (CIM10, CISP2, ipso) et correspondances. | `CIM10`, `CISP2` |
| `smoking` | Tabagisme structuré. | `PaquetAnnees` |

Toutes les tables patient-dépendantes ont une colonne `patient_id`.

## `Data`

`requipso.data.Data` est le conteneur central, passé de bloc en bloc.

```python
from requipso import Data

data = Data("/chemin/vers/final_data")    # ou "s3://bucket/prefix"
data.patient                               # pl.DataFrame de la table patient
data.get_table("consultation")
```

- À la construction, **toutes** les tables du dossier sont chargées en mémoire
  (`load_data`). `Data(path, empty=True)` charge seulement les schémas (0 ligne), utile pour des tests.
- `Data(path, patient_ids=serie)` restreint dès le chargement toutes les tables à un sous-ensemble de
  patients (pratique pour développer sur un échantillon).
- Les tables sont accessibles par attribut (`data.patient`), par index (`data["patient"]`) ou par
  `get_table`.

### Les résultats : `all_results`

`data.all_results` est un `defaultdict(dict)` indexé par nom de bloc :

```python
data.all_results["adultes"]["post"]    # une ligne par patient : patient_id, adultes
data.all_results["adultes"]["dates"]   # une ligne par événement : patient_id, adultes, start_date, end_date
```

| Clé | Contenu | Présent |
| --- | --- | --- |
| `"post"` | Valeur finale par patient, après agrégation et `post_func`. Pour un `CombinedBlock`, contient aussi les colonnes des sous-blocs. | Toujours |
| `"dates"` | Événements datés retenus après `date_sql` (dates converties en `pl.Date`). Dans le pipeline d'inclusion, restreint aux patients ayant franchi l'étape. | Seulement si le bloc a des dates |

`data.reset()` vide `all_results` ; l'application l'appelle avant chaque nouveau calcul d'inclusion.

## Entrées / sorties : `io.py`

`Data` délègue la lecture à un `BaseIO`, choisi selon le chemin :

| Classe | Chemin | Remarques |
| --- | --- | --- |
| `LocalIO` | Dossier local | Liste `*.parquet` du dossier. |
| `S3IO` | `s3://bucket/prefix` | Utilise `boto3` ; exige `AWS_ACCESS_KEY_ID` et `AWS_SECRET_ACCESS_KEY` dans l'environnement. |

Les deux implémentent `list_tables`, `read_table(name, n_rows)` et `write_table(name, df)`.

## Google : `google.py`

`GoogleConnector` s'authentifie avec le **compte Google de l'utilisateur** (OAuth), via
`get_user_credentials()` :

- le client OAuth est lu dans `google_oauth_client.json` (à la racine du dépôt, à côté du package
  `requipso`) ;
- au premier appel, un navigateur s'ouvre pour la connexion ; le jeton obtenu est mis en cache dans
  `~/.config/requipso/google_token.json` et rafraîchi automatiquement ensuite ;
- on peut aussi passer des identifiants déjà obtenus : `GoogleConnector(credentials=creds)`.

L'utilisateur doit avoir accès au dossier Drive Requipso (lecture pour les Sheets, édition pour
`upload_file`).

- `list_sheets()` liste les Google Sheets du dossier Drive Requipso (`folder_id`).
- `set_spreadsheet(nom)` ouvre une feuille (via `gspread-pandas`).
- `open_sheet(onglet, header_rows=1)` lit un onglet en `pandas.DataFrame`. Le contenu transite par un
  CSV pour que pandas infère les types de façon homogène (nombres, booléens `TRUE`/`FALSE`) ; les
  cellules vides deviennent `None`.
- `upload_file(chemin, nom)` dépose ou remplace un fichier dans le dossier Drive et renvoie son URL.

!!! warning "Secret"
    `google_oauth_client.json` identifie l'application et peut être versionné : l'écran de
    consentement est « Interne », seuls les comptes `@ipsosante.fr` peuvent s'y connecter. En
    revanche, `google_token.json` donne accès au Drive de l'utilisateur et ne doit jamais être
    partagé.

!!! note "Inférence de types par pandas"
    Le passage par CSV a une conséquence visible côté utilisateur : si une colonne ne contient que des
    nombres, pandas la lit en `int`/`float`, et les paramètres de type liste (`MultiStringParam`)
    échouent (`Input should be a valid list`). Voir le
    [guide utilisateur](../guide/parametres.md#value-la-valeur-principale).
