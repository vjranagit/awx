"""Health monitoring and checks for AWX operator."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, field

from awx_operator.utils.k8s_client import K8sClient

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health status for an AWX deployment component."""
    
    component: str
    healthy: bool
    message: str
    last_check: datetime = field(default_factory=datetime.utcnow)
    details: dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """
    Performs health checks on AWX deployment components.
    
    Monitors PostgreSQL, Redis, AWX web/task pods, and overall deployment health.
    """
    
    def __init__(self, k8s_client: K8sClient, deployment_name: str):
        """
        Initialize health checker.
        
        Args:
            k8s_client: Kubernetes client for API operations
            deployment_name: Name of AWX deployment to monitor
        """
        self.k8s = k8s_client
        self.deployment_name = deployment_name
        
    async def check_postgres_health(self) -> HealthStatus:
        """Check PostgreSQL database health."""
        try:
            # Check StatefulSet status
            sts_name = f"{self.deployment_name}-postgres"
            sts = await self.k8s.get_statefulset(sts_name)
            
            if not sts:
                return HealthStatus(
                    component="postgres",
                    healthy=False,
                    message="PostgreSQL StatefulSet not found"
                )
            
            ready_replicas = sts.status.ready_replicas or 0
            desired_replicas = sts.spec.replicas or 0
            
            if ready_replicas < desired_replicas:
                return HealthStatus(
                    component="postgres",
                    healthy=False,
                    message=f"PostgreSQL not ready: {ready_replicas}/{desired_replicas} replicas",
                    details={
                        "ready_replicas": ready_replicas,
                        "desired_replicas": desired_replicas
                    }
                )
            
            # Check pod status
            pods = await self.k8s.list_pods(label_selector=f"app={sts_name}")
            if not pods:
                return HealthStatus(
                    component="postgres",
                    healthy=False,
                    message="No PostgreSQL pods found"
                )
            
            for pod in pods:
                if pod.status.phase != "Running":
                    return HealthStatus(
                        component="postgres",
                        healthy=False,
                        message=f"PostgreSQL pod {pod.metadata.name} not running: {pod.status.phase}"
                    )
            
            return HealthStatus(
                component="postgres",
                healthy=True,
                message="PostgreSQL is healthy",
                details={"replicas": ready_replicas}
            )
            
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return HealthStatus(
                component="postgres",
                healthy=False,
                message=f"Health check error: {str(e)}"
            )
    
    async def check_redis_health(self) -> HealthStatus:
        """Check Redis cache health."""
        try:
            deployment_name = f"{self.deployment_name}-redis"
            deployment = await self.k8s.get_deployment(deployment_name)
            
            if not deployment:
                return HealthStatus(
                    component="redis",
                    healthy=False,
                    message="Redis Deployment not found"
                )
            
            ready_replicas = deployment.status.ready_replicas or 0
            desired_replicas = deployment.spec.replicas or 0
            
            if ready_replicas < desired_replicas:
                return HealthStatus(
                    component="redis",
                    healthy=False,
                    message=f"Redis not ready: {ready_replicas}/{desired_replicas} replicas",
                    details={
                        "ready_replicas": ready_replicas,
                        "desired_replicas": desired_replicas
                    }
                )
            
            return HealthStatus(
                component="redis",
                healthy=True,
                message="Redis is healthy",
                details={"replicas": ready_replicas}
            )
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return HealthStatus(
                component="redis",
                healthy=False,
                message=f"Health check error: {str(e)}"
            )
    
    async def check_web_health(self) -> HealthStatus:
        """Check AWX web pods health."""
        try:
            deployment_name = f"{self.deployment_name}-web"
            deployment = await self.k8s.get_deployment(deployment_name)
            
            if not deployment:
                return HealthStatus(
                    component="web",
                    healthy=False,
                    message="AWX web Deployment not found"
                )
            
            ready_replicas = deployment.status.ready_replicas or 0
            desired_replicas = deployment.spec.replicas or 0
            
            if ready_replicas < desired_replicas:
                return HealthStatus(
                    component="web",
                    healthy=False,
                    message=f"AWX web not ready: {ready_replicas}/{desired_replicas} replicas",
                    details={
                        "ready_replicas": ready_replicas,
                        "desired_replicas": desired_replicas
                    }
                )
            
            return HealthStatus(
                component="web",
                healthy=True,
                message="AWX web is healthy",
                details={"replicas": ready_replicas}
            )
            
        except Exception as e:
            logger.error(f"Web health check failed: {e}")
            return HealthStatus(
                component="web",
                healthy=False,
                message=f"Health check error: {str(e)}"
            )
    
    async def check_task_health(self) -> HealthStatus:
        """Check AWX task pods health."""
        try:
            deployment_name = f"{self.deployment_name}-task"
            deployment = await self.k8s.get_deployment(deployment_name)
            
            if not deployment:
                return HealthStatus(
                    component="task",
                    healthy=False,
                    message="AWX task Deployment not found"
                )
            
            ready_replicas = deployment.status.ready_replicas or 0
            desired_replicas = deployment.spec.replicas or 0
            
            if ready_replicas < desired_replicas:
                return HealthStatus(
                    component="task",
                    healthy=False,
                    message=f"AWX task not ready: {ready_replicas}/{desired_replicas} replicas",
                    details={
                        "ready_replicas": ready_replicas,
                        "desired_replicas": desired_replicas
                    }
                )
            
            return HealthStatus(
                component="task",
                healthy=True,
                message="AWX task is healthy",
                details={"replicas": ready_replicas}
            )
            
        except Exception as e:
            logger.error(f"Task health check failed: {e}")
            return HealthStatus(
                component="task",
                healthy=False,
                message=f"Health check error: {str(e)}"
            )
    
    async def check_overall_health(self) -> tuple[bool, list[HealthStatus]]:
        """
        Perform comprehensive health check on all components.
        
        Returns:
            Tuple of (overall_healthy, list of component statuses)
        """
        checks = await asyncio.gather(
            self.check_postgres_health(),
            self.check_redis_health(),
            self.check_web_health(),
            self.check_task_health(),
            return_exceptions=True
        )
        
        statuses = []
        for check in checks:
            if isinstance(check, Exception):
                logger.error(f"Health check failed with exception: {check}")
                statuses.append(HealthStatus(
                    component="unknown",
                    healthy=False,
                    message=f"Check failed: {str(check)}"
                ))
            else:
                statuses.append(check)
        
        overall_healthy = all(status.healthy for status in statuses)
        
        return overall_healthy, statuses
