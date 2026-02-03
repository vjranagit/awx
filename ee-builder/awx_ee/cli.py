"""Command-line interface for AWX EE builder."""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from awx_ee.builder import EEBuilder
from awx_ee.models.ee_spec import EESpec, get_default_awx_ee_spec

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="1.0.0")
def cli() -> None:
    """AWX Execution Environment Builder - Build EE container images."""
    pass


@cli.command()
@click.option(
    "--spec",
    "-s",
    type=click.Path(exists=True, path_type=Path),
    help="Path to EE specification YAML file",
)
@click.option(
    "--tag",
    "-t",
    required=True,
    help="Container image tag (e.g., quay.io/myorg/awx-ee:latest)",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Output directory for generated files",
)
@click.option(
    "--runtime",
    "-r",
    type=click.Choice(["podman", "docker"]),
    default="podman",
    help="Container runtime to use",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable build cache",
)
@click.option(
    "--push",
    is_flag=True,
    help="Push image to registry after build",
)
@click.option(
    "--use-defaults",
    is_flag=True,
    help="Use default AWX EE specification",
)
def build(
    spec: Optional[Path],
    tag: str,
    output_dir: Path,
    runtime: str,
    no_cache: bool,
    push: bool,
    use_defaults: bool,
) -> None:
    """Build an execution environment container image."""
    try:
        # Load specification
        if use_defaults:
            logger.info("Using default AWX EE specification")
            ee_spec = get_default_awx_ee_spec()
        elif spec:
            logger.info(f"Loading EE spec from {spec}")
            ee_spec = EESpec.from_yaml(str(spec))
        else:
            click.echo("Error: Must provide --spec or --use-defaults", err=True)
            sys.exit(1)

        # Create builder
        builder = EEBuilder(ee_spec, output_dir=output_dir)

        # Generate Dockerfile
        dockerfile = builder.generate_dockerfile()
        click.echo(f"Generated Dockerfile: {dockerfile}")

        # Generate requirements files
        req_txt = builder.generate_requirements_file()
        click.echo(f"Generated requirements.txt: {req_txt}")

        req_yml = builder.generate_collections_file()
        click.echo(f"Generated requirements.yml: {req_yml}")

        # Build image
        click.echo(f"Building image: {tag}")
        builder.build_image(tag=tag, runtime=runtime, no_cache=no_cache)
        click.echo(f"Successfully built: {tag}")

        # Push if requested
        if push:
            click.echo(f"Pushing image: {tag}")
            builder.push_image(tag=tag, runtime=runtime)
            click.echo(f"Successfully pushed: {tag}")

    except Exception as e:
        logger.exception("Build failed")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    required=True,
    help="Output path for EE spec YAML file",
)
@click.option(
    "--use-defaults",
    is_flag=True,
    help="Generate default AWX EE specification",
)
def init(output: Path, use_defaults: bool) -> None:
    """Initialize a new EE specification file."""
    try:
        if use_defaults:
            spec = get_default_awx_ee_spec()
        else:
            # Create minimal spec
            spec = EESpec()

        spec.to_yaml(str(output))
        click.echo(f"Created EE specification: {output}")
        click.echo("Edit this file and run 'awx-ee-build build --spec <file>' to build")

    except Exception as e:
        logger.exception("Init failed")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--spec",
    "-s",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to EE specification YAML file",
)
def validate(spec: Path) -> None:
    """Validate an EE specification file."""
    try:
        ee_spec = EESpec.from_yaml(str(spec))
        click.echo(f"✓ Valid EE specification")
        click.echo(f"  Base image: {ee_spec.base_image}")
        click.echo(f"  Python: {ee_spec.python_version}")
        click.echo(f"  Ansible: {ee_spec.ansible_core_version}")
        click.echo(f"  Collections: {len(ee_spec.collections)}")
        click.echo(f"  System packages: {len(ee_spec.system_packages)}")
        click.echo(f"  Python packages: {len(ee_spec.python_packages)}")

    except Exception as e:
        logger.exception("Validation failed")
        click.echo(f"✗ Invalid EE specification: {e}", err=True)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
