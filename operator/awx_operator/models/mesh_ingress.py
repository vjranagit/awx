"""AWXMeshIngress Custom Resource Definition models."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class AWXMeshIngressSpec(BaseModel):
    """
    AWXMeshIngress Custom Resource Specification.

    Defines parameters for Receptor mesh ingress configuration.
    """

    deployment_name: str = Field(description="Name of AWX deployment")
    receptor_image: str = Field(
        default="quay.io/ansible/receptor:devel", description="Receptor image"
    )
    receptor_log_level: str = Field(
        default="info", description="Receptor log level (debug, info, warning, error)"
    )
    resource_requirements: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="Resource requirements for receptor pod"
    )
    service_type: str = Field(
        default="LoadBalancer",
        description="Service type (ClusterIP, NodePort, LoadBalancer)",
    )
    node_port: Optional[int] = Field(
        default=None, ge=30000, le=32767, description="NodePort port number"
    )
    load_balancer_ip: Optional[str] = Field(
        default=None, description="LoadBalancer IP address"
    )
    service_annotations: dict[str, str] = Field(
        default_factory=dict, description="Service annotations"
    )
    service_labels: dict[str, str] = Field(
        default_factory=dict, description="Service labels"
    )
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
    node_selector: Optional[str] = Field(
        default=None, description="Node selector for receptor pod"
    )
    tolerations: Optional[str] = Field(
        default=None, description="Tolerations for receptor pod"
    )


class AWXMeshIngressStatus(BaseModel):
    """
    AWXMeshIngress Custom Resource Status.

    Represents the observed state of mesh ingress.
    """

    conditions: list[dict[str, Any]] = Field(
        default_factory=list, description="Status conditions"
    )
    receptor_image: Optional[str] = Field(
        default=None, description="Deployed receptor image"
    )
    service_name: Optional[str] = Field(default=None, description="Service name")
    load_balancer_ip: Optional[str] = Field(
        default=None, description="LoadBalancer IP if assigned"
    )

    def add_condition(
        self,
        type_: str,
        status: str,
        reason: str,
        message: str,
        last_transition_time: Optional[str] = None,
    ) -> None:
        """Add or update a status condition."""
        from datetime import datetime

        if last_transition_time is None:
            last_transition_time = datetime.utcnow().isoformat() + "Z"

        # Remove existing condition of same type
        self.conditions = [c for c in self.conditions if c.get("type") != type_]

        # Add new condition
        self.conditions.append(
            {
                "type": type_,
                "status": status,
                "reason": reason,
                "message": message,
                "lastTransitionTime": last_transition_time,
            }
        )
