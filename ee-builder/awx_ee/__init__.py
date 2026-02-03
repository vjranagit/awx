"""
AWX Execution Environment Builder

A Python-based builder for creating AWX execution environment container images.
This tool generates Dockerfiles from YAML specifications with all required
Ansible collections, Python packages, and system dependencies.
"""

__version__ = "1.0.0"
__author__ = "vjranagit"
__license__ = "Apache-2.0"

from awx_ee.builder import EEBuilder
from awx_ee.models.ee_spec import EESpec, CollectionSpec

__all__ = ["EEBuilder", "EESpec", "CollectionSpec"]
