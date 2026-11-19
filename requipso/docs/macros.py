"""mkdocs-macros module: block reference tables generated from the code.

Exposes ``bloc_resume``, ``bloc_parametres`` and ``blocs_tableau`` to the
Markdown pages so that defaults and descriptions always match ``requipso.pipes``.
"""

from __future__ import annotations

import importlib
import json
from functools import cache
from typing import Any

from requipso.signature_exporter import BlockExporter, BlockSignature

COMMON_ROLES = {
    "value": "Valeur principale du bloc (colonne `value`).",
    "agg_func": "Agrégation des événements par patient (colonne `agg_func`).",
    "post_func": "Transformation finale de la valeur patient (colonne `post_func`).",
    "date_sql": "Filtre temporel sur `start_date` / `end_date` / `reference_date`.",
    "reference_date_block": "Bloc antérieur fournissant une date de référence par patient.",
    "reference_date_sql": "Calcul de la date de référence à partir des dates du bloc référencé.",
}

BLOCK_TYPES = {
    "patient": "patient (une ligne par patient)",
    "event": "événement (plusieurs lignes par patient, agrégées)",
}

FAMILIES: dict[str, list[str]] = {
    "Patient": ["Age", "EstVivant", "Genre", "Departement", "CodePostal", "PaquetAnnees"],
    "Parcours de soins": ["MedecinTraitant", "Consultations"],
    "Couverture": ["ALD", "Insurance"],
    "Antécédents": ["CIM10", "CISP2"],
    "Prescriptions": ["PrescriptionATC", "RegexPrescription"],
    "Biométrie": ["Biometry"],
    "Texte libre (NLP)": ["RegexConsultation", "RegexPatientObservation"],
}

PAGES = {
    "Age": "age.md",
    "EstVivant": "est-vivant.md",
    "Genre": "genre.md",
    "Departement": "departement.md",
    "CodePostal": "code-postal.md",
    "PaquetAnnees": "paquet-annees.md",
    "MedecinTraitant": "medecin-traitant.md",
    "Consultations": "consultations.md",
    "ALD": "ald.md",
    "Insurance": "insurance.md",
    "CIM10": "cim10.md",
    "CISP2": "cisp2.md",
    "PrescriptionATC": "prescription-atc.md",
    "RegexPrescription": "regex-prescription.md",
    "Biometry": "biometry.md",
    "RegexConsultation": "regex-consultation.md",
    "RegexPatientObservation": "regex-patient-observation.md",
}


@cache
def _signatures() -> dict[str, BlockSignature]:
    return {s.block_name: s for s in BlockExporter().signatures}


def _signature(name: str) -> BlockSignature:
    sigs = _signatures()
    if name not in sigs:
        raise KeyError(f"Bloc inconnu {name!r}. Blocs disponibles : {sorted(sigs)}")
    return sigs[name]


def _classes(sig: BlockSignature) -> tuple[type, type | None]:
    block_cls = getattr(importlib.import_module(sig.module), sig.block_name)
    params_cls = (
        getattr(importlib.import_module(sig.params_module), sig.params_name)
        if sig.params_module and sig.params_name
        else None
    )
    return block_cls, params_cls


def _cell(text: Any) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def _code(value: Any) -> str:
    if value is None or value == "":
        return "—"
    # Python-Markdown tables ignore pipes inside code spans, so no escaping here.
    return f"`{' '.join(str(value).split())}`"


def _value_row(sig: BlockSignature, params_cls: type | None) -> tuple[str, str]:
    """Return (default, role) cells for the ``value`` parameter."""
    spec = sig.common_parameters["value"]
    if spec["type"] == "None":
        return "—", "Non utilisé par ce bloc : laisser vide."
    help_text = spec["description"].removeprefix("[HELP]").strip()
    required = bool(params_cls and params_cls.model_fields["value"].is_required())
    if required:
        default = "**obligatoire**"
    elif spec["type"].startswith("list"):
        default = "vide = pas de filtre"
    else:
        default = "—"
    return default, f"{_cell(help_text)} (type {_code(spec['type'])})"


