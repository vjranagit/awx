# Contributing to AWX Operator

Thank you for your interest in contributing to the AWX Operator project!

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch
4. Make your changes
5. Run tests and linters
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.11+
- Poetry or pip
- Kubernetes cluster (minikube, kind, or k3s for local development)
- kubectl configured

### Install Dependencies

```bash
cd operator
poetry install
# or
pip install -e .
```

### Running Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests (requires K8s cluster)
pytest tests/integration -v

# With coverage
pytest --cov=awx_operator --cov-report=html
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code
black operator/ ee-builder/

# Type checking
mypy operator/awx_operator --strict

# Linting
ruff check operator/ ee-builder/

# Run all checks
make lint
```

## Code Standards

### Python Style

- Follow PEP 8
- Use Black formatter (line length: 100)
- Add type hints to all functions
- Write docstrings for all public APIs (Google style)

### Type Safety

- Use Pydantic models for data validation
- Add type hints to all function signatures
- Pass mypy strict mode checks
- Avoid `Any` type when possible

### Testing

- Write unit tests for all new features
- Aim for >90% code coverage
- Use pytest fixtures for test data
- Mock external dependencies (K8s API calls)

### Documentation

- Update README.md for user-facing changes
- Add docstrings to new functions/classes
- Include usage examples for new features
- Keep API documentation up to date

## Commit Messages

Follow the conventional commits format:

```
type(scope): brief description

Longer description explaining the change in detail.

- Bullet point 1
- Bullet point 2
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or fixes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Build/tooling changes

## Pull Request Process

1. Update tests for your changes
2. Run full test suite and ensure it passes
3. Update documentation if needed
4. Ensure code passes all linters
5. Write a clear PR description explaining your changes
6. Link related issues

## Testing on Kubernetes

### Local Testing

```bash
# Create test cluster
kind create cluster --name awx-test

# Deploy operator
kubectl apply -f deploy/crds/
kubectl apply -f deploy/operator/

# Deploy test AWX instance
kubectl apply -f deploy/samples/awx_demo.yaml

# Check operator logs
kubectl logs -f deployment/awx-operator -n awx-operator
```

### Integration Tests

Integration tests require a Kubernetes cluster. Set the `KUBECONFIG` environment variable:

```bash
export KUBECONFIG=~/.kube/config
pytest tests/integration -v
```

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create git tag
4. Build and push container image
5. Create GitHub release

## Code of Conduct

Be respectful and professional in all interactions. We follow the [Ansible Code of Conduct](https://docs.ansible.com/ansible/latest/community/code_of_conduct.html).

## Questions?

Open an issue or start a discussion on GitHub.

Thank you for contributing!
