import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell
def _():
    import json
    from pathlib import Path

    from importlib.metadata import version

    import marimo as mo

    config_path = Path(__file__).parent / ".requipso_last.json"

    def load_config() -> dict:
        try:
            return json.loads(config_path.read_text())  # type: ignore
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_config(data_dir: str, sheet_name: str) -> None:
        config_path.write_text(
            json.dumps(
                {
                    "data_dir": data_dir,
                    "sheet_name": sheet_name,
                }
            )
        )

    version=version("requipso")
    last_config = load_config()
    return Path, last_config, mo, save_config, version


@app.cell
def _(mo, version):
    mo.md(
        "# Requipso\n\n"
        + f"* Version installée: {version}\n"
        + "* [Documentation en ligne](https://ipsosante.github.io/requipso/)"
    )
    return


@app.cell
def _(mo):
    import graphviz as _graphviz

    try:
        _graphviz_version = _graphviz.version()
        _graphviz_status = mo.md("")
    except _graphviz.ExecutableNotFound:
        _graphviz_status = mo.vstack(
            [
                mo.md(
                    "⚠️ **Graphviz executable n'est pas installé ou n'est pas dans le PATH.**\n"
                    "Installez Graphviz via un terminal (voir plus bas), puis relancez requipso :"
                ),
                mo.ui.tabs(
                    {
                        "macOS": mo.md(
                            """
    ### Installer Graphviz sur macOS

    Avec Homebrew :

    ```bash
    brew install graphviz
    ```

    Vérifier l'installation :

    ```bash
    dot -V
    ```
    """
                        ),
                        "Linux / WSL": mo.md(
                            """
    ### Installer Graphviz sur Linux ou WSL

    Debian / Ubuntu / WSL Ubuntu :

    ```bash
    sudo apt update
    sudo apt install graphviz
    ```

    Fedora :

    ```bash
    sudo dnf install graphviz
    ```

    Vérifier l'installation :

    ```bash
    dot -V
    ```
    """
                        ),
                        "Windows": mo.md(
                            """
    ### Installer Graphviz sur Windows

    Avec winget :

    ```powershell
    winget install graphviz
    ```

    Ou avec Chocolatey :

    ```powershell
    choco install graphviz
    ```

    Après installation, ouvrez un nouveau terminal et vérifiez :

    ```powershell
    dot -V
    ```

    Si la commande n'est pas reconnue, ajoutez le dossier `bin` de Graphviz au `PATH` Windows, puis redémarrez le terminal.
    """
                        ),
                    }
                ),
            ]
        )

    _graphviz_status
    return


@app.cell
def _(Path, last_config, mo):
    _initial = (
        Path(last_config["data_dir"]).parent
        if "data_dir" in last_config
        else Path.home()
    )

    file_browser = mo.ui.file_browser(
        initial_path=_initial,
        selection_mode="directory",
        multiple=False,
        label="choisir le dossier local contenant les données",
    )
    file_browser
    return (file_browser,)


@app.cell
def _():
    from requipso.google import GoogleConnector

    google_connector = GoogleConnector()
    return (google_connector,)


@app.cell
def _(google_connector, last_config, mo):
    _options = sorted(google_connector.sheets)
    _last_sheet = last_config.get("sheet_name")
    _initial_value = _last_sheet if _last_sheet in _options else None

    sheet_dropdown = mo.ui.dropdown(
        options=_options,
        value=_initial_value,
        label="choisir le Google Sheet",
    )
    sheet_dropdown
    return (sheet_dropdown,)


@app.cell
def _(file_browser, google_connector, mo, sheet_dropdown):
    from requipso import Data

    mo.stop(
        not (len(file_browser.value) > 0 and sheet_dropdown.value),
        mo.md(
            "renseigner le dossier contenant les données et choisir le Google Sheet pour continuer"
        ),
    )

    data_dir = file_browser.path(0)
    sheet_name = sheet_dropdown.value
    sheet_id = google_connector.sheets[sheet_name]

    data = Data(data_dir)

    run_button = mo.ui.run_button(
        label="(re)lancer la pipeline",
        kind="success",
        tooltip="cliquer pour lancer la pipeline",
    )

    mo.vstack(
        [
            mo.md(f"**Dossier:** `{data_dir}`"),
            mo.md(
                f"**Google Sheet:** [{sheet_name}](https://docs.google.com/spreadsheets/d/{sheet_id}/edit)"
            ),
            run_button,
        ]
    )
    return data, data_dir, run_button, sheet_name


@app.cell
def _(mo):
    get_pipeline_hash, set_pipeline_hash = mo.state(0)
    get_flowchart_url, set_flowchart_url = mo.state("")
    return (
        get_flowchart_url,
        get_pipeline_hash,
        set_flowchart_url,
        set_pipeline_hash,
    )


