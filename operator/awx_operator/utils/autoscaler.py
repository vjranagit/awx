"""Auto-scaling and resource limit management for AWX operator."""

import logging
from typing import Optional
from pydantic import BaseModel, Field

from awx_operator.utils.k8s_client import K8sClient

logger = logging.getLogger(__name__)


class AutoScalingSpec(BaseModel):
    """
    Auto-scaling configuration for AWX task pods.
    
    Prevents resource exhaustion by dynamically adjusting fork limits
    and task pod replicas based on system capacity.
    """
    
    enabled: bool = Field(default=False, description="Enable auto-scaling")
    min_task_replicas: int = Field(default=1, ge=1, description="Minimum task replicas")
    max_task_replicas: int = Field(default=10, ge=1, description="Maximum task replicas")
    target_cpu_utilization: int = Field(default=70, ge=1, le=100, description="Target CPU utilization %")
    target_memory_utilization: int = Field(default=80, ge=1, le=100, description="Target memory utilization %")
    
    # Fork limits to prevent system crashes
    max_forks_per_task: int = Field(default=50, ge=1, description="Maximum forks per task pod")
    max_total_forks: Optional[int] = Field(default=None, description="Global fork limit across all tasks")
    
    # Capacity-based scaling
    scale_up_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Scale up when capacity > threshold")
    scale_down_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Scale down when capacity < threshold")
    cooldown_period_seconds: int = Field(default=300, ge=0, description="Cooldown between scaling operations")


class ResourceLimits(BaseModel):
    """Resource limits for AWX components."""
    
    task_cpu_request: str = Field(default="500m", description="Task CPU request")
    task_cpu_limit: str = Field(default="2000m", description="Task CPU limit")
    task_memory_request: str = Field(default="1Gi", description="Task memory request")
    task_memory_limit: str = Field(default="4Gi", description="Task memory limit")
    
    web_cpu_request: str = Field(default="250m", description="Web CPU request")
    web_cpu_limit: str = Field(default="1000m", description="Web CPU limit")
    web_memory_request: str = Field(default="512Mi", description="Web memory request")
    web_memory_limit: str = Field(default="2Gi", description="Web memory limit")
    
    postgres_cpu_request: str = Field(default="500m", description="PostgreSQL CPU request")
    postgres_cpu_limit: str = Field(default="2000m", description="PostgreSQL CPU limit")
    postgres_memory_request: str = Field(default="1Gi", description="PostgreSQL memory request")
    postgres_memory_limit: str = Field(default="4Gi", description="PostgreSQL memory limit")
    
    redis_cpu_request: str = Field(default="100m", description="Redis CPU request")
    redis_cpu_limit: str = Field(default="500m", description="Redis CPU limit")
    redis_memory_request: str = Field(default="256Mi", description="Redis memory request")
    redis_memory_limit: str = Field(default="1Gi", description="Redis memory limit")


