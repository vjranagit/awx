"""Execution Environment specification models."""

from typing import Optional
from pydantic import BaseModel, Field


class CollectionSpec(BaseModel):
    """Ansible collection specification."""

    name: str = Field(description="Collection name (e.g., 'awx.awx')")
    version: str = Field(default="latest", description="Collection version")


class EESpec(BaseModel):
    """
    Execution Environment Specification.

    Defines all components needed to build an AWX execution environment
    container image.
    """

    # Base image configuration
    base_image: str = Field(
        default="quay.io/centos/centos:stream9", description="Base container image"
    )
    python_version: str = Field(default="3.11", description="Python version to use")

    # Ansible configuration
    ansible_core_version: str = Field(
        default=">=2.15.0,<2.16", description="Ansible core version requirement"
    )
    ansible_runner_version: str = Field(
        default="latest", description="Ansible runner version"
    )

    # Collections to install
    collections: list[CollectionSpec] = Field(
        default_factory=list, description="Ansible collections to install"
    )

    # System packages
    system_packages: list[str] = Field(
        default_factory=list, description="System packages to install via dnf/apt"
    )
    build_packages: list[str] = Field(
        default_factory=list,
        description="System packages needed only during build (compiler, headers)",
    )

    # Python packages
    python_packages: list[str] = Field(
        default_factory=list, description="Python packages to install via pip"
    )

    # Additional build steps
    additional_build_commands: list[str] = Field(
        default_factory=list, description="Additional commands to run during build"
    )
    additional_runtime_commands: list[str] = Field(
        default_factory=list, description="Additional commands to run in final image"
    )

    # Receptor configuration
    receptor_enabled: bool = Field(
        default=True, description="Include Receptor binary"
    )
    receptor_image: str = Field(
        default="quay.io/ansible/receptor:devel", description="Receptor source image"
    )

    # Entrypoint
    entrypoint: Optional[str] = Field(
        default=None, description="Custom entrypoint script"
    )
    default_command: str = Field(
        default="ansible-runner worker", description="Default container command"
    )

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "EESpec":
        """
        Load EE specification from YAML file.

        Args:
            yaml_path: Path to YAML file

        Returns:
            EESpec instance
        """
        import yaml
        from pathlib import Path

        content = Path(yaml_path).read_text()
        data = yaml.safe_load(content)
        return cls(**data)

    def to_yaml(self, yaml_path: str) -> None:
        """
        Save EE specification to YAML file.

        Args:
            yaml_path: Path to save YAML file
        """
        import yaml
        from pathlib import Path

        data = self.model_dump(exclude_defaults=True)
        Path(yaml_path).write_text(yaml.dump(data, sort_keys=False))


def get_default_awx_ee_spec() -> EESpec:
    """
    Get default AWX execution environment specification.

    Returns:
        EESpec with AWX defaults matching awx-ee project
    """
    return EESpec(
        base_image="quay.io/centos/centos:stream9",
        python_version="3.11",
        ansible_core_version=">=2.15.0,<2.16",
        collections=[
            CollectionSpec(name="awx.awx"),
            CollectionSpec(name="azure.azcollection", version=">=2.1.0"),
            CollectionSpec(name="amazon.aws"),
            CollectionSpec(name="theforeman.foreman"),
            CollectionSpec(name="google.cloud"),
            CollectionSpec(name="openstack.cloud"),
            CollectionSpec(name="community.vmware"),
            CollectionSpec(name="ovirt.ovirt"),
            CollectionSpec(name="kubernetes.core"),
            CollectionSpec(name="ansible.posix"),
            CollectionSpec(name="ansible.windows"),
            CollectionSpec(name="redhatinsights.insights"),
            CollectionSpec(name="kubevirt.core"),
        ],
        system_packages=[
            "git-core",
            "git-lfs",
            "subversion",
            "krb5-workstation",
            "sshpass",
            "rsync",
            "epel-release",
            "unzip",
            "podman-remote",
        ],
        build_packages=[
            "python3.11-devel",
            "libcurl-devel",
            "krb5-devel",
            "cmake",
            "gcc",
            "gcc-c++",
            "make",
            "openssl-devel",
        ],
        python_packages=[
            "ansible-runner",
            "ncclient",
            "paramiko",
            "pykerberos",
            "pyOpenSSL",
            "pypsrp[kerberos,credssp]",
            "pywinrm[kerberos,credssp]",
            "toml",
            "pexpect>=4.5",
            "python-daemon",
            "pyyaml",
            "six",
            "receptorctl",
        ],
        receptor_enabled=True,
        additional_runtime_commands=[
            "git lfs install --system",
            "alternatives --install /usr/bin/python python /usr/bin/python3.11 311",
            "mkdir -p /var/run/receptor",
        ],
    )
