# Utiliser l'application

L'application Requipso s'ouvre dans le navigateur (voir [Démarrage](demarrage.md#4-lancer-lapplication)).
Elle se lit de haut en bas : chaque section n'apparaît que lorsque la précédente est complète.

## 1. Choisir le dossier de données

Le sélecteur **« choisir le dossier local contenant les données »** permet de naviguer dans vos
dossiers. Sélectionnez le dossier qui contient les fichiers `.parquet` (par ex. `patient.parquet`).

- Le sélecteur s'ouvre directement à côté du dernier dossier utilisé.
- Le chargement des données en mémoire prend quelques secondes à quelques minutes selon la machine.

## 2. Choisir le Google Sheet

La liste **« choisir le Google Sheet »** affiche toutes les feuilles du dossier Drive Requipso. La
dernière feuille utilisée est présélectionnée.

Tant que le dossier et la feuille ne sont pas choisis, l'application affiche
« renseigner le dossier contenant les données et choisir le Google Sheet pour continuer ».

Une fois les deux choisis, l'application rappelle le dossier et un lien vers la feuille, et affiche
le bouton vert **« (re)lancer la pipeline »**.

## 3. Lancer le calcul

Cliquez sur **« (re)lancer la pipeline »**. Requipso relit **à chaque clic** le contenu de la feuille :
vous pouvez donc modifier la feuille, puis recliquer, sans relancer l'application.

1. **Inclusion** : une barre de progression `inclusion ...` affiche chaque étape et son effectif
   (`bloc adultes : 52000 patients`). Le flowchart est ensuite dessiné et déposé sur le Drive.
2. **Tableau descriptif** : une barre `tableau descriptif ...` affiche chaque variable calculée. Le
   résultat est écrit dans l'onglet `🔒 Results` de la feuille.
3. **Résultats** : l'application affiche les liens vers le tableau et le flowchart, puis le flowchart
   et le tableau eux-mêmes.

!!! tip "Les blocs NLP sont plus lents"
    Les blocs qui analysent du texte libre (`RegexConsultation`, `RegexPatientObservation`,
    `PaquetAnnees`) peuvent prendre plusieurs minutes sur toute la base. Placez-les de préférence
    **après** des étapes qui réduisent déjà la population : ils ne traitent que les patients retenus
    par l'étape parente.

### Recalcul automatique

Si l'onglet `Inclusion` n'a pas changé depuis le dernier calcul, l'application affiche
« pipeline déjà exécutée, pas de recalcul nécessaire » et ne recalcule que le tableau descriptif.
C'est pratique pour ajuster le tableau sans attendre l'inclusion.

Seul l'onglet `Inclusion` est surveillé. Si vous changez **uniquement** la date de référence (onglet
`Project`), **rechargez la page** du navigateur pour forcer un recalcul complet.

### En cas d'erreur

Si quelque chose ne va pas dans la feuille, l'application affiche un encadré rouge avec le message
d'erreur. Le message utile est en général la **dernière ligne**. La page
[Erreurs fréquentes](erreurs.md) explique les messages les plus courants.

Le message « pipeline non exécutée, pas de tableau descriptif disponible » signifie que l'inclusion
n'a pas abouti : corrigez d'abord l'onglet `Inclusion`. Si l'inclusion réussit mais que le tableau
descriptif échoue, l'encadré rouge apparaît dans la section du tableau : corrigez l'onglet
`Descriptive_table` puis recliquez.

## 4. Télécharger une liste de patients

Après un calcul réussi, la section **Liste de patients** permet d'exporter les patients retenus à
une étape :

1. **« choisir l'étape »** : une étape de l'onglet `Inclusion` ;
2. **« clé de permutation des ID patients (1Password) »** (optionnelle) : la clé numérique stockée
   dans 1Password ;
3. **« télécharger la liste des patients (CSV) »** : télécharge `patients.csv`.

| Colonne | Contenu |
| --- | --- |
| `patient_id` | Identifiant pseudonymisé (permuté avec la clé). Absente si aucune clé n'est saisie. |
| `shuffled_patient_id` | Identifiant interne RED d'origine. |
| `patient_identifier` | Trigramme du patient visible dans le dossier médical. |

!!! danger "Données identifiantes"
    Ce fichier permet de retrouver les patients dans le dossier médical. Il doit être manipulé et
    stocké selon les règles de protection des données de santé en vigueur.
