"""CLI for final-form semantic processing engine."""

import json
import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from final_form import __version__
from final_form.pipeline import Pipeline, PipelineConfig

app = typer.Typer(
    name="final-form",
    help="Semantic processing engine for clinical measures.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"final-form version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """final-form: Semantic processing engine for clinical measures."""
    pass


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
            form_binding_registry = Path("form-binding-registry")

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

    console.print(f"[bold]final-form[/bold] v{__version__}")
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

    console.print(f"\n[green]Loaded binding:[/green] {pipeline.binding_spec.binding_id}@{pipeline.binding_spec.version}")
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
                        console.print(f"\n[yellow]Warning:[/yellow] Invalid JSON on line {line_num}: {e}")
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
