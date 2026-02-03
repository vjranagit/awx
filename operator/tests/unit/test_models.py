"""Unit tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from awx_operator.models.awx import AWXSpec, AWXStatus
from awx_operator.models.backup import AWXBackupSpec, AWXBackupStatus
from awx_operator.models.restore import AWXRestoreSpec, AWXRestoreStatus


class TestAWXSpec:
    """Tests for AWXSpec model."""

    def test_default_values(self) -> None:
        """Test AWXSpec with default values."""
        spec = AWXSpec()
        assert spec.admin_user == "admin"
        assert spec.admin_email == "admin@localhost"
        assert spec.service_type == "ClusterIP"
        assert spec.ingress_type == "none"
        assert spec.web_replicas == 1
        assert spec.task_replicas == 1

    def test_custom_values(self) -> None:
        """Test AWXSpec with custom values."""
        spec = AWXSpec(
            admin_user="superadmin",
            admin_email="admin@example.com",
            service_type="LoadBalancer",
            ingress_type="ingress",
            hostname="awx.example.com",
            web_replicas=2,
            task_replicas=3,
        )
        assert spec.admin_user == "superadmin"
        assert spec.admin_email == "admin@example.com"
        assert spec.service_type == "LoadBalancer"
        assert spec.ingress_type == "ingress"
        assert spec.hostname == "awx.example.com"
        assert spec.web_replicas == 2
        assert spec.task_replicas == 3

    def test_invalid_service_type(self) -> None:
        """Test AWXSpec with invalid service type."""
        with pytest.raises(ValidationError) as exc_info:
            AWXSpec(service_type="Invalid")
        assert "service_type" in str(exc_info.value)

    def test_invalid_ingress_type(self) -> None:
        """Test AWXSpec with invalid ingress type."""
        with pytest.raises(ValidationError) as exc_info:
            AWXSpec(ingress_type="InvalidType")
        assert "ingress_type" in str(exc_info.value)

    def test_invalid_replicas(self) -> None:
        """Test AWXSpec with invalid replicas."""
        with pytest.raises(ValidationError):
            AWXSpec(web_replicas=0)  # Must be >= 1

        with pytest.raises(ValidationError):
            AWXSpec(task_replicas=-1)  # Must be >= 0


class TestAWXStatus:
    """Tests for AWXStatus model."""

    def test_default_status(self) -> None:
        """Test AWXStatus with defaults."""
        status = AWXStatus()
        assert status.conditions == []
        assert status.version is None
        assert status.url is None

    def test_add_condition(self) -> None:
        """Test adding conditions to status."""
        status = AWXStatus()
        status.add_condition(
            type_="Ready",
            status="True",
            reason="DeploymentComplete",
            message="AWX is ready",
        )

        assert len(status.conditions) == 1
        assert status.conditions[0]["type"] == "Ready"
        assert status.conditions[0]["status"] == "True"
        assert status.conditions[0]["reason"] == "DeploymentComplete"

    def test_update_condition(self) -> None:
        """Test updating existing condition."""
        status = AWXStatus()
        status.add_condition(
            type_="Ready", status="False", reason="Deploying", message="Deploying..."
        )
        status.add_condition(
            type_="Ready", status="True", reason="Complete", message="Ready"
        )

        # Should only have one condition of type "Ready"
        assert len(status.conditions) == 1
        assert status.conditions[0]["status"] == "True"
        assert status.conditions[0]["reason"] == "Complete"


class TestAWXBackupSpec:
    """Tests for AWXBackupSpec model."""

    def test_required_fields(self) -> None:
        """Test AWXBackupSpec with required fields."""
        spec = AWXBackupSpec(deployment_name="awx-demo")
        assert spec.deployment_name == "awx-demo"
        assert spec.clean_backup_on_delete is False
        assert spec.no_log is True

    def test_custom_storage(self) -> None:
        """Test AWXBackupSpec with custom storage."""
        spec = AWXBackupSpec(
            deployment_name="awx-demo",
            backup_pvc="awx-backup",
            backup_storage_class="fast-ssd",
        )
        assert spec.backup_pvc == "awx-backup"
        assert spec.backup_storage_class == "fast-ssd"


class TestAWXRestoreSpec:
    """Tests for AWXRestoreSpec model."""

    def test_required_fields(self) -> None:
        """Test AWXRestoreSpec with required fields."""
        spec = AWXRestoreSpec(deployment_name="awx-demo", backup_name="awx-backup-daily")
        assert spec.deployment_name == "awx-demo"
        assert spec.backup_name == "awx-backup-daily"
        assert spec.no_log is True

    def test_custom_backup_location(self) -> None:
        """Test AWXRestoreSpec with custom backup location."""
        spec = AWXRestoreSpec(
            deployment_name="awx-demo",
            backup_name="awx-backup-daily",
            backup_pvc="custom-backup-pvc",
            backup_dir="/backups/2024-01-15",
        )
        assert spec.backup_pvc == "custom-backup-pvc"
        assert spec.backup_dir == "/backups/2024-01-15"
