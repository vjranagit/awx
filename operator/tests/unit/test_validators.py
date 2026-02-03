"""Tests for validation utilities."""

import pytest

from awx_operator.utils.validators import (
    validate_resource_name,
    validate_storage_size,
    validate_hostname,
)


class TestResourceNameValidation:
    """Tests for Kubernetes resource name validation."""

    def test_valid_names(self) -> None:
        """Test valid resource names."""
        assert validate_resource_name("awx") is True
        assert validate_resource_name("awx-demo") is True
        assert validate_resource_name("awx-123") is True
        assert validate_resource_name("a") is True
        assert validate_resource_name("123-abc") is True

    def test_invalid_names(self) -> None:
        """Test invalid resource names."""
        assert validate_resource_name("") is False
        assert validate_resource_name("AWX") is False  # Uppercase not allowed
        assert validate_resource_name("-awx") is False  # Cannot start with dash
        assert validate_resource_name("awx-") is False  # Cannot end with dash
        assert validate_resource_name("awx_demo") is False  # Underscore not allowed
        assert validate_resource_name("a" * 254) is False  # Too long (>253)


class TestStorageSizeValidation:
    """Tests for storage size validation."""

    def test_valid_sizes(self) -> None:
        """Test valid storage sizes."""
        assert validate_storage_size("8Gi") is True
        assert validate_storage_size("100Mi") is True
        assert validate_storage_size("1Ti") is True
        assert validate_storage_size("500Ki") is True
        assert validate_storage_size("2.5Gi") is True
        assert validate_storage_size("10Pi") is True
        assert validate_storage_size("1Ei") is True

    def test_invalid_sizes(self) -> None:
        """Test invalid storage sizes."""
        assert validate_storage_size("") is False
        assert validate_storage_size("8GB") is False  # Wrong unit
        assert validate_storage_size("8G") is False  # Missing 'i'
        assert validate_storage_size("Gi") is False  # Missing number
        assert validate_storage_size("eight Gi") is False  # Not numeric


class TestHostnameValidation:
    """Tests for hostname validation."""

    def test_valid_hostnames(self) -> None:
        """Test valid hostnames."""
        assert validate_hostname("example.com") is True
        assert validate_hostname("awx.example.com") is True
        assert validate_hostname("my-awx.example.com") is True
        assert validate_hostname("sub.domain.example.com") is True
        assert validate_hostname("localhost") is True
        assert validate_hostname("a.b") is True

    def test_invalid_hostnames(self) -> None:
        """Test invalid hostnames."""
        assert validate_hostname("") is False
        assert validate_hostname("-example.com") is False  # Cannot start with dash
        assert validate_hostname("example-.com") is False  # Cannot end with dash
        assert validate_hostname("exam ple.com") is False  # No spaces
        assert validate_hostname("a" * 254) is False  # Too long (>253)
        assert validate_hostname("example..com") is False  # Double dot
