"""Kubernetes API client wrapper with async support."""

import logging
from typing import Any, Optional

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

logger = logging.getLogger(__name__)


class K8sClient:
    """
    Wrapper around Kubernetes Python client with helper methods.

    Provides simplified interface for common Kubernetes operations
    used by the AWX operator.
    """

    def __init__(self, namespace: str = "default"):
        """
        Initialize Kubernetes client.

        Args:
            namespace: Default namespace for operations
        """
        self.namespace = namespace
        self._core_v1: Optional[client.CoreV1Api] = None
        self._apps_v1: Optional[client.AppsV1Api] = None
        self._networking_v1: Optional[client.NetworkingV1Api] = None
        self._custom_objects: Optional[client.CustomObjectsApi] = None

        # Load kubeconfig
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        except config.ConfigException:
            config.load_kube_config()
            logger.info("Loaded kubeconfig from file")

    @property
    def core_v1(self) -> client.CoreV1Api:
        """Get CoreV1Api client."""
        if self._core_v1 is None:
            self._core_v1 = client.CoreV1Api()
        return self._core_v1

    @property
    def apps_v1(self) -> client.AppsV1Api:
        """Get AppsV1Api client."""
        if self._apps_v1 is None:
            self._apps_v1 = client.AppsV1Api()
        return self._apps_v1

    @property
    def networking_v1(self) -> client.NetworkingV1Api:
        """Get NetworkingV1Api client."""
        if self._networking_v1 is None:
            self._networking_v1 = client.NetworkingV1Api()
        return self._networking_v1

    @property
    def custom_objects(self) -> client.CustomObjectsApi:
        """Get CustomObjectsApi client."""
        if self._custom_objects is None:
            self._custom_objects = client.CustomObjectsApi()
        return self._custom_objects

    def create_secret(
        self, name: str, data: dict[str, str], labels: Optional[dict[str, str]] = None
    ) -> client.V1Secret:
        """
        Create a Kubernetes secret.

        Args:
            name: Secret name
            data: Secret data (will be base64 encoded)
            labels: Optional labels for the secret

        Returns:
            Created secret object

        Raises:
            ApiException: If secret creation fails
        """
        import base64

        encoded_data = {k: base64.b64encode(v.encode()).decode() for k, v in data.items()}

        secret = client.V1Secret(
            api_version="v1",
            kind="Secret",
            metadata=client.V1ObjectMeta(name=name, labels=labels or {}),
            data=encoded_data,
        )

        try:
            return self.core_v1.create_namespaced_secret(self.namespace, secret)
        except ApiException as e:
            logger.error(f"Failed to create secret {name}: {e}")
            raise

    def get_secret(self, name: str) -> Optional[client.V1Secret]:
        """
        Get a Kubernetes secret.

        Args:
            name: Secret name

        Returns:
            Secret object or None if not found
        """
        try:
            return self.core_v1.read_namespaced_secret(name, self.namespace)
        except ApiException as e:
            if e.status == 404:
                return None
            logger.error(f"Failed to get secret {name}: {e}")
            raise

    def create_configmap(
        self, name: str, data: dict[str, str], labels: Optional[dict[str, str]] = None
    ) -> client.V1ConfigMap:
        """
        Create a Kubernetes ConfigMap.

        Args:
            name: ConfigMap name
            data: ConfigMap data
            labels: Optional labels

        Returns:
            Created ConfigMap object

        Raises:
            ApiException: If creation fails
        """
        configmap = client.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=client.V1ObjectMeta(name=name, labels=labels or {}),
            data=data,
        )

        try:
            return self.core_v1.create_namespaced_config_map(self.namespace, configmap)
        except ApiException as e:
            logger.error(f"Failed to create configmap {name}: {e}")
            raise

    def create_service(
        self, name: str, selector: dict[str, str], ports: list[dict[str, Any]], **kwargs: Any
    ) -> client.V1Service:
        """
        Create a Kubernetes service.

        Args:
            name: Service name
            selector: Pod selector labels
            ports: List of port specifications
            **kwargs: Additional service spec fields

        Returns:
            Created service object

        Raises:
            ApiException: If creation fails
        """
        service_ports = [
            client.V1ServicePort(
                name=p.get("name", f"port-{p['port']}"),
                port=p["port"],
                target_port=p.get("target_port", p["port"]),
                protocol=p.get("protocol", "TCP"),
            )
            for p in ports
        ]

        service = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(
                name=name,
                labels=kwargs.get("labels", {}),
                annotations=kwargs.get("annotations", {}),
            ),
            spec=client.V1ServiceSpec(
                selector=selector,
                ports=service_ports,
                type=kwargs.get("type", "ClusterIP"),
            ),
        )

        try:
            return self.core_v1.create_namespaced_service(self.namespace, service)
        except ApiException as e:
            logger.error(f"Failed to create service {name}: {e}")
            raise

    def create_pvc(
        self,
        name: str,
        size: str,
        storage_class: Optional[str] = None,
        labels: Optional[dict[str, str]] = None,
    ) -> client.V1PersistentVolumeClaim:
        """
        Create a PersistentVolumeClaim.

        Args:
            name: PVC name
            size: Storage size (e.g., "8Gi")
            storage_class: Optional storage class name
            labels: Optional labels

        Returns:
            Created PVC object

        Raises:
            ApiException: If creation fails
        """
        pvc = client.V1PersistentVolumeClaim(
            api_version="v1",
            kind="PersistentVolumeClaim",
            metadata=client.V1ObjectMeta(name=name, labels=labels or {}),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(requests={"storage": size}),
                storage_class_name=storage_class,
            ),
        )

        try:
            return self.core_v1.create_namespaced_persistent_volume_claim(
                self.namespace, pvc
            )
        except ApiException as e:
            logger.error(f"Failed to create PVC {name}: {e}")
            raise

    def delete_resource(
        self, api_method: Any, name: str, **kwargs: Any
    ) -> Optional[client.V1Status]:
        """
        Delete a Kubernetes resource.

        Args:
            api_method: API method to call (e.g., delete_namespaced_deployment)
            name: Resource name
            **kwargs: Additional arguments for the API call

        Returns:
            Status object or None if not found
        """
        try:
            return api_method(name, self.namespace, **kwargs)
        except ApiException as e:
            if e.status == 404:
                return None
            logger.error(f"Failed to delete resource {name}: {e}")
            raise

    def resource_exists(self, api_method: Any, name: str) -> bool:
        """
        Check if a Kubernetes resource exists.

        Args:
            api_method: API method to call (e.g., read_namespaced_deployment)
            name: Resource name

