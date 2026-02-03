"""Tests for auto-scaling and resource limits."""

import pytest
from awx_operator.utils.autoscaler import (
    AutoScalingSpec,
    ResourceLimits,
    AutoScaler
)


def test_autoscaling_spec_defaults():
    """Test auto-scaling spec with default values."""
    spec = AutoScalingSpec()
    
    assert spec.enabled is False
    assert spec.min_task_replicas == 1
    assert spec.max_task_replicas == 10
    assert spec.target_cpu_utilization == 70
    assert spec.max_forks_per_task == 50


def test_autoscaling_spec_custom_values():
    """Test auto-scaling spec with custom values."""
    spec = AutoScalingSpec(
        enabled=True,
        min_task_replicas=2,
        max_task_replicas=20,
        max_forks_per_task=100,
        max_total_forks=500
    )
    
    assert spec.enabled is True
    assert spec.min_task_replicas == 2
    assert spec.max_task_replicas == 20
    assert spec.max_forks_per_task == 100
    assert spec.max_total_forks == 500


def test_autoscaling_spec_validation():
    """Test auto-scaling spec validation."""
    with pytest.raises(Exception):
        # Invalid min replicas (< 1)
        AutoScalingSpec(min_task_replicas=0)
    
    with pytest.raises(Exception):
        # Invalid CPU utilization (> 100)
        AutoScalingSpec(target_cpu_utilization=150)


def test_resource_limits_defaults():
    """Test resource limits with default values."""
    limits = ResourceLimits()
    
    assert limits.task_cpu_request == "500m"
    assert limits.task_memory_request == "1Gi"
    assert limits.web_cpu_request == "250m"
    assert limits.postgres_memory_limit == "4Gi"


def test_resource_limits_custom_values():
    """Test resource limits with custom values."""
    limits = ResourceLimits(
        task_cpu_request="1000m",
        task_cpu_limit="4000m",
        task_memory_request="2Gi",
        task_memory_limit="8Gi"
    )
    
    assert limits.task_cpu_request == "1000m"
    assert limits.task_cpu_limit == "4000m"
    assert limits.task_memory_request == "2Gi"
    assert limits.task_memory_limit == "8Gi"


def test_fork_limit_enforcement():
    """Test fork limit enforcement."""
    spec = AutoScalingSpec(
        enabled=True,
        max_forks_per_task=50
    )
    
    # Mock K8s client
    class MockK8sClient:
        def __init__(self, namespace="default"):
            self.namespace = namespace
    
    k8s = MockK8sClient()
    limits = ResourceLimits()
    autoscaler = AutoScaler(k8s, "test-awx", spec, limits)
    
    # Test fork limit enforcement
    job_template = {"forks": 100}
    limited_template = autoscaler.enforce_fork_limits(job_template)
    
    assert limited_template["forks"] == 50


def test_get_resource_requirements():
    """Test getting resource requirements for components."""
    spec = AutoScalingSpec()
    
    class MockK8sClient:
        def __init__(self, namespace="default"):
            self.namespace = namespace
    
    k8s = MockK8sClient()
    limits = ResourceLimits(
        task_cpu_request="1000m",
        task_memory_request="2Gi"
    )
    autoscaler = AutoScaler(k8s, "test-awx", spec, limits)
    
    # Get task requirements
    task_reqs = autoscaler.get_resource_requirements("task")
    assert task_reqs["requests"]["cpu"] == "1000m"
    assert task_reqs["requests"]["memory"] == "2Gi"
    
    # Get web requirements
    web_reqs = autoscaler.get_resource_requirements("web")
    assert "requests" in web_reqs
    assert "limits" in web_reqs
