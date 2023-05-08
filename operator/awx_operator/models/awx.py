"""AWX Custom Resource Definition models."""

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class AWXSpec(BaseModel):
    """
    AWX Custom Resource Specification.

    Defines the desired state of an AWX deployment on Kubernetes.
    """

    # Admin user configuration
    admin_user: str = Field(default="admin", description="AWX admin username")
    admin_email: str = Field(default="admin@localhost", description="AWX admin email")
    admin_password_secret: Optional[str] = Field(
        default=None, description="Secret containing admin password"
    )

    # Image configuration
    image: Optional[str] = Field(default=None, description="AWX image to deploy")
    image_version: str = Field(default="24.6.1", description="AWX version tag")
    image_pull_policy: str = Field(
        default="IfNotPresent", description="Image pull policy"
    )
    image_pull_secrets: list[str] = Field(
        default_factory=list, description="Image pull secrets"
    )
    ee_images: list[dict[str, str]] = Field(
        default_factory=list, description="Execution environment images"
    )

    # PostgreSQL configuration
    postgres_configuration_secret: Optional[str] = Field(
        default=None, description="PostgreSQL configuration secret"
    )
    postgres_data_path: str = Field(
        default="/var/lib/postgresql/data/pgdata", description="PostgreSQL data path"
    )
    postgres_storage_class: Optional[str] = Field(
        default=None, description="Storage class for PostgreSQL PVC"
    )
    postgres_storage_requirements: dict[str, str] = Field(
        default_factory=lambda: {"requests": {"storage": "8Gi"}},
        description="PostgreSQL storage requirements",
    )
    postgres_resource_requirements: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="PostgreSQL resource requirements"
    )
    postgres_selector: Optional[str] = Field(
        default=None, description="PostgreSQL node selector"
    )
    postgres_tolerations: Optional[str] = Field(
        default=None, description="PostgreSQL tolerations"
    )
    postgres_image: str = Field(
        default="postgres:13", description="PostgreSQL image"
    )
    postgres_init_container_resource_requirements: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="PostgreSQL init container resources"
    )

    # Redis configuration
    redis_image: str = Field(default="redis:7", description="Redis image")
    redis_resource_requirements: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="Redis resource requirements"
    )

    # AWX task/web configuration
    task_replicas: int = Field(default=1, ge=0, description="Number of task replicas")
    web_replicas: int = Field(default=1, ge=1, description="Number of web replicas")
    task_resource_requirements: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="Task resource requirements"
    )
    web_resource_requirements: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="Web resource requirements"
    )
    ee_resource_requirements: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="EE resource requirements"
    )

    # Service configuration
    service_type: str = Field(
        default="ClusterIP", description="Service type (ClusterIP, NodePort, LoadBalancer)"
    )
    service_labels: dict[str, str] = Field(
        default_factory=dict, description="Additional service labels"
    )
    service_annotations: dict[str, str] = Field(
        default_factory=dict, description="Service annotations"
    )
    nodeport_port: Optional[int] = Field(
        default=None, ge=30000, le=32767, description="NodePort port number"
    )

    # Ingress configuration
    ingress_type: str = Field(
        default="none", description="Ingress type (none, Ingress, Route)"
    )
    ingress_class_name: Optional[str] = Field(
        default=None, description="Ingress class name"
    )
    ingress_annotations: dict[str, str] = Field(
        default_factory=dict, description="Ingress annotations"
    )
    ingress_tls_secret: Optional[str] = Field(
        default=None, description="TLS secret for ingress"
    )
    hostname: Optional[str] = Field(default=None, description="Hostname for ingress")

    # Projects/data configuration
    projects_persistence: bool = Field(
        default=False, description="Enable projects persistence"
    )
    projects_storage_class: Optional[str] = Field(
        default=None, description="Projects storage class"
    )
    projects_storage_size: str = Field(
        default="8Gi", description="Projects storage size"
    )
    projects_existing_claim: Optional[str] = Field(
        default=None, description="Existing PVC for projects"
    )

    # Security
    security_context_settings: dict[str, Any] = Field(
        default_factory=dict, description="Pod security context"
    )
    service_account_name: Optional[str] = Field(
        default=None, description="Service account name"
    )

    # Additional settings
    extra_settings: list[dict[str, Any]] = Field(
        default_factory=list, description="Extra AWX settings"
    )
    extra_volumes: list[dict[str, Any]] = Field(
        default_factory=list, description="Extra volumes"
    )
    init_container_image: Optional[str] = Field(
        default=None, description="Init container image"
    )
    init_container_commands: Optional[str] = Field(
        default=None, description="Init container commands"
    )
    init_projects_container_image: Optional[str] = Field(
        default=None, description="Init projects container image"
    )

    # Deployment configuration
    node_selector: Optional[str] = Field(
        default=None, description="Node selector for pods"
    )
    tolerations: Optional[str] = Field(default=None, description="Pod tolerations")
    topology_spread_constraints: Optional[str] = Field(
        default=None, description="Topology spread constraints"
    )

    # Metrics and monitoring
    metrics_utility_enabled: bool = Field(
        default=False, description="Enable metrics utility sidecar"
    )
    metrics_utility_image: str = Field(
        default="quay.io/prometheus/node-exporter:latest",
        description="Metrics utility image",
    )

    # Garbage collection
    garbage_collect_secrets: bool = Field(
        default=False, description="Enable secret garbage collection"
    )

    # LDAP integration
    ldap_password_secret: Optional[str] = Field(
        default=None, description="LDAP password secret"
    )
    ldap_cacert_secret: Optional[str] = Field(
        default=None, description="LDAP CA cert secret"
    )

    # Bundle CA
    bundle_cacert_secret: Optional[str] = Field(
        default=None, description="Bundle CA cert secret"
    )

    # Auto-upgrade
    auto_upgrade: bool = Field(default=True, description="Enable auto-upgrade")

    # Task privileged
    task_privileged: bool = Field(
        default=False, description="Run task containers as privileged"
    )

    # No log
    no_log: bool = Field(default=True, description="Hide sensitive logs")

    @field_validator("service_type")
    @classmethod
    def validate_service_type(cls, v: str) -> str:
        """Validate service type is one of the allowed values."""
        allowed = ["ClusterIP", "NodePort", "LoadBalancer"]
        if v not in allowed:
            raise ValueError(f"service_type must be one of {allowed}")
        return v

    @field_validator("ingress_type")
    @classmethod
    def validate_ingress_type(cls, v: str) -> str:
        """Validate ingress type is one of the allowed values."""
        allowed = ["none", "Ingress", "Route", "ingress", "route"]
        if v not in allowed:
            raise ValueError(f"ingress_type must be one of {allowed}")
        return v.lower() if v.lower() in ["none", "ingress", "route"] else v

    @field_validator("image_pull_policy")
    @classmethod
    def validate_image_pull_policy(cls, v: str) -> str:
        """Validate image pull policy."""
        allowed = ["Always", "Never", "IfNotPresent"]
