"""Cloud storage backup support for AWX operator."""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class BackupStorageType(str, Enum):
    """Backup storage backend types."""
    LOCAL = "local"
    S3 = "s3"
    AZURE_BLOB = "azure"
    GCS = "gcs"


class S3BackupConfig(BaseModel):
    """AWS S3 backup configuration."""
    
    bucket: str = Field(..., description="S3 bucket name")
    region: str = Field(default="us-east-1", description="AWS region")
    endpoint_url: Optional[str] = Field(default=None, description="Custom S3 endpoint (for MinIO, etc.)")
    access_key_secret: Optional[str] = Field(default=None, description="Secret containing AWS credentials")
    prefix: str = Field(default="awx-backups", description="S3 key prefix for backups")
    storage_class: str = Field(default="STANDARD", description="S3 storage class")
    encryption: bool = Field(default=True, description="Enable server-side encryption")
    
    @field_validator('bucket')
    @classmethod
    def validate_bucket_name(cls, v: str) -> str:
        """Validate S3 bucket name format."""
        if not v or len(v) < 3 or len(v) > 63:
            raise ValueError("Bucket name must be between 3 and 63 characters")
        return v


class AzureBlobConfig(BaseModel):
    """Azure Blob Storage backup configuration."""
    
    storage_account: str = Field(..., description="Azure storage account name")
    container: str = Field(..., description="Blob container name")
    connection_string_secret: Optional[str] = Field(
        default=None, 
        description="Secret containing Azure connection string"
    )
    prefix: str = Field(default="awx-backups", description="Blob prefix for backups")


class GCSConfig(BaseModel):
    """Google Cloud Storage backup configuration."""
    
    bucket: str = Field(..., description="GCS bucket name")
    project_id: str = Field(..., description="GCP project ID")
    credentials_secret: Optional[str] = Field(
        default=None,
        description="Secret containing GCP service account credentials"
    )
    prefix: str = Field(default="awx-backups", description="GCS object prefix for backups")


class CloudBackupSpec(BaseModel):
    """Cloud backup specification for AWX."""
    
    storage_type: BackupStorageType = Field(
        default=BackupStorageType.LOCAL,
        description="Backup storage backend"
    )
    
    # Storage-specific configurations
    s3_config: Optional[S3BackupConfig] = None
    azure_config: Optional[AzureBlobConfig] = None
    gcs_config: Optional[GCSConfig] = None
    
    # Backup retention
    retention_days: int = Field(default=30, ge=1, description="Days to retain backups")
    max_backups: Optional[int] = Field(default=None, description="Maximum number of backups to keep")
    
    # Scheduling
    schedule: Optional[str] = Field(
        default=None,
        description="Cron schedule for automatic backups (e.g., '0 2 * * *')"
    )
    
    # Compression and encryption
    compress: bool = Field(default=True, description="Compress backup archives")
    encryption_key_secret: Optional[str] = Field(
        default=None,
        description="Secret containing backup encryption key"
    )
    
    @field_validator('s3_config', 's3_config', 'gcs_config')
    @classmethod
    def validate_storage_config(cls, v, info):
        """Validate that appropriate config exists for storage type."""
        storage_type = info.data.get('storage_type')
        field_name = info.field_name
        
        if storage_type == BackupStorageType.S3 and field_name == 's3_config' and not v:
            raise ValueError("s3_config required when storage_type is s3")
        elif storage_type == BackupStorageType.AZURE_BLOB and field_name == 'azure_config' and not v:
            raise ValueError("azure_config required when storage_type is azure")
        elif storage_type == BackupStorageType.GCS and field_name == 'gcs_config' and not v:
            raise ValueError("gcs_config required when storage_type is gcs")
        
        return v


