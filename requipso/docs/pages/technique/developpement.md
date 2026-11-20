# Développement

## Installation

Prérequis système : un compilateur C/C++ et Graphviz (pour le flowchart).

=== "macOS"

    ```bash
    brew install graphviz
    ```

=== "Debian / Ubuntu"

    ```bash
    sudo apt update
    sudo apt install build-essential graphviz
    ```

Puis, à la racine du dépôt, avec [uv](https://docs.astral.sh/uv/) :

```bash
uv sync    # Python 3.12, dépendances du projet et outils de documentation
```

Le groupe `docs` (MkDocs) est installé par défaut (`[tool.uv] default-groups` dans
`pyproject.toml`).

L'accès au Sheet et au Drive se fait avec le compte Google `@ipsosante.fr` de l'utilisateur. Au
premier lancement, un onglet du navigateur s'ouvre pour se connecter ; le jeton est ensuite conservé
dans `~/.config/requipso/google_token.json` (le supprimer pour changer de compte). Le fichier
`google_oauth_client.json` (client OAuth « Desktop » du projet Google Cloud) doit être présent à la
racine du dépôt.

## Lancer l'application

```bash
uv run requipso                  # = marimo run requipso/notebooks/new/marimo/run.py --show-tracebacks
uv run requipso --port 2718      # les arguments sont transmis à marimo
```

`requipso` sert aussi cette documentation sur <http://127.0.0.1:8001> (`mkdocs serve` en
arrière-plan, arrêté avec l'application) et l'ouvre dans un nouvel onglet après quelques secondes.
Si MkDocs n'est pas installé, l'application démarre seule avec un message.

L'application mémorise le dernier dossier de données et la dernière feuille dans
`requipso/notebooks/marimo/.requipso_last.json` (ignoré par git).

## Notebooks

| Fichier | Usage |
| --- | --- |
| `requipso/notebooks/marimo/run.py` | L'application utilisateur (lancée par `requipso`). |

Pour éditer un notebook marimo :

```bash
uv run marimo edit requipso/notebooks/marimo/dev.py
```

`[tool.marimo.runtime] on_cell_change = "autorun"` est configuré dans `pyproject.toml`.

Dans IPython / Jupyter, importer `requipso` installe une complétion des noms de colonnes dans
`pl.col("…")` (`requipso/completer.py`).

## Qualité du code

```bash
uv run ruff check .
uv run ruff format .
uv run mypy requipso
```

La configuration mypy (`pyproject.toml`) est modérément stricte : `check_untyped_defs`,
`disallow_incomplete_defs`, `warn_return_any`… Les surcharges de `transform` avec des arguments
nommés par table portent un `# type: ignore[override]`.

## Documentation

La documentation (ce site) est générée avec [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

```bash
uv run mkdocs serve -f requipso/docs/mkdocs.yml           # http://127.0.0.1:8000, rechargement automatique
uv run mkdocs build -f requipso/docs/mkdocs.yml --strict  # génère site/ et échoue sur tout avertissement
```

La documentation est dans le paquet (`requipso/docs/`, déclarée en `package-data`) pour que
`requipso` puisse la servir aussi depuis une installation hors dépôt.

| Élément | Emplacement |
| --- | --- |
| Configuration et navigation | `requipso/docs/mkdocs.yml` |
| Pages | `requipso/docs/pages/` (`guide/`, `blocs/`, `technique/`) |
| Images | `requipso/docs/pages/assets/` |
| Macros (tableaux générés) | `requipso/docs/macros.py` |

`macros.py` réutilise `BlockExporter` de
[`requipso/signature_exporter.py`](export-signatures.md) et fournit trois macros
utilisables dans toute page :

| Macro | Rendu |
| --- | --- |
| `bloc_resume("Nom")` | Encadré « Fiche du bloc » : niveau, type de valeur, dates, chemin du code. |
| `bloc_parametres("Nom")` | Tableaux des paramètres communs (valeurs par défaut du bloc) et spécifiques. |
| `blocs_tableau()` | Tableau récapitulatif de tous les blocs, par famille. |

Le build importe `requipso.pipes` (et donc edsnlp) : il nécessite l'environnement du projet.

## Image Docker

`docker/Dockerfile` construit une image basée sur `inseefrlab/onyxia-marimo-python` (plateforme
Onyxia) :

```bash
docker build -f docker/Dockerfile -t requipso .
docker run -p 2718:2718 requipso
```

L'image installe le projet avec `uv sync --frozen` dans `/opt/python` et lance
`uv run --no-sync requipso --host 0.0.0.0 --port 2718`.

## Publication d'une version

Deux workflows GitHub Actions partent du même tag `vX.Y.Z` :

| Workflow | Fichier | Effet |
| --- | --- | --- |
| Build and publish | `.github/workflows/publish.yml` | Envoie le paquet sur [PyPI](https://pypi.org/p/requipso). |
| Documentation | `.github/workflows/docs.yml` | Ajoute cette documentation sur la branche `gh-pages`. |

Le paquet s'installe ensuite avec :

```bash
uvx --python 3.12 requipso
```

Python 3.12 est obligatoire (`requires-python` dans `pyproject.toml`). Les arguments passés après la commande sont transmis à marimo, comme avec `uv run requipso --port 2718`. Graphviz reste un prérequis système : `uvx` n'installe que les dépendances Python.

### Une seule fois

La publication sur PyPI utilise [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) : GitHub prouve son identité au moment du tag, aucun jeton n'est stocké dans le dépôt.

1. Sur GitHub : **Settings → Environments**, environnement nommé `pypi`.
2. Sur PyPI : un Trusted Publisher pour ce dépôt, fichier de workflow `publish.yml`, environnement `pypi`.
3. Pour le site : **Settings → Pages → Deploy from a branch**, branche `gh-pages`, dossier `/ (root)`.

### Publier

1. Mettre à jour la version du projet via `uv version --bump`.
2. Commiter, puis créer et pousser le tag correspondant sur GitHub :

    ```bash
    git tag v0.2.4
    git push origin v0.2.4
    git push --tags
    ```

Le tag, sans le `v` initial, doit être exactement la version de `pyproject.toml`. Sinon le job s'arrête avant l'envoi.

`publish.yml` construit le paquet avec `uv build` (sdist et wheel) à chaque pull request et à chaque push sur `main`, et ne le publie que pour un tag. Le wheel contient le code, `google_oauth_client.json` et `requipso/docs/` (déclarés dans `[tool.setuptools.package-data]`). Le groupe `docs` de `pyproject.toml` (MkDocs) n'est pas une dépendance du paquet : une installation PyPI lance l'application sans servir ce site. Le site public est celui publié sur `gh-pages`.

!!! warning "Une version PyPI ne se remplace pas"
    PyPI refuse un second envoi du même numéro. Pour corriger un paquet déjà publié, il faut incrémenter `version` et pousser un nouveau tag. Relancer le workflow d'un tag existant réutilise le fichier de workflow **tel qu'il est dans ce tag**, pas celui de `main`.