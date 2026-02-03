"""Execution Environment Builder implementation."""

import logging
import subprocess
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from awx_ee.models.ee_spec import EESpec

logger = logging.getLogger(__name__)


class EEBuilder:
    """
    Execution Environment Builder.

    Builds container images for AWX execution environments from
    declarative specifications.
    """

    def __init__(self, spec: EESpec, output_dir: Optional[Path] = None):
        """
        Initialize builder.

        Args:
            spec: Execution environment specification
            output_dir: Directory for generated files (default: current dir)
        """
        self.spec = spec
        self.output_dir = output_dir or Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate_dockerfile(self) -> Path:
        """
        Generate Dockerfile from specification.

        Returns:
            Path to generated Dockerfile
        """
        logger.info("Generating Dockerfile")

        template = self.jinja_env.get_template("Dockerfile.j2")

        # Prepare template variables
        context = {
            "base_image": self.spec.base_image,
            "python_version": self.spec.python_version,
            "ansible_core_version": self.spec.ansible_core_version,
            "collections": self.spec.collections,
            "system_packages": self.spec.system_packages,
            "build_packages": self.spec.build_packages,
            "python_packages": self.spec.python_packages,
            "receptor_enabled": self.spec.receptor_enabled,
            "receptor_image": self.spec.receptor_image,
            "entrypoint": self.spec.entrypoint,
            "default_command_args": self._format_command_args(
                self.spec.default_command
            ),
            "additional_runtime_commands": self.spec.additional_runtime_commands,
            "version": "1.0.0",
        }

        # Render Dockerfile
        dockerfile_content = template.render(**context)

        # Write to file
        dockerfile_path = self.output_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)

        logger.info(f"Generated Dockerfile at {dockerfile_path}")
        return dockerfile_path

    def build_image(
        self,
        tag: str,
        runtime: str = "podman",
        build_args: Optional[dict[str, str]] = None,
        no_cache: bool = False,
    ) -> None:
        """
        Build container image.

        Args:
            tag: Image tag (e.g., 'quay.io/myorg/awx-ee:latest')
            runtime: Container runtime ('podman' or 'docker')
            build_args: Additional build arguments
            no_cache: Disable build cache

        Raises:
            subprocess.CalledProcessError: If build fails
        """
        logger.info(f"Building container image: {tag}")

        # Generate Dockerfile first
        dockerfile = self.generate_dockerfile()

        # Build command
        cmd = [runtime, "build", "-t", tag, "-f", str(dockerfile)]

        if no_cache:
            cmd.append("--no-cache")

        if build_args:
            for key, value in build_args.items():
                cmd.extend(["--build-arg", f"{key}={value}"])

        cmd.append(str(self.output_dir))

        # Run build
        logger.info(f"Running: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True, cwd=self.output_dir)
            logger.info(f"Successfully built image: {tag}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to build image: {e}")
            raise

    def push_image(self, tag: str, runtime: str = "podman") -> None:
        """
        Push container image to registry.

        Args:
            tag: Image tag to push
            runtime: Container runtime ('podman' or 'docker')

        Raises:
            subprocess.CalledProcessError: If push fails
        """
        logger.info(f"Pushing container image: {tag}")

        cmd = [runtime, "push", tag]

        try:
            subprocess.run(cmd, check=True)
            logger.info(f"Successfully pushed image: {tag}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to push image: {e}")
            raise

    def generate_requirements_file(self) -> Path:
        """
        Generate requirements.txt from Python packages.

        Returns:
            Path to requirements.txt file
        """
        logger.info("Generating requirements.txt")

        req_path = self.output_dir / "requirements.txt"

        # Add ansible-core first
        requirements = [f"ansible-core{self.spec.ansible_core_version}"]

        # Add other packages
        requirements.extend(self.spec.python_packages)

        req_path.write_text("\n".join(requirements) + "\n")

        logger.info(f"Generated requirements.txt at {req_path}")
        return req_path

    def generate_collections_file(self) -> Path:
        """
        Generate collections requirements YAML file.

        Returns:
            Path to requirements.yml file
        """
        import yaml

        logger.info("Generating collections requirements.yml")

        collections_data = {
            "collections": [
                (
                    {"name": col.name, "version": col.version}
                    if col.version != "latest"
                    else {"name": col.name}
                )
                for col in self.spec.collections
            ]
        }

        req_path = self.output_dir / "requirements.yml"
        req_path.write_text(yaml.dump(collections_data, sort_keys=False))

        logger.info(f"Generated requirements.yml at {req_path}")
        return req_path

    @staticmethod
    def _format_command_args(command: str) -> str:
        """
        Format command string for Dockerfile CMD.

        Args:
            command: Command string (e.g., 'ansible-runner worker')

        Returns:
            Formatted command args (e.g., '"ansible-runner", "worker"')
        """
        parts = command.split()
        return ", ".join(f'"{part}"' for part in parts)
