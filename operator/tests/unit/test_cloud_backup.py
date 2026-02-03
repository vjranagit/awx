"""Tests for cloud backup functionality."""

import pytest
from awx_operator.utils.cloud_backup import (
    CloudBackupSpec,
    S3BackupConfig,
    AzureBlobConfig,
    GCSConfig,
    BackupStorageType,
    CloudBackupManager
)


def test_s3_config_validation():
    """Test S3 configuration validation."""
    # Valid config
    config = S3BackupConfig(
        bucket="my-awx-backups",
        region="us-west-2"
    )
    assert config.bucket == "my-awx-backups"
    assert config.region == "us-west-2"
    
    # Invalid bucket name (too short)
    with pytest.raises(Exception):
        S3BackupConfig(bucket="ab")


def test_cloud_backup_spec_defaults():
    """Test cloud backup spec with defaults."""
    spec = CloudBackupSpec()
    
    assert spec.storage_type == BackupStorageType.LOCAL
    assert spec.retention_days == 30
    assert spec.compress is True
    assert spec.s3_config is None


def test_cloud_backup_spec_s3():
    """Test cloud backup spec with S3 configuration."""
    s3_config = S3BackupConfig(
        bucket="awx-backups",
        region="eu-central-1",
        prefix="prod"
    )
    
    spec = CloudBackupSpec(
        storage_type=BackupStorageType.S3,
        s3_config=s3_config,
        retention_days=60,
        max_backups=10
    )
    
    assert spec.storage_type == BackupStorageType.S3
    assert spec.s3_config.bucket == "awx-backups"
    assert spec.s3_config.region == "eu-central-1"
    assert spec.retention_days == 60
    assert spec.max_backups == 10


def test_cloud_backup_spec_azure():
    """Test cloud backup spec with Azure configuration."""
    azure_config = AzureBlobConfig(
        storage_account="awxstorage",
        container="backups",
        prefix="production"
    )
    
    spec = CloudBackupSpec(
        storage_type=BackupStorageType.AZURE_BLOB,
        azure_config=azure_config
    )
    
    assert spec.storage_type == BackupStorageType.AZURE_BLOB
    assert spec.azure_config.storage_account == "awxstorage"
    assert spec.azure_config.container == "backups"


def test_cloud_backup_spec_gcs():
    """Test cloud backup spec with GCS configuration."""
    gcs_config = GCSConfig(
        bucket="awx-backups-gcs",
        project_id="my-project",
        prefix="prod"
    )
    
    spec = CloudBackupSpec(
        storage_type=BackupStorageType.GCS,
        gcs_config=gcs_config
    )
    
    assert spec.storage_type == BackupStorageType.GCS
    assert spec.gcs_config.bucket == "awx-backups-gcs"
    assert spec.gcs_config.project_id == "my-project"


def test_backup_script_generation_s3():
    """Test backup script generation for S3."""
    s3_config = S3BackupConfig(
        bucket="test-bucket",
        region="us-east-1",
        prefix="backups"
    )
    
    spec = CloudBackupSpec(
        storage_type=BackupStorageType.S3,
        s3_config=s3_config,
        compress=True
    )
    
    manager = CloudBackupManager(spec, "test-awx", "default")
    script = manager._generate_backup_script()
    
    assert "pg_dump" in script
    assert "tar czf" in script
    assert "aws s3 cp" in script
    assert "s3://test-bucket/backups/" in script


def test_backup_script_generation_no_compression():
    """Test backup script generation without compression."""
    s3_config = S3BackupConfig(bucket="test-bucket")
    
    spec = CloudBackupSpec(
        storage_type=BackupStorageType.S3,
        s3_config=s3_config,
        compress=False
    )
    
    manager = CloudBackupManager(spec, "test-awx", "default")
    script = manager._generate_backup_script()
    
    assert "pg_dump" in script
    assert "tar czf" not in script
    assert "aws s3 cp" in script


def test_backup_job_manifest_creation():
    """Test Kubernetes backup job manifest creation."""
    s3_config = S3BackupConfig(
        bucket="test-bucket",
        access_key_secret="aws-credentials"
    )
    
    spec = CloudBackupSpec(
        storage_type=BackupStorageType.S3,
        s3_config=s3_config
    )
    
    manager = CloudBackupManager(spec, "test-awx", "default")
    job_manifest = manager.create_backup_job("test-backup-001")
    
    assert job_manifest["kind"] == "Job"
    assert "test-awx-backup-test-backup-001" in job_manifest["metadata"]["name"]
    assert job_manifest["metadata"]["namespace"] == "default"
    assert job_manifest["spec"]["template"]["spec"]["restartPolicy"] == "OnFailure"