class AutoScaler:
    """
    Manages auto-scaling and resource limits for AWX deployments.
    
    Dynamically adjusts task pod replicas and enforces fork limits
    to prevent system overload in resource-constrained environments.
    """
    
    def __init__(
        self,
        k8s_client: K8sClient,
        deployment_name: str,
        autoscaling_spec: AutoScalingSpec,
        resource_limits: ResourceLimits
    ):
        """
        Initialize auto-scaler.
        
        Args:
            k8s_client: Kubernetes client
            deployment_name: AWX deployment name
            autoscaling_spec: Auto-scaling configuration
            resource_limits: Resource limit configuration
        """
        self.k8s = k8s_client
        self.deployment_name = deployment_name
        self.spec = autoscaling_spec
        self.limits = resource_limits
        
    async def create_hpa(self) -> None:
        """
        Create Horizontal Pod Autoscaler for AWX task pods.
        
        Automatically scales task pods based on CPU and memory utilization.
        """
        if not self.spec.enabled:
            logger.info("Auto-scaling disabled, skipping HPA creation")
            return
        
        hpa_name = f"{self.deployment_name}-task-hpa"
        target_deployment = f"{self.deployment_name}-task"
        
        hpa_manifest = {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {
                "name": hpa_name,
                "namespace": self.k8s.namespace,
                "labels": {
                    "app": self.deployment_name,
                    "component": "autoscaling"
                }
            },
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": target_deployment
                },
                "minReplicas": self.spec.min_task_replicas,
                "maxReplicas": self.spec.max_task_replicas,
                "metrics": [
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "cpu",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": self.spec.target_cpu_utilization
                            }
                        }
                    },
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "memory",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": self.spec.target_memory_utilization
                            }
                        }
                    }
                ],
                "behavior": {
                    "scaleUp": {
                        "stabilizationWindowSeconds": self.spec.cooldown_period_seconds,
                        "policies": [
                            {
                                "type": "Percent",
                                "value": 50,
                                "periodSeconds": 60
                            }
                        ]
                    },
                    "scaleDown": {
                        "stabilizationWindowSeconds": self.spec.cooldown_period_seconds,
                        "policies": [
                            {
                                "type": "Percent",
                                "value": 25,
                                "periodSeconds": 60
                            }
                        ]
                    }
                }
            }
        }
        
        logger.info(f"Creating HPA: {hpa_name}")
        await self.k8s.create_or_update_hpa(hpa_manifest)
        
    async def enforce_fork_limits(self, job_template: dict) -> dict:
        """
        Enforce fork limits on AWX job template.
        
        Prevents jobs from specifying excessive fork counts that
        could crash the system.
        
        Args:
            job_template: Job template configuration
            
        Returns:
            Modified job template with enforced limits
        """
        requested_forks = job_template.get("forks", 0)
        
        # Enforce per-task fork limit
        if requested_forks > self.spec.max_forks_per_task:
            logger.warning(
                f"Job requested {requested_forks} forks, "
                f"limiting to {self.spec.max_forks_per_task}"
            )
            job_template["forks"] = self.spec.max_forks_per_task
        
        # Check global fork limit if configured
        if self.spec.max_total_forks:
            # This would require querying current active jobs and their fork counts
            # For now, we enforce the per-task limit
            pass
        
        return job_template
    
    def get_resource_requirements(self, component: str) -> dict:
        """
        Get resource requirements for a component.
        
        Args:
            component: Component name (task, web, postgres, redis)
            
        Returns:
            Kubernetes resource requirements dict
        """
        if component == "task":
            return {
                "requests": {
                    "cpu": self.limits.task_cpu_request,
                    "memory": self.limits.task_memory_request
                },
                "limits": {
                    "cpu": self.limits.task_cpu_limit,
                    "memory": self.limits.task_memory_limit
                }
            }
        elif component == "web":
            return {
                "requests": {
                    "cpu": self.limits.web_cpu_request,
                    "memory": self.limits.web_memory_request
                },
                "limits": {
                    "cpu": self.limits.web_cpu_limit,
                    "memory": self.limits.web_memory_limit
                }
            }
        elif component == "postgres":
            return {
                "requests": {
                    "cpu": self.limits.postgres_cpu_request,
                    "memory": self.limits.postgres_memory_request
                },
                "limits": {
                    "cpu": self.limits.postgres_cpu_limit,
                    "memory": self.limits.postgres_memory_limit
                }
            }
        elif component == "redis":
            return {
                "requests": {
                    "cpu": self.limits.redis_cpu_request,
                    "memory": self.limits.redis_memory_request
                },
                "limits": {
                    "cpu": self.limits.redis_cpu_limit,
                    "memory": self.limits.redis_memory_limit
                }
            }
        else:
            return {}
    
    async def calculate_optimal_replicas(self) -> int:
        """
        Calculate optimal number of task replicas based on current load.
        
        Returns:
            Recommended number of task replicas
        """
        try:
            # Get current task deployment
            deployment_name = f"{self.deployment_name}-task"
            deployment = await self.k8s.get_deployment(deployment_name)
            
            if not deployment:
                return self.spec.min_task_replicas
            
            current_replicas = deployment.spec.replicas or 0
            
            # Get pod metrics (this would integrate with metrics-server)
            # For now, return current replicas as placeholder
            # In production, would query metrics-server API
            
            return max(self.spec.min_task_replicas, 
                      min(current_replicas, self.spec.max_task_replicas))
                      
        except Exception as e:
            logger.error(f"Failed to calculate optimal replicas: {e}")
            return self.spec.min_task_replicas