def _date_columns(block_cls: type) -> str:
    date_column = block_cls.config.date_column
    if date_column is None:
        return "aucune (le bloc ne porte pas de date)"
    if isinstance(date_column, str):
        return f"`{date_column}` (début = fin)"
    start, end = date_column
    return f"`{start}` → `start_date`, `{end}` → `end_date`"


def define_env(env: Any) -> None:
    @env.macro
    def bloc_resume(name: str) -> str:
        """Summary admonition for a block (type, dates, description)."""
        sig = _signature(name)
        block_cls, _ = _classes(sig)
        output_type = block_cls.config.output_type.value
        return "\n".join(
            [
                f'!!! abstract "Fiche du bloc `{name}`"',
                "",
                f"    *{_cell(sig.description or '')}*",
                "",
                f"    - **Nom à saisir dans `block_type`** : `{name}`",
                f"    - **Niveau** : {BLOCK_TYPES.get(sig.block_type, sig.block_type)}",
                f"    - **Type de valeur avant `post_func`** : `{output_type}`",
                f"    - **Dates exposées** : {_date_columns(block_cls)}",
                f"    - **Code source** : `{sig.module}.{name}` (paramètres : `{sig.params_name}`)",
                "",
            ]
        )

    @env.macro
    def bloc_parametres(name: str) -> str:
        """Common and specific parameter tables for a block."""
        sig = _signature(name)
        _, params_cls = _classes(sig)

        lines = [
            "#### Paramètres communs",
            "",
            "| Colonne du Sheet | Valeur par défaut | Rôle |",
            "| --- | --- | --- |",
        ]
        value_default, value_role = _value_row(sig, params_cls)
        lines.append(f"| `value` | {value_default} | {value_role} |")
        for param, role in COMMON_ROLES.items():
            if param == "value":
                continue
            default = sig.common_parameters.get(param, {}).get("default")
            lines.append(f"| `{param}` | {_code(default)} | {role} |")
        lines.append("")

        if sig.specific_parameters:
            lines += [
                "#### Paramètres spécifiques",
                "",
                "À renseigner dans la colonne `supplementary_params` sous forme de "
                "dictionnaire, par exemple "
                f"`{_example_supplementary(sig)}`.",
                "",
                "| Paramètre | Type | Valeur par défaut | Description (code) |",
                "| --- | --- | --- | --- |",
            ]
            for param, spec in sorted(sig.specific_parameters.items()):
                default = spec["default"]
                default_json = None if default is None else json.dumps(default, ensure_ascii=False)
                lines.append(
                    f"| `{param}` | {_code(spec['type'])} | {_code(default_json)} "
                    f"| {_cell(spec['description'])} |"
                )
        else:
            lines.append(
                "Ce bloc n'a pas de paramètre spécifique : "
                "la colonne `supplementary_params` reste vide."
            )
        lines.append("")
        return "\n".join(lines)

    @env.macro
    def blocs_tableau() -> str:
        """Summary table of every block grouped by family."""
        sigs = _signatures()
        listed = {b for blocks in FAMILIES.values() for b in blocks}
        unlisted = sorted(set(sigs) - listed)
        families = dict(FAMILIES)
        if unlisted:
            families["Autres"] = unlisted

        lines = [
            "| Famille | Bloc | Niveau | Daté | Description |",
            "| --- | --- | --- | --- | --- |",
        ]
        for family, blocks in families.items():
            for block in blocks:
                sig = sigs.get(block)
                if sig is None:
                    continue
                page = PAGES.get(block)
                label = f"[`{block}`]({page})" if page else f"`{block}`"
                lines.append(
                    f"| {family} | {label} | {sig.block_type} | "
                    f"{'oui' if sig.has_date else 'non'} | {_cell(sig.description or '')} |"
                )
        return "\n".join(lines) + "\n"


def _example_supplementary(sig: BlockSignature) -> str:
    param, spec = sorted(sig.specific_parameters.items())[0]
    default = spec["default"]
    if isinstance(default, bool):
        example: Any = str(not default).lower()
    elif isinstance(default, list):
        example = "[" + ", ".join(f'"{v}"' for v in default[:1] or ["..."]) + "]"
    else:
        example = '"..."'
    return "{" + f'"{param}": {example}' + "}"
