"""
AWX Operator - Kubernetes operator for AWX

A modern Python-based Kubernetes operator for deploying and managing
AWX (Ansible Automation Platform) on Kubernetes clusters.

This operator uses Kopf (Kubernetes Operator Pythonic Framework) to watch
and reconcile AWX custom resources, providing automated lifecycle management
including installation, upgrades, backups, and restores.
"""

__version__ = "2.19.0"
__author__ = "vjranagit"
__license__ = "Apache-2.0"

from awx_operator.models.awx import AWXSpec, AWXStatus
from awx_operator.models.backup import AWXBackupSpec, AWXBackupStatus
from awx_operator.models.restore import AWXRestoreSpec, AWXRestoreStatus

__all__ = [
    "AWXSpec",
    "AWXStatus",
    "AWXBackupSpec",
    "AWXBackupStatus",
    "AWXRestoreSpec",
    "AWXRestoreStatus",
]