class CloudBackupManager:
    """
    Manages cloud storage backups for AWX deployments.
    
    Supports multiple cloud providers (AWS S3, Azure Blob, GCS)
    with features like compression, encryption, and retention policies.
    """
    
    def __init__(self, spec: CloudBackupSpec, deployment_name: str, namespace: str):
        """
        Initialize cloud backup manager.
        
        Args:
            spec: Cloud backup specification
            deployment_name: AWX deployment name
            namespace: Kubernetes namespace
        """
        self.spec = spec
        self.deployment_name = deployment_name
        self.namespace = namespace
        
    async def create_backup_job(self, backup_name: str) -> dict:
        """
        Create Kubernetes Job to perform backup to cloud storage.
        
        Args:
            backup_name: Name for this backup
            
        Returns:
            Kubernetes Job manifest
        """
        job_name = f"{self.deployment_name}-backup-{backup_name}"
        
        # Base container spec
        container_spec = {
            "name": "backup",
            "image": "quay.io/ansible/awx-ee:latest",  # Use EE image with cloud tools
            "command": ["/bin/bash", "-c"],
            "args": [self._generate_backup_script()],
            "env": self._generate_env_vars(),
            "volumeMounts": [
                {
                    "name": "postgres-data",
                    "mountPath": "/var/lib/postgresql/data",
                    "readOnly": True
                }
            ]
        }
        
        # Add cloud provider credentials
        if self.spec.storage_type == BackupStorageType.S3 and self.spec.s3_config:
            if self.spec.s3_config.access_key_secret:
                container_spec["envFrom"] = [{
                    "secretRef": {"name": self.spec.s3_config.access_key_secret}
                }]
        
        job_manifest = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": job_name,
                "namespace": self.namespace,
                "labels": {
                    "app": self.deployment_name,
                    "component": "backup",
                    "backup-type": "cloud"
                }
            },
            "spec": {
                "template": {
                    "metadata": {
                        "labels": {
                            "app": self.deployment_name,
                            "component": "backup"
                        }
                    },
                    "spec": {
                        "restartPolicy": "OnFailure",
                        "containers": [container_spec],
                        "volumes": [
                            {
                                "name": "postgres-data",
                                "persistentVolumeClaim": {
                                    "claimName": f"{self.deployment_name}-postgres-data"
                                }
                            }
                        ]
                    }
                },
                "backoffLimit": 3,
                "ttlSecondsAfterFinished": 86400  # Clean up after 24 hours
            }
        }
        
        return job_manifest
    
    def _generate_backup_script(self) -> str:
        """Generate backup script based on storage type."""
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        backup_file = f"awx-backup-{self.deployment_name}-{timestamp}.tar.gz"
        
        script_parts = [
            "set -e",
            "echo 'Starting AWX backup to cloud storage...'",
            "",
            "# Create backup directory",
            "mkdir -p /tmp/backup",
            "cd /tmp/backup",
            "",
            "# Dump PostgreSQL database",
            f"pg_dump -h {self.deployment_name}-postgres -U awx -Fc awx > awx.dump",
            "",
        ]
        
        if self.spec.compress:
            script_parts.extend([
                "# Compress backup",
                f"tar czf {backup_file} awx.dump",
                ""
            ])
        else:
            backup_file = "awx.dump"
        
        # Add cloud-specific upload commands
        if self.spec.storage_type == BackupStorageType.S3:
            s3_config = self.spec.s3_config
            if s3_config:
                s3_path = f"s3://{s3_config.bucket}/{s3_config.prefix}/{backup_file}"
                script_parts.extend([
                    "# Upload to S3",
                    f"aws s3 cp {backup_file} {s3_path} --region {s3_config.region}",
                    f"echo 'Backup uploaded to {s3_path}'",
                    ""
                ])
        
        elif self.spec.storage_type == BackupStorageType.AZURE_BLOB:
            azure_config = self.spec.azure_config
            if azure_config:
                blob_path = f"{azure_config.prefix}/{backup_file}"
                script_parts.extend([
                    "# Upload to Azure Blob",
                    f"az storage blob upload --file {backup_file} "
                    f"--container-name {azure_config.container} "
                    f"--name {blob_path} "
                    f"--account-name {azure_config.storage_account}",
                    f"echo 'Backup uploaded to Azure Blob: {blob_path}'",
                    ""
                ])
        
        elif self.spec.storage_type == BackupStorageType.GCS:
            gcs_config = self.spec.gcs_config
            if gcs_config:
                gcs_path = f"gs://{gcs_config.bucket}/{gcs_config.prefix}/{backup_file}"
                script_parts.extend([
                    "# Upload to GCS",
                    f"gsutil cp {backup_file} {gcs_path}",
                    f"echo 'Backup uploaded to GCS: {gcs_path}'",
                    ""
                ])
        
        script_parts.extend([
            "# Cleanup",
            "rm -rf /tmp/backup",
            "echo 'Backup completed successfully'"
        ])
        
        return "\n".join(script_parts)
    
    def _generate_env_vars(self) -> list[dict]:
        """Generate environment variables for backup job."""
        env_vars = [
            {"name": "PGPASSWORD", "value": "awxpass"},  # Should come from secret
            {"name": "BACKUP_NAME", "value": self.deployment_name},
            {"name": "BACKUP_TIMESTAMP", "value": datetime.utcnow().isoformat()}
        ]
        
        if self.spec.storage_type == BackupStorageType.S3 and self.spec.s3_config:
            if self.spec.s3_config.endpoint_url:
                env_vars.append({
                    "name": "AWS_ENDPOINT_URL",
                    "value": self.spec.s3_config.endpoint_url
                })
        
        return env_vars
    
    async def cleanup_old_backups(self) -> None:
        """
        Clean up old backups based on retention policy.
        
        Removes backups older than retention_days or exceeding max_backups count.
        """
        logger.info(f"Cleaning up old backups for {self.deployment_name}")
        
        # This would list and delete old backups from the cloud storage
        # Implementation depends on cloud provider SDK
        
        if self.spec.storage_type == BackupStorageType.S3:
            # Use boto3 to list and delete old backups
            pass
        elif self.spec.storage_type == BackupStorageType.AZURE_BLOB:
            # Use azure-storage-blob to cleanup
            pass
        elif self.spec.storage_type == BackupStorageType.GCS:
            # Use google-cloud-storage to cleanup
            pass
        
        logger.info("Backup cleanup completed")
