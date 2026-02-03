"""Kopf event handlers for AWX custom resources."""

from awx_operator.handlers.awx_handler import (
    create_awx,
    update_awx,
    delete_awx,
)

__all__ = [
    "create_awx",
    "update_awx",
    "delete_awx",
]