@app.cell
def _(
    Path,
    data,
    data_dir,
    get_pipeline_hash,
    google_connector,
    mo,
    run_button,
    save_config,
    set_flowchart_url,
    set_pipeline_hash,
    sheet_name,
):
    mo.stop(not run_button.value)

    get_success_pipeline, set_success_pipeline = mo.state(False)
    get_success_descriptive, set_success_descriptive = mo.state(False)

    import time

    from requipso.pipeline_loader import PipelineBuilder

    save_config(str(data_dir), sheet_name)

    google_connector.set_spreadsheet(sheet_name)

    builder = PipelineBuilder(google_connector)
    inclusion = builder.build()

    if get_pipeline_hash() == builder.pipeline_hash:
        mo.output.append(mo.md("pipeline déjà exécutée, pas de recalcul nécessaire"))
    else:
        data.reset()

        n_steps = len(inclusion.steps_names)
        with mo.status.progress_bar(
            total=n_steps, title="inclusion ...", subtitle=""
        ) as _bar:
            for step_name, n in inclusion.iter_run(data):
                time.sleep(0.5)
                _bar.update(
                    increment=1,
                    subtitle=f"bloc {step_name} : {n} patients",
                )

        inclusion.graph("graph")
        url = google_connector.upload_file(
            Path("graph.png"), upload_name=f"{sheet_name}.png"
        )

        # Run was successful, we store the hash and url:
        set_pipeline_hash(builder.pipeline_hash)
        set_flowchart_url(url)

    set_success_pipeline(True)
    print("NEW HASH", get_pipeline_hash())
    return (
        builder,
        get_success_descriptive,
        get_success_pipeline,
        inclusion,
        set_success_descriptive,
        time,
    )


@app.cell
def _(
    builder,
    data,
    get_flowchart_url,
    get_success_pipeline,
    google_connector,
    inclusion,
    mo,
    set_success_descriptive,
    time,
):

    mo.stop(
        not get_success_pipeline(),
        mo.md("pipeline non exécutée, pas de tableau descriptif disponible"),
    )

    descriptive = builder.build_descriptive(
        data=data,
        inclusion_pipeline=inclusion,
    )

    n_rows = len(descriptive.rows)

    with mo.status.progress_bar(
        total=n_rows, title="tableau descriptif ...", subtitle=""
    ) as _bar:
        for row, _ in zip(descriptive.rows, descriptive.run_iter(data)):
            time.sleep(0.5)
            _bar.update(
                increment=1,
                subtitle=f"variable: {row['display_name']}",
            )

    stats = descriptive.format_stats(descriptive.stats)
    descriptive.upload_stats(stats)

    set_success_descriptive(True)

    mo.vstack(
        [
            mo.md(f"""
    **pipeline terminée**
    * Tableau descriptif [dispo plus bas](#tableau-descriptif) et sur le [Google Sheet](https://docs.google.com/spreadsheets/d/{google_connector.spreadsheet_key}), onglet "🔒 Results"
    * Flowchart d'inclusion sur le [Google Drive]({get_flowchart_url()})
    """),
            mo.md("### Flowchart d'inclusion"),
            mo.image(src="graph.png"),
            mo.md("### Tableau descriptif"),
            mo.ui.table(stats, label="Statistiques descriptives", page_size=100),
        ]
    )
    return


@app.cell
def _(get_success_descriptive, inclusion, mo):
    mo.stop(not get_success_descriptive())

    import polars as pl
    import polars_permutation as pp

    AVAILABLE_STEPS = list(inclusion.steps_names.keys())

    def get_patient_list(
        data, step_name: str, shuffling_key: str | None
    ) -> pl.DataFrame:
        if step_name not in AVAILABLE_STEPS:
            raise ValueError(f"step_name {step_name} not found in data.all_results")
        df = (
            data.all_results[step_name]["post"]
            .filter(pl.col(step_name))
            .select("patient_id")
        )

        patients = data.get_table("patient").select("patient_id", "patient_identifier")
        if not shuffling_key:
            return df.join(patients, on="patient_id", how="inner").select(
                shuffled_patient_id="patient_id",
                patient_identifier="patient_identifier",
            )

        df_ids = pl.select(
            pl.int_range(0, 100_000_000, eager=False).alias("final_patient_id")
        ).with_columns(
            patient_id=pp.feistel_permute(
                pl.col("final_patient_id"), n=100_000_000, seed=int(shuffling_key)
            )
        )
        df_ids = df_ids.join(patients, on="patient_id", how="inner")
        df = df.join(df_ids, on="patient_id", how="inner")
        return df.select(
            patient_id="final_patient_id",
            shuffled_patient_id="patient_id",
            patient_identifier="patient_identifier",
        )

    step_dropdown = mo.ui.dropdown(
        options=AVAILABLE_STEPS,
        value=AVAILABLE_STEPS[0] if AVAILABLE_STEPS else None,
        label="choisir l'étape",
    )

    shuffle_key_input = mo.ui.text(
        label="clé de permutation des ID patients (1Password)",
        placeholder="optionnel",
    )
    return get_patient_list, shuffle_key_input, step_dropdown


@app.cell
def _(data, get_patient_list, mo, shuffle_key_input, step_dropdown):
    mo.stop(not step_dropdown.value)

    def _make_csv():
        return (
            get_patient_list(
                data, step_dropdown.value, shuffling_key=shuffle_key_input.value
            )
            .write_csv()
            .encode("utf-8")
        )

    _download = mo.download(
        data=_make_csv,
        filename=f"patients.csv",
        mimetype="text/csv",
        label="télécharger la liste des patients (CSV)",
    )

    mo.vstack(
        [
            mo.md("### Liste de patients"),
            step_dropdown,
            shuffle_key_input,
            _download,
        ]
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
