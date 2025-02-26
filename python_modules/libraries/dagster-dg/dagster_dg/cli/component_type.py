import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from dagster_dg.cli.global_options import dg_global_options
from dagster_dg.component import RemoteComponentRegistry
from dagster_dg.component_key import GlobalComponentKey
from dagster_dg.config import normalize_cli_config
from dagster_dg.context import DgContext
from dagster_dg.docs import html_from_markdown, markdown_for_component_type, open_html_in_browser
from dagster_dg.scaffold import scaffold_component_type
from dagster_dg.utils import (
    DgClickCommand,
    DgClickGroup,
    exit_with_error,
    generate_missing_component_type_error_message,
)


@click.group(name="component-type", cls=DgClickGroup)
def component_type_group():
    """Commands for operating on components types."""


# ########################
# ##### SCAFFOLD
# ########################


@component_type_group.command(name="scaffold", cls=DgClickCommand)
@click.argument("name", type=str)
@dg_global_options
@click.pass_context
def component_type_scaffold_command(
    context: click.Context, name: str, **global_options: object
) -> None:
    """Scaffold of a custom Dagster component type.

    This command must be run inside a Dagster code location directory. The component type scaffold
    will be placed in submodule `<code_location_name>.lib.<name>`.
    """
    cli_config = normalize_cli_config(global_options, context)
    dg_context = DgContext.for_component_library_environment(Path.cwd(), cli_config)
    registry = RemoteComponentRegistry.from_dg_context(dg_context)
    component_key = GlobalComponentKey(name=name, namespace=dg_context.root_package_name)
    if registry.has_global(component_key):
        exit_with_error(f"Component type`{component_key.to_typename()}` already exists.")

    scaffold_component_type(dg_context, name)


# ########################
# ##### DOCS
# ########################


@component_type_group.command(name="docs", cls=DgClickCommand)
@click.argument("component_type", type=str)
@click.option("--output", type=click.Choice(["browser", "cli"]), default="browser")
@dg_global_options
@click.pass_context
def component_type_docs_command(
    context: click.Context,
    component_type: str,
    output: str,
    **global_options: object,
) -> None:
    """Get detailed information on a registered Dagster component type."""
    cli_config = normalize_cli_config(global_options, context)
    dg_context = DgContext.for_defined_registry_environment(Path.cwd(), cli_config)
    registry = RemoteComponentRegistry.from_dg_context(dg_context)
    component_key = GlobalComponentKey.from_typename(component_type)
    if not registry.has_global(component_key):
        exit_with_error(f"Component type`{component_type}` not found.")

    markdown = markdown_for_component_type(registry.get_global(component_key))
    if output == "browser":
        open_html_in_browser(html_from_markdown(markdown))
    else:
        click.echo(html_from_markdown(markdown))


# ########################
# ##### INFO
# ########################


@component_type_group.command(name="info", cls=DgClickCommand)
@click.argument("component_type", type=str)
@click.option("--description", is_flag=True, default=False)
@click.option("--scaffold-params-schema", is_flag=True, default=False)
@click.option("--component-params-schema", is_flag=True, default=False)
@dg_global_options
@click.pass_context
def component_type_info_command(
    context: click.Context,
    component_type: str,
    description: bool,
    scaffold_params_schema: bool,
    component_params_schema: bool,
    **global_options: object,
) -> None:
    """Get detailed information on a registered Dagster component type."""
    cli_config = normalize_cli_config(global_options, context)
    dg_context = DgContext.for_defined_registry_environment(Path.cwd(), cli_config)
    registry = RemoteComponentRegistry.from_dg_context(dg_context)
    component_key = GlobalComponentKey.from_typename(component_type)
    if not registry.has_global(component_key):
        exit_with_error(generate_missing_component_type_error_message(component_type))
    elif sum([description, scaffold_params_schema, component_params_schema]) > 1:
        exit_with_error(
            "Only one of --description, --scaffold-params-schema, and --component-params-schema can be specified."
        )

    component_type_metadata = registry.get_global(component_key)

    if description:
        if component_type_metadata.description:
            click.echo(component_type_metadata.description)
        else:
            click.echo("No description available.")
    elif scaffold_params_schema:
        if component_type_metadata.scaffold_params_schema:
            click.echo(_serialize_json_schema(component_type_metadata.scaffold_params_schema))
        else:
            click.echo("No scaffold params schema defined.")
    elif component_params_schema:
        if component_type_metadata.component_params_schema:
            click.echo(_serialize_json_schema(component_type_metadata.component_params_schema))
        else:
            click.echo("No component params schema defined.")

    # print all available metadata
    else:
        click.echo(component_type)
        if component_type_metadata.description:
            click.echo("\nDescription:\n")
            click.echo(component_type_metadata.description)
        if component_type_metadata.scaffold_params_schema:
            click.echo("\nScaffold params schema:\n")
            click.echo(_serialize_json_schema(component_type_metadata.scaffold_params_schema))
        if component_type_metadata.component_params_schema:
            click.echo("\nComponent params schema:\n")
            click.echo(_serialize_json_schema(component_type_metadata.component_params_schema))


def _serialize_json_schema(schema: Mapping[str, Any]) -> str:
    return json.dumps(schema, indent=4)


# ########################
# ##### LIST
# ########################


@component_type_group.command(name="list", cls=DgClickCommand)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Output as JSON instead of a table.",
)
@dg_global_options
@click.pass_context
def component_type_list(
    context: click.Context, output_json: bool, **global_options: object
) -> None:
    """List registered Dagster components in the current code location environment."""
    cli_config = normalize_cli_config(global_options, context)
    dg_context = DgContext.for_defined_registry_environment(Path.cwd(), cli_config)
    registry = RemoteComponentRegistry.from_dg_context(dg_context)

    sorted_keys = sorted(registry.global_keys(), key=lambda k: k.to_typename())

    # JSON
    if output_json:
        output: list[dict[str, object]] = []
        for key in sorted_keys:
            component_type_metadata = registry.get_global(key)
            output.append(
                {
                    "key": key.to_typename(),
                    "summary": component_type_metadata.summary,
                }
            )
        click.echo(json.dumps(output, indent=4))

    # TABLE
    else:
        table = Table(border_style="dim")
        table.add_column("Component Type", style="bold cyan", no_wrap=True)
        table.add_column("Summary")
        for key in sorted(registry.global_keys(), key=lambda k: k.to_typename()):
            table.add_row(key.to_typename(), registry.get_global(key).summary)
        console = Console()
        console.print(table)
