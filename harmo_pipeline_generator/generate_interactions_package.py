#!/usr/bin/env python3
"""Generate Matillion harmonization packages from metadata Excel files.

The script supports:
- the original Interactions package flow as a preset
- generic category runs such as GA by swapping header/detail/template arguments

Interactions remains the best-supported preset because it also generates
unit-test orchestration jobs. Generic categories can reuse the harmonization
generation path without the interactions-specific unit-test layer.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import uuid
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


DEFAULT_BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PREFIX_ORDER = ["MDE", "TDE", "RDE", "FACT", "DIM"]
SOURCE_DATABASE_ENV = "${ev_database_10_staging}"
TARGET_DATABASE_ENV = "${ev_database_30_presentation}"

DATA_TYPE_MAPPING = {
    "TEXT(255)": "TEXT(255)",
    "TEXT": "TEXT",
    "TIMESTAMP_NTZ": "TIMESTAMP_NTZ",
    "BOOLEAN": "BOOLEAN",
    "NUMBER": "NUMBER",
    "text": "TEXT",
    "Text": "TEXT",
    "Date & Time": "TIMESTAMP_NTZ",
    "Decimal (38,4)": "NUMBER(38,5)",
    "Decimal (38,5)": "NUMBER(38,5)",
    "decimal": "NUMBER(38,5)",
    "Boolean": "BOOLEAN",
    "flag": "BOOLEAN",
    "Integer": "NUMBER",
    "integer": "NUMBER",
    "datetime": "TIMESTAMP_NTZ",
    "Date": "DATE",
    "DATE": "DATE",
    "Time": "TIMESTAMP_NTZ",
}


@dataclass
class GeneratorConfig:
    base_dir: Path
    header_file: str
    detail_file: str
    harm_template_file: str
    harm_filter_template_file: str
    output_path: Path
    package_name: str
    tree_path: list[str]
    include_transformations: bool
    include_unit_tests: bool
    unit_test_template_file: str | None
    version_override: str | None


def normalize_value(value):
    if pd.isna(value):
        return None
    return value


def is_present(value) -> bool:
    if value is None:
        return False
    if isinstance(value, float) and math.isnan(value):
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    return True


def column_priority(column_name: str) -> int:
    lowered = (column_name or "").lower()
    if lowered == "valid_from":
        return 999
    if lowered.endswith("_key") and (
        lowered.startswith("mde_")
        or lowered.startswith("tde_")
        or lowered.startswith("fact_")
        or lowered.startswith("dim_")
    ):
        return 0
    if lowered.endswith("_bk"):
        return 1
    return 2


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def replace_placeholders(payload: object, replacements: dict[str, str]) -> object:
    rendered = json.dumps(payload)
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return json.loads(rendered)


def offset_ids(payload: object, offset: int, parent_key: str | None = None) -> object:
    connector_key_parents = {
        "components",
        "successConnectors",
        "failureConnectors",
        "unconditionalConnectors",
        "trueConnectors",
        "falseConnectors",
        "iterationConnectors",
        "noteConnectors",
        "variables",
        "grids",
    }
    id_array_keys = {
        "inputConnectorIDs",
        "outputConnectorIDs",
        "outputSuccessConnectorIDs",
        "outputFailureConnectorIDs",
        "outputUnconditionalConnectorIDs",
        "outputTrueConnectorIDs",
        "outputFalseConnectorIDs",
        "outputIterationConnectorIDs",
        "inputIterationConnectorIDs",
    }

    if isinstance(payload, dict):
        result = {}
        for key, value in payload.items():
            new_key = key
            if (
                parent_key in connector_key_parents
                and key.isdigit()
                and parent_key not in {"variables", "grids"}
            ):
                new_key = str(int(key) + offset)

            if key == "id" and isinstance(value, int):
                result[new_key] = value + offset
            elif key in {"sourceID", "targetID"} and isinstance(value, int):
                result[new_key] = value + offset
            elif key in id_array_keys and isinstance(value, list):
                result[new_key] = [item + offset for item in value]
            else:
                result[new_key] = offset_ids(value, offset, key)
        return result

    if isinstance(payload, list):
        return [offset_ids(item, offset, parent_key) for item in payload]

    return payload


def first_component_value(component: dict, parameter_slot: str, value_slot: str = "1") -> str | None:
    parameter = component.get("parameters", {}).get(parameter_slot, {})
    for element in parameter.get("elements", {}).values():
        value = element.get("values", {}).get(value_slot)
        if value and value.get("type") == "STRING":
            return value.get("value")
    return None


def set_component_string(
    component: dict,
    parameter_slot: str,
    element_slot: str,
    value_slot: str,
    new_value: str,
) -> None:
    component["parameters"][parameter_slot]["elements"][element_slot]["values"][value_slot]["value"] = new_value


def find_component_by_name(job: dict, component_name: str) -> dict:
    for component in job.get("components", {}).values():
        if first_component_value(component, "1") == component_name:
            return component
    raise KeyError(f"Component {component_name!r} not found")


def load_metadata(base_dir: Path, header_file: str, detail_file: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    header_df = pd.read_excel(base_dir / header_file, keep_default_na=False)
    detail_df = pd.read_excel(base_dir / detail_file, keep_default_na=False)
    detail_df = detail_df[detail_df["target_table_name"].notna()].copy()
    detail_df["bk_priority"] = detail_df["target_column"].apply(column_priority)
    detail_df = detail_df.sort_values(
        by=["target_table_name", "primary_key_flag", "bk_priority", "target_column"],
        ascending=[True, False, True, True],
    ).drop(columns="bk_priority")
    return header_df, detail_df


def unit_test_key_order(column_name: str) -> tuple[int, str]:
    normalized = (column_name or "").upper()
    if normalized in {"IDENTITY_UNIQUE_IDENTIFIER_BK", "IDENTITY_UNIQUE_IDENTIFIER"}:
        return 0, normalized
    if normalized in {"INTERACTION_IDENTIFIER_BK", "INTERACTION_ID"}:
        return 1, normalized
    return 2, normalized


def build_prefix_order(specs: list[dict]) -> list[str]:
    discovered = []
    for prefix in DEFAULT_PREFIX_ORDER:
        if any(spec["prefix"] == prefix for spec in specs):
            discovered.append(prefix)
    leftovers = sorted({spec["prefix"] for spec in specs if spec["prefix"] not in DEFAULT_PREFIX_ORDER})
    return discovered + leftovers


def build_table_specs(header_df: pd.DataFrame, detail_df: pd.DataFrame) -> list[dict]:
    specs = []
    grouped_details = {
        table_name: group.copy()
        for table_name, group in detail_df.groupby("target_table_name", sort=False)
    }

    for _, row in header_df.iterrows():
        pl_name = str(row["pl_name"]).upper()
        table_details = grouped_details.get(pl_name)
        if table_details is None or table_details.empty:
            raise ValueError(f"No detail rows found for {pl_name}")

        calculator_rows = []
        description_rows = []
        classification_rows = []
        primary_key_rows = []
        source_columns = []
        primary_key_source_columns = []
        primary_key_target_columns = []

        for _, detail_row in table_details.iterrows():
            source_column = normalize_value(detail_row["source_column"])
            target_column = str(detail_row["target_column"])
            formula = normalize_value(detail_row["column_formula"])
            data_type_raw = str(detail_row["column_data_type"]).strip()
            column_data_type = DATA_TYPE_MAPPING.get(data_type_raw)
            if column_data_type is None:
                raise ValueError(
                    f"Unsupported column_data_type {data_type_raw!r} in {pl_name}.{target_column}"
                )

            if is_present(source_column):
                source_columns.append(str(source_column))

            calculation_formula = (
                f"{formula}::{column_data_type}"
                if is_present(formula)
                else f"{source_column}::{column_data_type}"
            )
            calculator_rows.append({"values": [target_column, calculation_formula]})

            if str(detail_row["primary_key_flag"]).strip().upper() == "Y":
                primary_key_rows.append({"values": [target_column]})
                primary_key_target_columns.append(target_column)
                if not is_present(source_column):
                    raise ValueError(f"Primary key {pl_name}.{target_column} has no source_column")
                primary_key_source_columns.append(str(source_column))

            column_description = normalize_value(detail_row["column_description"])
            if is_present(column_description):
                description_rows.append(
                    {"values": [target_column, str(column_description).replace("'", "\\'")]}
                )

            column_classification = normalize_value(detail_row["column_classification"])
            column_domain = normalize_value(detail_row["column_domain"])
            if is_present(column_classification) and is_present(column_domain):
                classification_rows.append(
                    {"values": [target_column, str(column_classification), str(column_domain)]}
                )
            else:
                raise ValueError(
                    f"{pl_name}.{target_column} is missing column_classification or column_domain"
                )

        interaction_datetime_rows = table_details[
            table_details["target_column"].astype(str).str.upper() == "INTERACTION_DATETIME"
        ]
        interaction_datetime_source = None
        if not interaction_datetime_rows.empty:
            interaction_datetime_source = normalize_value(
                interaction_datetime_rows.iloc[0]["source_column"]
            )

        unit_test_target_columns = sorted(primary_key_target_columns, key=unit_test_key_order)
        unit_test_source_columns = sorted(primary_key_source_columns, key=unit_test_key_order)

        filter_fields = {
            "filter_column": normalize_value(row.get("filter_column")),
            "filter_qualifier": normalize_value(row.get("filter_qualifier")),
            "filter_operator": normalize_value(row.get("filter_operator")),
            "filter_column_value": normalize_value(row.get("filter_column_value")),
        }
        use_filter_template = all(is_present(value) for value in filter_fields.values())

        specs.append(
            {
                "pl_name": pl_name,
                "pl_name_lower": pl_name.lower(),
                "pl_schema": str(row["pl_schema"]).upper(),
                "pl_description": str(row["pl_description"]),
                "staging_schema": str(row["staging_schema"]),
                "staging_table": str(row["staging_table"]).upper(),
                "prefix": pl_name.split("_", 1)[0],
                "historization": str(row["historization"]).upper() if "historization" in row else "",
                "calculator_rows": calculator_rows,
                "description_rows": description_rows,
                "classification_rows": classification_rows,
                "primary_key_rows": primary_key_rows,
                "primary_key_target_columns": primary_key_target_columns,
                "primary_key_source_columns": primary_key_source_columns,
                "unit_test_target_columns": unit_test_target_columns,
                "unit_test_source_columns": unit_test_source_columns,
                "source_column_string": ",".join(source_columns),
                "interaction_datetime_source": interaction_datetime_source,
                "use_filter_template": use_filter_template,
                "filter_fields": filter_fields,
                "stg_primary_keys": normalize_value(row.get("stg_primary_keys")),
            }
        )

    prefix_order = build_prefix_order(specs)

    def prefix_sort_key(spec: dict) -> tuple[int, str]:
        prefix_index = prefix_order.index(spec["prefix"]) if spec["prefix"] in prefix_order else len(prefix_order)
        return prefix_index, spec["pl_name"]

    return sorted(specs, key=prefix_sort_key)


def build_replacements(spec: dict) -> dict[str, str]:
    replacements = {
        "$$target_schema$$": spec["pl_schema"],
        "$$target_table_lower$$": spec["pl_name_lower"],
        "$$target_table$$": spec["pl_name"],
        "$$source_schema$$": spec["staging_schema"],
        "$$source_table$$": spec["staging_table"],
        "$$column_list$$": spec["source_column_string"],
        "$$table_description$$": spec["pl_description"].replace("'", "\\\\'"),
        "$$historization$$": spec["historization"],
    }
    if spec["use_filter_template"]:
        replacements.update(
            {
                "$$filter_column$$": str(spec["filter_fields"]["filter_column"]),
                "$$filter_qualifier$$": str(spec["filter_fields"]["filter_qualifier"]),
                "$$filter_operator$$": str(spec["filter_fields"]["filter_operator"]),
                "$$filter_column_value$$": str(spec["filter_fields"]["filter_column_value"]),
            }
        )
    return replacements


def render_harmonization_job(
    spec: dict,
    harm_template: dict,
    harm_filter_template: dict,
) -> tuple[dict, dict]:
    template = harm_filter_template if spec["use_filter_template"] else harm_template
    rendered = replace_placeholders(copy.deepcopy(template), build_replacements(spec))

    orchestration_job = rendered["orchestrationJobs"][0]
    transformation_job = rendered["transformationJobs"][0]

    orchestration_job["grids"]["gv_primary_key_configuration"]["values"] = spec["primary_key_rows"]
    orchestration_job["grids"]["gv_column_description_configuration"]["values"] = spec["description_rows"]
    orchestration_job["grids"]["gv_column_classification_configuration"]["values"] = spec["classification_rows"]
    transformation_job["grids"]["gv_calculator"]["values"] = spec["calculator_rows"]

    return orchestration_job, transformation_job


def build_interactions_unit_test_sql(spec: dict) -> str:
    target_pk_list = ", ".join(spec["unit_test_target_columns"])
    source_pk_list = ", ".join(spec["unit_test_source_columns"])
    table_name = spec["pl_name"]
    target_table_ref = f'{TARGET_DATABASE_ENV}.{spec["pl_schema"]}."{table_name}"'
    staging_table_ref = f'{SOURCE_DATABASE_ENV}."{spec["staging_schema"]}"."{spec["staging_table"]}" i'

    staging_filter = ""
    if is_present(spec["interaction_datetime_source"]):
        source_datetime = spec["interaction_datetime_source"]
        staging_filter = (
            f"\n    WHERE TRY_TO_TIMESTAMP_NTZ(i.{source_datetime}) <= i.__LOAD_TS "
            f"OR TRY_TO_TIMESTAMP_NTZ(i.{source_datetime}) IS NULL"
        )

    extra_comment = ""
    if table_name == "MDE_CONSUMER_INTERACTION_FLAVOUR":
        extra_comment = (
            "    -- WHERE VALID_FROM < VALID_TO --qas only since there is "
            "FLAVOUR_REFERENCE_CODE_BK with null values\n"
        )

    return (
        "-- Makes sure each BK only have 1 active flag = true\n"
        "WITH VERSIONS_CNT AS (\n"
        "    SELECT \n"
        f"        {target_pk_list},\n"
        "        COUNT(*) AS total_records,\n"
        "        SUM(CASE WHEN ACTIVE_FLAG = TRUE THEN 1 ELSE 0 END) AS ACTIVE_FLAG_CNT\n"
        f"    FROM {target_table_ref}\n"
        f"    GROUP BY {target_pk_list}\n"
        ")\n"
        f"SELECT '{table_name}: distinct BK cnt comparison' AS TEST_TYPE, s.CNT AS SOURCE, t.CNT AS TARGET\n"
        "FROM (\n"
        "    SELECT COUNT(*) AS CNT\n"
        "    FROM VERSIONS_CNT\n"
        ") as s\n"
        "CROSS JOIN (\n"
        "    SELECT COUNT(*) AS CNT\n"
        "    FROM VERSIONS_CNT\n"
        "    WHERE ACTIVE_FLAG_CNT = 1\n"
        ") as t\n\n"
        "UNION ALL\n\n"
        "-- Makes sure there is no record that has VALID_FROM >= VALID_TO\n"
        f"SELECT '{table_name}: VALID_FROM >= VALID_TO' AS TEST_TYPE, s.CNT AS SOURCE, t.CNT AS TARGET\n"
        "FROM (\n"
        "\tSELECT COUNT(*) AS CNT\n"
        f"    FROM {target_table_ref}\n"
        f"{extra_comment}"
        ") as s\n"
        "CROSS JOIN (\n"
        "    SELECT COUNT(*) AS CNT\n"
        f"    FROM {target_table_ref}\n"
        "    WHERE VALID_FROM < VALID_TO\n"
        ") as t\n\n"
        "UNION ALL\n\n"
        "-- Makes sure that the count distinct of the BK composite key in Staging == Presentation\n"
        f"SELECT '{table_name}: distinct BK cnt comparison' AS TEST_TYPE, s.CNT AS SOURCE, t.CNT AS TARGET\n"
        "FROM (\n"
        f"    SELECT COUNT(DISTINCT {source_pk_list}) AS CNT\n"
        f"    FROM {staging_table_ref}"
        f"{staging_filter}\n"
        ") s\n"
        "CROSS JOIN (\n"
        f"    SELECT COUNT(DISTINCT {target_pk_list}) AS CNT\n"
        f"    FROM {target_table_ref}\n"
        ") t\n"
    )


def render_unit_test_job(spec: dict, unit_test_template: dict) -> dict:
    rendered = replace_placeholders(copy.deepcopy(unit_test_template), build_replacements(spec))
    unit_test_job = rendered["orchestrationJobs"][0]

    query_component = find_component_by_name(unit_test_job, "Query Result To Grid")
    set_component_string(
        query_component,
        parameter_slot="7",
        element_slot="1",
        value_slot="1",
        new_value=build_interactions_unit_test_sql(spec),
    )

    return unit_test_job


_tree_id_counter = 20000000


def next_tree_id() -> int:
    global _tree_id_counter
    _tree_id_counter += 1
    return _tree_id_counter


def add_jobs_tree_entry(name: str, jobs: list[dict], children: list[dict] | None = None) -> dict:
    return {
        "id": next_tree_id(),
        "name": name,
        "children": children or [],
        "jobs": jobs,
    }


def build_job_tree(
    tree_path: list[str],
    grouped_jobs: dict[str, list[dict]],
    grouped_unit_tests: dict[str, list[dict]],
    prefix_order: list[str],
) -> dict:
    prefix_nodes = []
    for prefix in [key for key in prefix_order if key in grouped_jobs or key in grouped_unit_tests]:
        unit_test_jobs = grouped_unit_tests.get(prefix, [])
        children = []
        if unit_test_jobs:
            children.append(add_jobs_tree_entry("Unit Test", unit_test_jobs))
        prefix_nodes.append(
            {
                "id": next_tree_id(),
                "name": prefix,
                "children": children,
                "jobs": grouped_jobs.get(prefix, []),
            }
        )

    current = {
        "id": next_tree_id(),
        "name": tree_path[-1],
        "children": prefix_nodes,
        "jobs": [],
    }
    for name in reversed(tree_path[:-1]):
        current = {"id": next_tree_id(), "name": name, "children": [current], "jobs": []}

    return {"id": next_tree_id(), "name": "ROOT", "children": [current], "jobs": []}


def job_tree_job_entry(job_id: int, name: str, job_type: str, description: str = "") -> dict:
    return {
        "id": job_id,
        "name": name,
        "description": description,
        "type": job_type,
        "tag": str(uuid.uuid4()),
    }


def infer_default_output(base_dir: Path, package_name: str) -> Path:
    safe_name = package_name.replace(" ", "_")
    return base_dir / f"{safe_name}.generated.json"


def infer_package_name(header_file: str, explicit_name: str | None) -> str:
    if explicit_name:
        return explicit_name
    stem = Path(header_file).stem
    if " - " in stem:
        return stem.split(" - ", 1)[1].strip().upper()
    return stem.replace("table_header", "").replace("-", " ").strip().upper() or "PACKAGE"


def build_config(args: argparse.Namespace) -> GeneratorConfig:
    base_dir = Path(args.base_dir).resolve()

    if args.preset == "interactions":
        header_file = args.header_file or "table_header - interactions.xlsx"
        detail_file = args.detail_file or "table_detail - interactions.xlsx"
        package_name = infer_package_name(header_file, args.package_name or "INTERACTIONS")
        tree_path = (args.tree_path or "02_DATA_WAREHOUSE/03_PRESENTATION/DCE2/INTERACTIONS").split("/")
        include_unit_tests = args.include_unit_tests if args.include_unit_tests is not None else True
        unit_test_template_file = args.unit_test_template_file or "delta_filled.json"
        output_path = Path(args.output).resolve() if args.output else base_dir / "INTERACTIONS.generated.json"
        version_override = args.version_override
    else:
        header_file = args.header_file or "table_header - template.xlsx"
        detail_file = args.detail_file or "table_detail - template.xlsx"
        package_name = infer_package_name(header_file, args.package_name)
        tree_path = (args.tree_path or f"02_DATA_WAREHOUSE/03_PRESENTATION/{package_name}").split("/")
        include_unit_tests = args.include_unit_tests if args.include_unit_tests is not None else False
        unit_test_template_file = args.unit_test_template_file if include_unit_tests else None
        output_path = Path(args.output).resolve() if args.output else infer_default_output(base_dir, package_name)
        version_override = args.version_override

    if include_unit_tests and not unit_test_template_file:
        raise ValueError("Unit tests were enabled but no unit-test template file was provided.")

    return GeneratorConfig(
        base_dir=base_dir,
        header_file=header_file,
        detail_file=detail_file,
        harm_template_file=args.harm_template_file or "matillion_full.json",
        harm_filter_template_file=args.harm_filter_template_file or "matillion_full_filter.json",
        output_path=output_path,
        package_name=package_name,
        tree_path=[segment for segment in tree_path if segment],
        include_transformations=args.include_transformations,
        include_unit_tests=include_unit_tests,
        unit_test_template_file=unit_test_template_file,
        version_override=version_override,
    )


def generate_package(config: GeneratorConfig) -> dict:
    header_df, detail_df = load_metadata(config.base_dir, config.header_file, config.detail_file)
    specs = build_table_specs(header_df, detail_df)
    prefix_order = build_prefix_order(specs)

    harm_template = load_json(config.base_dir / config.harm_template_file)
    harm_filter_template = load_json(config.base_dir / config.harm_filter_template_file)
    unit_test_template = (
        load_json(config.base_dir / config.unit_test_template_file)
        if config.include_unit_tests and config.unit_test_template_file
        else None
    )

    result = {
        "dbEnvironment": harm_template["dbEnvironment"],
        "version": config.version_override or harm_template["version"],
        "jobsTree": {},
        "orchestrationJobs": [],
        "transformationJobs": [],
        "variables": [],
        "environments": [],
    }

    grouped_harmonization_entries: dict[str, list[dict]] = {}
    grouped_unit_test_entries: dict[str, list[dict]] = {}
    grouped_harmonization_jobs: dict[str, list[dict]] = {}
    grouped_unit_test_jobs: dict[str, list[dict]] = {}
    offset_seed = 0

    for spec in specs:
        offset_seed += 100000
        harmonization_job, transformation_job = render_harmonization_job(
            spec,
            harm_template=harm_template,
            harm_filter_template=harm_filter_template,
        )
        harmonization_job = offset_ids(harmonization_job, offset_seed)
        transformation_job = offset_ids(transformation_job, offset_seed)
        grouped_harmonization_jobs.setdefault(spec["prefix"], []).append(harmonization_job)

        if config.include_transformations:
            result["transformationJobs"].append(transformation_job)

        grouped_harmonization_entries.setdefault(spec["prefix"], []).append(
            job_tree_job_entry(
                job_id=harmonization_job["id"],
                name=f"orc_harmonization_{spec['pl_name_lower']}",
                job_type="ORCHESTRATION",
            )
        )

    if config.include_unit_tests:
        assert unit_test_template is not None
        for spec in specs:
            offset_seed += 100000
            unit_test_job = render_unit_test_job(spec, unit_test_template)
            unit_test_job = offset_ids(unit_test_job, offset_seed)
            grouped_unit_test_jobs.setdefault(spec["prefix"], []).append(unit_test_job)
            grouped_unit_test_entries.setdefault(spec["prefix"], []).append(
                job_tree_job_entry(
                    job_id=unit_test_job["id"],
                    name=f"orc_unit_test_{spec['pl_name_lower']}",
                    job_type="ORCHESTRATION",
                    description=f"orc_harmonization_{spec['pl_name_lower']}",
                )
            )

    for prefix in [key for key in prefix_order if key in grouped_harmonization_jobs or key in grouped_unit_test_jobs]:
        result["orchestrationJobs"].extend(grouped_harmonization_jobs.get(prefix, []))
        result["orchestrationJobs"].extend(grouped_unit_test_jobs.get(prefix, []))

    result["jobsTree"] = build_job_tree(
        tree_path=config.tree_path,
        grouped_jobs=grouped_harmonization_entries,
        grouped_unit_tests=grouped_unit_test_entries,
        prefix_order=prefix_order,
    )

    with config.output_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)

    return {
        "output_path": str(config.output_path),
        "package_name": config.package_name,
        "tree_path": config.tree_path,
        "table_count": len(specs),
        "orchestration_jobs": len(result["orchestrationJobs"]),
        "transformation_jobs": len(result["transformationJobs"]),
        "unit_tests_enabled": config.include_unit_tests,
        "tables": [
            {
                "pl_name": spec["pl_name"],
                "historization": spec["historization"],
                "use_filter_template": spec["use_filter_template"],
                "primary_key_target_columns": spec["primary_key_target_columns"],
            }
            for spec in specs
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preset",
        choices=["interactions", "generic"],
        default="interactions",
        help="Preset defaults to use. 'interactions' keeps the original behavior.",
    )
    parser.add_argument(
        "--base-dir",
        default=str(DEFAULT_BASE_DIR),
        help="Directory containing the Excel metadata and Matillion templates.",
    )
    parser.add_argument("--header-file", default=None, help="Header Excel file name inside --base-dir.")
    parser.add_argument("--detail-file", default=None, help="Detail Excel file name inside --base-dir.")
    parser.add_argument(
        "--harm-template-file",
        default=None,
        help="Template JSON for non-filtered harmonization jobs. Defaults to matillion_full.json.",
    )
    parser.add_argument(
        "--harm-filter-template-file",
        default=None,
        help="Template JSON for filtered harmonization jobs. Defaults to matillion_full_filter.json.",
    )
    parser.add_argument(
        "--unit-test-template-file",
        default=None,
        help="Template JSON used for unit-test orchestration jobs.",
    )
    parser.add_argument("--package-name", default=None, help="Logical package name used for defaults and summaries.")
    parser.add_argument(
        "--tree-path",
        default=None,
        help="Folder path under ROOT, separated by '/'. Example: 02_DATA_WAREHOUSE/03_PRESENTATION/DCE2/GA",
    )
    parser.add_argument("--output", default=None, help="Output JSON path.")
    parser.add_argument(
        "--version-override",
        default=None,
        help="Override the top-level Matillion export version string.",
    )
    parser.add_argument(
        "--include-transformations",
        action="store_true",
        help="Also include top-level transformationJobs in the package export.",
    )
    parser.add_argument(
        "--include-unit-tests",
        dest="include_unit_tests",
        action="store_true",
        help="Include unit-test orchestration jobs. Best supported for interactions.",
    )
    parser.add_argument(
        "--no-unit-tests",
        dest="include_unit_tests",
        action="store_false",
        help="Disable unit-test orchestration jobs.",
    )
    parser.set_defaults(include_unit_tests=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = build_config(args)
    summary = generate_package(config)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
