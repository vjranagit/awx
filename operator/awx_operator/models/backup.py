"""AWXBackup Custom Resource Definition models."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class AWXBackupSpec(BaseModel):
    """
    AWXBackup Custom Resource Specification.

    Defines parameters for backing up an AWX deployment.
    """

    deployment_name: str = Field(description="Name of AWX deployment to backup")
    backup_pvc: Optional[str] = Field(
        default=None, description="PVC name for storing backups"
    )
    backup_pvc_namespace: Optional[str] = Field(
        default=None, description="Namespace of backup PVC"
    )
    backup_storage_class: Optional[str] = Field(
        default=None, description="Storage class for backup PVC"
    )
    backup_storage_requirements: dict[str, str] = Field(
        default_factory=lambda: {"requests": {"storage": "5Gi"}},
        description="Backup storage requirements",
    )
    backup_resource_requirements: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="Backup job resource requirements"
    )
    postgres_image: Optional[str] = Field(
        default="postgres:13", description="PostgreSQL image for backup"
    )
    postgres_label_selector: Optional[str] = Field(
        default=None, description="Label selector for PostgreSQL pod"
    )
    clean_backup_on_delete: bool = Field(
        default=False, description="Delete backup PVC when backup CR is deleted"
    )
    no_log: bool = Field(default=True, description="Hide sensitive information in logs")
    pg_dump_suffix: Optional[str] = Field(
        default=None, description="Suffix for pg_dump filename"
    )
    set_self_ownerref: bool = Field(
        default=False, description="Set owner reference to backup CR"
    )


class AWXBackupStatus(BaseModel):
    """
    AWXBackup Custom Resource Status.

    Represents the observed state of a backup operation.
    """

    conditions: list[dict[str, Any]] = Field(
        default_factory=list, description="Status conditions"
    )
    backup_claim: Optional[str] = Field(default=None, description="Backup PVC name")
    backup_directory: Optional[str] = Field(
        default=None, description="Directory containing backup"
    )
    deployment_name: Optional[str] = Field(
        default=None, description="Name of backed up deployment"
    )
    postgres_label: Optional[str] = Field(
        default=None, description="PostgreSQL pod label"
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
