# AWX Execution Environment Builder

Python-based builder for creating AWX execution environment container images.

## Features

- Declarative YAML specification
- Multi-stage Docker builds for minimal image size
- Support for multiple Ansible collections
- System and Python dependency management
- Receptor integration for mesh networking
- CLI tool for easy image builds

## Installation

```bash
pip install -e .
```

## Usage

### Using default AWX EE specification

```bash
awx-ee-build build --use-defaults --tag quay.io/myorg/awx-ee:latest
```

### Using custom specification

Create a specification file:

```bash
awx-ee-build init --output my-ee-spec.yml --use-defaults
```

Edit the file, then build:

```bash
awx-ee-build build --spec my-ee-spec.yml --tag quay.io/myorg/awx-ee:latest
```

### Validate specification

```bash
awx-ee-build validate --spec my-ee-spec.yml
```

### Build and push

```bash
awx-ee-build build --spec my-ee-spec.yml --tag quay.io/myorg/awx-ee:latest --push
```

## Specification Format

```yaml
base_image: "quay.io/centos/centos:stream9"
python_version: "3.11"
ansible_core_version: ">=2.15.0,<2.16"

collections:
  - name: awx.awx
  - name: amazon.aws
  - name: azure.azcollection
    version: ">=2.1.0"

system_packages:
  - git-core
  - git-lfs
  - sshpass
  - rsync

python_packages:
  - ansible-runner
  - paramiko
  - pexpect>=4.5

receptor_enabled: true
receptor_image: "quay.io/ansible/receptor:devel"
```

## Development

Run tests:

```bash
pytest -v --cov=awx_ee
```

Format code:

```bash
black awx_ee/
```

Type checking:

```bash
mypy awx_ee/ --strict
```
