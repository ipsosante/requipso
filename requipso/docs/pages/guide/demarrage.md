# Démarrage

Cette page liste tout ce qu'il faut avant de construire sa première étude. La plupart de ces étapes
ne sont à faire qu'**une seule fois**.

## 1. Les accès nécessaires

| Accès | Pourquoi |
| --- | --- |
| Dossier Google Drive Requipso | C'est là que vivent les Google Sheets des études et les flowcharts générés. |
| Données RED | Les fichiers de données sur lesquels tournent les requêtes. |
| 1Password | Mot de passe de déchiffrement des données et clé de permutation des identifiants patients. |

!!! warning "Données de santé"
    Les données RED sont des données de santé à caractère personnel. Elles ne doivent jamais être
    copiées en dehors des environnements autorisés, ni partagées par e-mail ou messagerie.

## 2. Créer le Google Sheet de son étude

1. Ouvrez le [dossier Drive Requipso](https://drive.google.com/drive/folders/1vTA1zVLbyU6mVMkiTL1J1bLolOlsut7A).
2. Faites un clic droit sur la feuille nommée **template** puis **Créer une copie**.
3. Renommez la copie avec un nom parlant (ex. `Diabète T2 - suivi 2024`). Ce nom sera affiché dans
   l'application, et le flowchart sera enregistré sous `<nom de la feuille>.png` dans le même dossier.

!!! info "La feuille doit rester dans ce dossier"
    Requipso ne « voit » que les feuilles présentes dans ce dossier Drive (il y accède avec votre
    compte Google `@ipsosante.fr`). Une feuille déplacée ailleurs n'apparaîtra pas dans la liste de
    l'application.

## 3. Récupérer les données

Les données sont un dossier contenant un fichier `.parquet` par table de la base RED
(`patient.parquet`, `consultation.parquet`, `biometry.parquet`…). La procédure actuelle de
récupération (export depuis l'instance ETL, puis décompression avec le mot de passe
« Clé chiffrement export RED » stocké dans 1Password) est décrite dans le `README.md` du dépôt.

Après décompression, notez l'emplacement du dossier : vous le sélectionnerez dans l'application.

## 4. Lancer l'application

L'application Requipso s'ouvre dans votre navigateur. Selon votre installation :

=== "Sur votre poste"

    Dans un terminal, à la racine du dépôt :

    ```bash
    uv run requipso
    ```

    Un onglet de navigateur s'ouvre automatiquement. Au premier lancement, un autre onglet vous
    demande de vous connecter avec votre compte Google `@ipsosante.fr` et d'autoriser l'accès au
    Drive ; cette étape n'est plus demandée ensuite.

=== "Sur un environnement hébergé (Docker / Onyxia)"

    L'image Docker démarre directement l'application sur le port `2718`.
    Ouvrez l'URL du service fournie par la plateforme.

La suite (choix des données, de la feuille et lancement) est décrite dans
[Utiliser l'application](application.md).

## 5. Et ensuite ?

Le parcours conseillé pour une première étude :

1. Lire la [présentation du Google Sheet](google-sheet.md) ;
2. Renseigner l'[onglet Project](onglet-projet.md) (date de référence) ;
3. Construire le flowchart dans l'[onglet Inclusion](onglet-inclusion.md) ;
4. Lancer une première fois l'application pour vérifier le flowchart ;
5. Choisir les populations et remplir l'[onglet Descriptive_table](onglet-tableau-descriptif.md) ;
6. Relancer et consulter les résultats.

L'[exemple complet](exemple-complet.md) déroule ce parcours sur une étude réelle.
