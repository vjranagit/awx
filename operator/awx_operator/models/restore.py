"""AWXRestore Custom Resource Definition models."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class AWXRestoreSpec(BaseModel):
    """
    AWXRestore Custom Resource Specification.

    Defines parameters for restoring an AWX deployment from backup.
    """

    deployment_name: str = Field(description="Name of AWX deployment to restore")
    backup_name: str = Field(description="Name of AWXBackup to restore from")
    backup_pvc: Optional[str] = Field(
        default=None, description="PVC containing backup data"
    )
    backup_pvc_namespace: Optional[str] = Field(
        default=None, description="Namespace of backup PVC"
    )
    backup_dir: Optional[str] = Field(default=None, description="Backup directory path")
    postgres_image: Optional[str] = Field(
        default="postgres:13", description="PostgreSQL image for restore"
    )
    postgres_label_selector: Optional[str] = Field(
        default=None, description="Label selector for PostgreSQL pod"
    )
    restore_resource_requirements: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="Restore job resource requirements"
    )
    no_log: bool = Field(default=True, description="Hide sensitive information in logs")
    set_self_ownerref: bool = Field(
        default=False, description="Set owner reference to restore CR"
    )


class AWXRestoreStatus(BaseModel):
    """
    AWXRestore Custom Resource Status.

    Represents the observed state of a restore operation.
    """

    conditions: list[dict[str, Any]] = Field(
        default_factory=list, description="Status conditions"
    )
    restored_from_backup: Optional[str] = Field(
        default=None, description="Name of backup restored from"
    )
    restored_deployment: Optional[str] = Field(
        default=None, description="Name of restored deployment"
    )
    restore_time: Optional[str] = Field(
        default=None, description="Time when restore completed"
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
