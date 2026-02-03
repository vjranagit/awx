"""Input validation utilities."""

import re
from typing import Pattern


# Kubernetes resource name pattern (RFC 1123 DNS label)
K8S_NAME_PATTERN: Pattern[str] = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")

# Storage size pattern (e.g., "8Gi", "100Mi", "1Ti")
STORAGE_SIZE_PATTERN: Pattern[str] = re.compile(r"^\d+(\.\d+)?(Ki|Mi|Gi|Ti|Pi|Ei)$")


def validate_resource_name(name: str) -> bool:
    """
    Validate Kubernetes resource name.

    Args:
        name: Resource name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name or len(name) > 253:
        return False
    return K8S_NAME_PATTERN.match(name) is not None


def validate_storage_size(size: str) -> bool:
    """
    Validate Kubernetes storage size specification.

    Args:
        size: Storage size string (e.g., "8Gi")

    Returns:
        True if valid, False otherwise
    """
    if not size:
        return False
    return STORAGE_SIZE_PATTERN.match(size) is not None


def validate_hostname(hostname: str) -> bool:
    """
    Validate hostname format.

    Args:
        hostname: Hostname to validate

    Returns:
        True if valid, False otherwise
    """
    if not hostname or len(hostname) > 253:
        return False

    # Hostname pattern: alphanumeric and hyphens, dots for subdomains
    hostname_pattern = re.compile(
        r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$",
        re.IGNORECASE,
    )
    return hostname_pattern.match(hostname) is not None
