"""Prometheus metrics and health monitoring for AWX operator."""

import logging
from typing import Optional
from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest
from prometheus_client.core import CollectorRegistry

logger = logging.getLogger(__name__)


class AWXMetrics:
    """
    Prometheus metrics collector for AWX operator.
    
    Tracks deployment health, reconciliation performance, and resource usage.
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize metrics with optional custom registry."""
        self.registry = registry or CollectorRegistry()
        
        # Deployment info
        self.deployment_info = Info(
            'awx_deployment',
            'AWX deployment information',
            ['name', 'namespace', 'version'],
            registry=self.registry
        )
        
        # Reconciliation metrics
        self.reconciliation_total = Counter(
            'awx_reconciliation_total',
            'Total number of reconciliation events',
            ['name', 'namespace', 'event_type'],
            registry=self.registry
        )
        
        self.reconciliation_errors = Counter(
            'awx_reconciliation_errors_total',
            'Total reconciliation errors',
            ['name', 'namespace', 'error_type'],
            registry=self.registry
        )
        
        self.reconciliation_duration = Histogram(
            'awx_reconciliation_duration_seconds',
            'Reconciliation duration in seconds',
            ['name', 'namespace', 'event_type'],
            registry=self.registry
        )
        
        # Resource status
        self.deployment_status = Gauge(
            'awx_deployment_status',
            'AWX deployment status (1=ready, 0=not ready)',
            ['name', 'namespace'],
            registry=self.registry
        )
        
        self.pod_status = Gauge(
            'awx_pod_status',
            'AWX pod status by type',
            ['name', 'namespace', 'pod_type', 'phase'],
            registry=self.registry
        )
        
        # Capacity metrics
        self.task_capacity = Gauge(
            'awx_task_capacity_total',
            'Total task execution capacity',
            ['name', 'namespace'],
            registry=self.registry
        )
        
        self.task_capacity_used = Gauge(
            'awx_task_capacity_used',
            'Used task execution capacity',
            ['name', 'namespace'],
            registry=self.registry
        )
        
        # Backup metrics
        self.backup_total = Counter(
            'awx_backup_total',
            'Total number of backup operations',
            ['name', 'namespace', 'status'],
            registry=self.registry
        )
        
        self.backup_size_bytes = Gauge(
            'awx_backup_size_bytes',
            'Backup size in bytes',
            ['name', 'namespace', 'backup_name'],
            registry=self.registry
        )
        
        self.backup_duration = Histogram(
            'awx_backup_duration_seconds',
            'Backup operation duration',
            ['name', 'namespace'],
            registry=self.registry
        )
        
    def record_reconciliation(
        self, 
        name: str, 
        namespace: str, 
        event_type: str,
        duration: float
    ) -> None:
        """Record a reconciliation event."""
        self.reconciliation_total.labels(
            name=name, 
            namespace=namespace, 
            event_type=event_type
        ).inc()
        
        self.reconciliation_duration.labels(
            name=name,
            namespace=namespace,
            event_type=event_type
        ).observe(duration)
        
    def record_error(
        self, 
        name: str, 
        namespace: str, 
        error_type: str
    ) -> None:
        """Record a reconciliation error."""
        self.reconciliation_errors.labels(
            name=name,
            namespace=namespace,
            error_type=error_type
        ).inc()
        
    def update_deployment_status(
        self, 
        name: str, 
        namespace: str, 
        is_ready: bool
    ) -> None:
        """Update deployment readiness status."""
        self.deployment_status.labels(
            name=name,
            namespace=namespace
        ).set(1 if is_ready else 0)
        
    def update_pod_status(
        self,
        name: str,
        namespace: str,
        pod_type: str,
        phase: str,
        count: int
    ) -> None:
        """Update pod status counts."""
        self.pod_status.labels(
            name=name,
            namespace=namespace,
            pod_type=pod_type,
            phase=phase
        ).set(count)
        
    def update_capacity(
        self,
        name: str,
        namespace: str,
        total: int,
        used: int
    ) -> None:
        """Update task capacity metrics."""
        self.task_capacity.labels(name=name, namespace=namespace).set(total)
        self.task_capacity_used.labels(name=name, namespace=namespace).set(used)
        
    def record_backup(
        self,
        name: str,
        namespace: str,
        status: str,
        duration: float,
        size_bytes: Optional[int] = None,
        backup_name: Optional[str] = None
    ) -> None:
        """Record backup operation."""
        self.backup_total.labels(
            name=name,
            namespace=namespace,
            status=status
        ).inc()
        
        self.backup_duration.labels(
            name=name,
            namespace=namespace
        ).observe(duration)
        
        if size_bytes and backup_name:
            self.backup_size_bytes.labels(
                name=name,
                namespace=namespace,
                backup_name=backup_name
            ).set(size_bytes)
            
    def export_metrics(self) -> bytes:
        """Export metrics in Prometheus format."""
        return generate_latest(self.registry)


# Global metrics instance
_metrics: Optional[AWXMetrics] = None


def get_metrics() -> AWXMetrics:
    """Get or create global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = AWXMetrics()
    return _metrics
