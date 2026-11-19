# Requipso

## Installation

Tout d'abord les dépendances:

```
sudo apt update
sudo apt install build-essential graphviz
```

Ensuite clonez le repo puis:

```
cd requipso
uv sync
```

## Données 

Demander à l"équipe RED d'ipso de vous fournir les données finales de l'ETL (ensemble de fichiers parquets)


## Démo

Pour lancer la démo: `uv run requipso`.  
Cela devrait ouvrir:  

* un onglet sur navigateur
* un autre onglet contenant la documentation

[![demo.mp4 - Google Drive](https://res.cloudinary.com/marcomontalbano/image/upload/v1777483912/video_to_markdown/images/google-drive--1OTeSeuiUC5FhiQMEqwwUt_1l2KcusFtH-c05b58ac6eb4c4700831b2b3070cd403.jpg)](https://drive.google.com/file/d/1OTeSeuiUC5FhiQMEqwwUt_1l2KcusFtH/view "demo.mp4 - Google Drive")

## Mode d'emploi

* Il faut créer une feuille de calcul dans [ce dossier Drive](https://drive.google.com/drive/folders/1vTA1zVLbyU6mVMkiTL1J1bLolOlsut7A). Vous pouvez dupliquer la feuille de calcul nommée **template**
* Ensuite:
    * Dans l'onglet 'Projet'
        * définir la date de référence
        * les populations d'intérêt seront à définir une fois la pipeline d'inclusion définie
    * Bien lire l'onglet "Explications" pour comprendre
    * L'onglet 'Inclusion' permet de définir son flowchart
    * Ensuite l'onglet 'Descriptive_table' permet de définir le tableau descriptif
        * A ce moment là, vous pouvez renseigner les populations d'intérêt (qui formeront les colonnes du tableau desciptif) en faisant référence à certains blocs de votre diagramme d'inclusion
* Une fois que tout est rempli, cf plus haut (démo) pour lancer le requêteur.

## Documentation

Pour build/serve la documentation seule:

```bash
uv run mkdocs serve -f requipso/docs/mkdocs.yml
uv run mkdocs build -f requipso/docs/mkdocs.yml --strict
```