"""CLI for finalform semantic processing engine."""

import json
import os
import shutil
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from finalform import __version__
from finalform.config import (
    get_binding_registry_path,
    get_final_form_home,
    get_measure_registry_path,
    get_registry_root,
    load_global_config,
)
from finalform.pipeline import Pipeline, PipelineConfig

app = typer.Typer(
    name="finalform",
    help="Semantic processing engine for clinical measures.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"finalform version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """finalform: Semantic processing engine for clinical measures."""
    pass


@app.command()
def init(
    source: Annotated[
        Path | None,
        typer.Option(
            "--from",
            "-f",
            help="Source directory containing measure-registry and form-binding-registry",
        ),
    ] = None,
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing registries",
    ),
) -> None:
    """Initialize finalform global configuration and sync registries.

    Creates:
      ~/.config/finalform/config.yaml
      ~/.config/finalform/registry/measure-registry/
      ~/.config/finalform/registry/form-binding-registry/

    If --from is provided, copies registries from that directory.
    Otherwise, looks for registries in current directory.

    Examples:
        finalform init --from /workspace/finalform
        finalform init  # Uses current directory
    """
    import yaml

    home = get_final_form_home()
    registry_root = get_registry_root()
    measure_dest = get_measure_registry_path()
    binding_dest = get_binding_registry_path()

    # Determine source directory
    if source is None:
        source = Path.cwd()

    source_measure = source / "measure-registry"
    source_binding = source / "form-binding-registry"

    # Validate source registries exist
    if not source_measure.exists():
        console.print(f"[red]Error:[/red] measure-registry not found at {source_measure}")
        console.print("Use --from to specify source directory")
        raise typer.Exit(1)

    if not source_binding.exists():
        console.print(f"[red]Error:[/red] form-binding-registry not found at {source_binding}")
        console.print("Use --from to specify source directory")
        raise typer.Exit(1)

    # Check if already initialized
    if registry_root.exists() and not force:
        console.print(f"[yellow]Warning:[/yellow] Registry already exists at {registry_root}")
        console.print("Use --force to overwrite")
        raise typer.Exit(1)

    # Create directory structure
    console.print(f"[bold]Initializing finalform at {home}[/bold]")
    home.mkdir(parents=True, exist_ok=True)
    registry_root.mkdir(parents=True, exist_ok=True)

    # Copy measure registry
    console.print(f"  Syncing measure-registry from {source_measure}...")
    if measure_dest.exists():
        shutil.rmtree(measure_dest)
    shutil.copytree(source_measure, measure_dest)
    measure_count = len(list(measure_dest.glob("measures/*")))
    console.print(f"    [green]✓[/green] {measure_count} measures synced")

    # Copy form binding registry
    console.print(f"  Syncing form-binding-registry from {source_binding}...")
    if binding_dest.exists():
        shutil.rmtree(binding_dest)
    shutil.copytree(source_binding, binding_dest)
    binding_count = len(list(binding_dest.glob("bindings/*")))
    console.print(f"    [green]✓[/green] {binding_count} bindings synced")

    # Create config file
    config_path = home / "config.yaml"
    config = {
        "default_measure_registry_path": str(measure_dest),
        "default_form_binding_registry_path": str(binding_dest),
    }
    with open(config_path, "w") as f:
        yaml.dump(config, f, sort_keys=False)
    console.print(f"  [green]✓[/green] Created config at {config_path}")

    console.print("\n[green]✓ Initialized finalform[/green]")
    console.print(f"  Home: {home}")
    console.print(f"  Registry: {registry_root}")


