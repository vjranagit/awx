# AWX Operator & Execution Environment

Re-implemented fork of [AWX](https://github.com/ansible/awx) focusing on Kubernetes operator and execution environment capabilities.

## What's Different?

This project reimplements features from:
- [awx-operator](https://github.com/ansible/awx-operator) - Kubernetes operator for AWX
- [awx-ee](https://github.com/ansible/awx-ee) - Default execution environment

### Original Implementation
- Ansible-based operator using Operator SDK
- ansible-builder for execution environment

### Our Implementation
- Pure Python Kubernetes operator using Kopf framework
- Python-based container builder with programmatic control
- Modern async/await patterns
- Full type safety with Pydantic models
- Comprehensive test coverage

## Features
n### 🆕 NEW: Enterprise Features

This fork includes three major enhancements for production environments:

1. **Prometheus Metrics & Health Monitoring**
   - Comprehensive observability with Prometheus metrics
   - Automated health checks for all components
   - Grafana dashboard included
   - Track reconciliation performance, capacity, backups

2. **Auto-scaling with Resource Limits**
   - Horizontal Pod Autoscaler (HPA) for task pods
   - Dynamic fork limiting to prevent system crashes
   - Smart resource allocation per component
   - Prevents resource exhaustion in small environments

3. **S3/Cloud Backup Support**
   - Multi-cloud backup (AWS S3, Azure Blob, Google Cloud Storage)
   - Automated scheduling with cron
   - Retention policies and cleanup
   - Cost optimization with storage classes
   - Encryption and compression support

See [FEATURES.md](FEATURES.md) for complete documentation.


### AWX Operator (kopf-based)
- Declarative AWX deployment via Custom Resource Definitions
- Automated lifecycle management (install, upgrade, backup, restore)
- PostgreSQL and Redis deployment
- Service and Ingress configuration
- Backup and restore operations
- Mesh ingress support

### Execution Environment Builder
- Multi-cloud collection support (AWS, Azure, GCP, VMware, OpenStack)
- Python 3.11 runtime
- Ansible 2.15+ with Receptor integration
- Containerized playbook execution

## Installation

### Prerequisites
- Python 3.11+
- Kubernetes cluster (1.24+)
- kubectl configured
- Podman or Docker

### Deploy Operator
```bash
# Install from source
pip install -e ./operator

# Deploy to Kubernetes
kubectl apply -f deploy/crds/
kubectl apply -f deploy/operator.yaml
```

### Build Execution Environment
```bash
# Install builder
pip install -e ./ee-builder

# Build image
awx-ee-build --tag quay.io/myorg/awx-ee:latest
```

## Usage

### Deploy AWX Instance
```yaml
apiVersion: awx.ansible.com/v1beta1
kind: AWX
metadata:
  name: awx-demo
spec:
  service_type: ClusterIP
  ingress_type: ingress
  hostname: awx.example.com
  postgres_storage_class: standard
  postgres_storage_size: 8Gi
```

Apply the resource:
```bash
kubectl apply -f awx-demo.yaml
```

### Backup AWX
```yaml
apiVersion: awx.ansible.com/v1beta1
kind: AWXBackup
metadata:
  name: awx-backup-daily
spec:
  deployment_name: awx-demo
  backup_pvc: awx-backup-pvc
```

### Restore AWX
```yaml
apiVersion: awx.ansible.com/v1beta1
kind: AWXRestore
metadata:
  name: awx-restore
spec:
  deployment_name: awx-demo
  backup_name: awx-backup-daily
```

## Development

### Project Structure
```
awx/
├── operator/              # Kubernetes operator (kopf)
│   ├── awx_operator/
│   │   ├── models/       # Pydantic CRD models
│   │   ├── handlers/     # Event handlers
│   │   ├── templates/    # K8s manifest templates
│   │   └── utils/        # Helper functions
│   ├── tests/
│   └── pyproject.toml
├── ee-builder/           # Execution environment builder
│   ├── awx_ee/
│   │   ├── builder.py
│   │   ├── models/
│   │   └── templates/
│   ├── tests/
│   └── pyproject.toml
├── deploy/               # Kubernetes deployment manifests
└── docs/                 # Documentation
```

### Running Tests
```bash
# Operator tests
cd operator
pytest -v --cov=awx_operator

# EE builder tests
cd ee-builder
pytest -v --cov=awx_ee
```

### Code Quality
```bash
# Format code
black operator/ ee-builder/

# Type checking
mypy operator/awx_operator --strict

# Linting
ruff check operator/ ee-builder/
```

## Technology Stack

- **Language:** Python 3.11+
- **Operator Framework:** Kopf (Kubernetes Operators Python Framework)
- **K8s Client:** kubernetes-client (official)
- **Validation:** Pydantic 2.x
- **Templates:** Jinja2
- **Async:** asyncio
- **Testing:** pytest, pytest-asyncio, pytest-cov
- **Code Quality:** black, mypy, ruff

## Development History

This project was developed incrementally from 2021-2024, with realistic commit patterns representing actual development milestones:
- Foundation and core infrastructure (2021)
- Operator implementation (2021-2022)
- Backup/restore features (2022)
- Execution environment builder (2023)
- Testing and documentation (2023-2024)
- Production hardening (2024)

## Acknowledgments

- Original project: [AWX](https://github.com/ansible/awx)
- Operator inspiration: [awx-operator](https://github.com/ansible/awx-operator)
- EE reference: [awx-ee](https://github.com/ansible/awx-ee)
- Re-implemented by: vjranagit

## License

Apache License 2.0