@app.command()
def run(
    input_path: Annotated[
        Path,
        typer.Option("--in", "-i", help="Input JSONL file path"),
    ],
    output_path: Annotated[
        Path,
        typer.Option("--out", "-o", help="Output JSONL file path"),
    ],
    binding: Annotated[
        str,
        typer.Option("--binding", "-b", help="Binding spec ID (required)"),
    ],
    binding_version: Annotated[
        str | None,
        typer.Option("--binding-version", help="Binding spec version (default: latest)"),
    ] = None,
    measure_registry: Annotated[
        Path | None,
        typer.Option(
            "--measure-registry",
            envvar="FINAL_FORM_MEASURE_REGISTRY",
            help="Path to measure registry",
        ),
    ] = None,
    form_binding_registry: Annotated[
        Path | None,
        typer.Option(
            "--form-binding-registry",
            envvar="FINAL_FORM_BINDING_REGISTRY",
            help="Path to form binding registry",
        ),
    ] = None,
    diagnostics: Annotated[
        Path | None,
        typer.Option("--diagnostics", "-d", help="Diagnostics output JSONL path"),
    ] = None,
) -> None:
    """Process form responses and emit MeasurementEvents.

    Requires:
    - Input JSONL file with canonical form responses
    - Output path for MeasurementEvents JSONL
    - Binding spec ID (required, no auto-detection)
    """
    # Resolve registry paths
    if measure_registry is None:
        env_path = os.environ.get("FINAL_FORM_MEASURE_REGISTRY")
        if env_path:
            measure_registry = Path(env_path)
        else:
            measure_registry = Path("measure-registry")



    if form_binding_registry is None:
        env_path = os.environ.get("FINAL_FORM_BINDING_REGISTRY")
        if env_path:
            form_binding_registry = Path(env_path)
        else:
             # Check global config
            global_config = load_global_config()
            if global_config.default_form_binding_registry_path:
                form_binding_registry = Path(global_config.default_form_binding_registry_path)
            else:
                form_binding_registry = Path("form-binding-registry")

    # Resolve measure registry from config if still default
    if str(measure_registry) == "measure-registry":
         global_config = load_global_config()
         if global_config.default_measure_registry_path:
             measure_registry = Path(global_config.default_measure_registry_path)

    # Validate paths exist
    if not input_path.exists():
        console.print(f"[red]Error:[/red] Input file not found: {input_path}")
        raise typer.Exit(1)

    if not measure_registry.exists():
        console.print(f"[red]Error:[/red] Measure registry not found: {measure_registry}")
        raise typer.Exit(1)

    if not form_binding_registry.exists():
        console.print(f"[red]Error:[/red] Form binding registry not found: {form_binding_registry}")
        raise typer.Exit(1)

    console.print(f"[bold]finalform[/bold] v{__version__}")
    console.print(f"  Input: {input_path}")
    console.print(f"  Output: {output_path}")
    console.print(f"  Binding: {binding}@{binding_version or 'latest'}")
    console.print(f"  Measure Registry: {measure_registry}")
    console.print(f"  Binding Registry: {form_binding_registry}")
    if diagnostics:
        console.print(f"  Diagnostics: {diagnostics}")

    # Resolve schema paths
    schema_dir = Path("schemas")
    measure_schema = schema_dir / "measure_spec.schema.json"
    binding_schema = schema_dir / "form_binding_spec.schema.json"

    # Initialize pipeline
    try:
        config = PipelineConfig(
            measure_registry_path=measure_registry,
            binding_registry_path=form_binding_registry,
            binding_id=binding,
            binding_version=binding_version,
            measure_schema_path=measure_schema if measure_schema.exists() else None,
            binding_schema_path=binding_schema if binding_schema.exists() else None,
        )
        pipeline = Pipeline(config)
    except Exception as e:
        console.print(f"\n[red]Error initializing pipeline:[/red] {e}")
        raise typer.Exit(1)

    binding_info = f"{pipeline.binding_spec.binding_id}@{pipeline.binding_spec.version}"
    console.print(f"\n[green]Loaded binding:[/green] {binding_info}")
    console.print(f"[green]Loaded measures:[/green] {', '.join(pipeline.measures.keys())}")

    # Process input file
    events_written = 0
    diagnostics_written = 0
    success_count = 0
    partial_count = 0
    failed_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing forms...", total=None)

        with open(input_path) as f_in, open(output_path, "w") as f_out:
            # Open diagnostics file if requested
            f_diag = open(diagnostics, "w") if diagnostics else None

            try:
                for line_num, line in enumerate(f_in, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        form_response = json.loads(line)
                    except json.JSONDecodeError as e:
                        console.print(
                            f"\n[yellow]Warning:[/yellow] Invalid JSON on line {line_num}: {e}"
                        )
                        continue

                    # Process the form response
                    result = pipeline.process(form_response)

                    # Write events
                    for event in result.events:
                        f_out.write(event.model_dump_json(by_alias=True) + "\n")
                        events_written += 1

                    # Write diagnostics
                    if f_diag:
                        f_diag.write(result.diagnostics.model_dump_json() + "\n")
                        diagnostics_written += 1

                    # Track status
                    status = result.diagnostics.status.value
                    if status == "success":
                        success_count += 1
                    elif status == "partial":
                        partial_count += 1
                    else:
                        failed_count += 1

                    progress.update(task, description=f"Processed {line_num} forms...")
            finally:
                if f_diag:
                    f_diag.close()

    # Print summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Forms processed: {success_count + partial_count + failed_count}")
    console.print(f"  [green]Success:[/green] {success_count}")
    if partial_count:
        console.print(f"  [yellow]Partial:[/yellow] {partial_count}")
    if failed_count:
        console.print(f"  [red]Failed:[/red] {failed_count}")
    console.print(f"  Events written: {events_written}")
    if diagnostics:
        console.print(f"  Diagnostics written: {diagnostics_written}")


@app.command()
def validate(
    spec_type: Annotated[
        str,
        typer.Argument(help="Type of spec to validate: measure, binding"),
    ],
    spec_path: Annotated[
        Path,
        typer.Argument(help="Path to the spec file"),
    ],
    schema_path: Annotated[
        Path | None,
        typer.Option("--schema", "-s", help="Path to the schema file"),
    ] = None,
) -> None:
    """Validate a spec file against its schema."""
    import json

    import jsonschema

    if not spec_path.exists():
        console.print(f"[red]Error:[/red] Spec file not found: {spec_path}")
        raise typer.Exit(1)

    # Determine schema path if not provided
    if schema_path is None:
        schema_dir = Path("schemas")
        if spec_type == "measure":
            schema_path = schema_dir / "measure_spec.schema.json"
        elif spec_type == "binding":
            schema_path = schema_dir / "form_binding_spec.schema.json"
        else:
            console.print(f"[red]Error:[/red] Unknown spec type: {spec_type}")
            raise typer.Exit(1)

    if not schema_path.exists():
        console.print(f"[red]Error:[/red] Schema file not found: {schema_path}")
        raise typer.Exit(1)

    with open(spec_path) as f:
        spec = json.load(f)

    with open(schema_path) as f:
        schema = json.load(f)

    try:
        jsonschema.validate(spec, schema)
        console.print(f"[green]Valid:[/green] {spec_path}")
    except jsonschema.ValidationError as e:
        console.print(f"[red]Invalid:[/red] {e.message}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
