# New Features

This fork adds three major enterprise-grade features to AWX operator:

## 1. Prometheus Metrics & Health Monitoring

### Overview
Production-ready observability with Prometheus metrics and comprehensive health checks for all AWX components.

### Features
- **Prometheus Metrics Exporter**: Exposes metrics for monitoring dashboards and alerting
- **Reconciliation Tracking**: Monitor operator performance and reconciliation cycles
- **Resource Status**: Track pod health, deployment readiness, and capacity usage
- **Backup Monitoring**: Track backup operations, size, and success rates
- **Error Tracking**: Detailed error categorization for troubleshooting

### Metrics Exposed
```
# Deployment status
awx_deployment_status{name, namespace} = 1 (ready) | 0 (not ready)

# Reconciliation performance
awx_reconciliation_total{name, namespace, event_type}
awx_reconciliation_errors_total{name, namespace, error_type}
awx_reconciliation_duration_seconds{name, namespace, event_type}

# Pod status
awx_pod_status{name, namespace, pod_type, phase}

# Capacity metrics
awx_task_capacity_total{name, namespace}
awx_task_capacity_used{name, namespace}

# Backup operations
awx_backup_total{name, namespace, status}
awx_backup_size_bytes{name, namespace, backup_name}
awx_backup_duration_seconds{name, namespace}
```

### Health Checks
Automated health monitoring for:
- PostgreSQL database connectivity and replica status
- Redis cache availability
- AWX web pod readiness
- AWX task pod capacity
- Overall deployment health

### Usage Example
```python
from awx_operator.utils.metrics import get_metrics
from awx_operator.utils.health import HealthChecker

# Record metrics
metrics = get_metrics()
metrics.record_reconciliation("awx-demo", "default", "create", duration=1.5)
metrics.update_deployment_status("awx-demo", "default", is_ready=True)

# Perform health checks
health_checker = HealthChecker(k8s_client, "awx-demo")
is_healthy, statuses = await health_checker.check_overall_health()
```

### Grafana Dashboard
Import the provided Grafana dashboard (`deploy/monitoring/grafana-dashboard.json`) to visualize:
- Deployment health over time
- Reconciliation performance
- Resource utilization
- Backup success rates

---

## 2. Auto-scaling with Resource Limits

### Overview
Prevents resource exhaustion by dynamically managing fork limits and auto-scaling task pods based on workload.

### Problem Solved
On small systems, AWX jobs with excessive fork counts can consume all available resources and crash the system. This feature implements intelligent capacity management and horizontal pod autoscaling.

### Features

#### Dynamic Fork Limiting
- **Per-Task Fork Limit**: Prevents individual jobs from exceeding safe fork counts
- **Global Fork Budget**: Optional cluster-wide fork limit across all tasks
- **Automatic Enforcement**: Transparently limits forks before job execution

#### Horizontal Pod Autoscaling (HPA)
- **CPU-Based Scaling**: Scale task pods based on CPU utilization
- **Memory-Based Scaling**: Scale based on memory pressure
- **Smart Cooldown**: Prevents rapid scaling oscillation
- **Configurable Bounds**: Set min/max replica counts

#### Resource Guarantees
- **Request/Limit Management**: Proper Kubernetes resource specifications
- **Per-Component Tuning**: Different limits for web, task, PostgreSQL, Redis
- **QoS Classes**: Ensures critical components get resources first

### Configuration Example
```yaml
apiVersion: awx.ansible.com/v1beta1
kind: AWX
metadata:
  name: awx-demo
spec:
  # Enable auto-scaling
  autoscaling:
    enabled: true
    min_task_replicas: 2
    max_task_replicas: 10
    target_cpu_utilization: 70
    target_memory_utilization: 80
    
    # Fork limits (prevents system crashes)
    max_forks_per_task: 50
    max_total_forks: 200
    
    # Scaling behavior
    scale_up_threshold: 0.8
    scale_down_threshold: 0.3
    cooldown_period_seconds: 300
  
  # Resource limits
  resource_limits:
    task_cpu_request: "1000m"
    task_cpu_limit: "2000m"
    task_memory_request: "2Gi"
    task_memory_limit: "4Gi"
    
    web_cpu_request: "500m"
    web_cpu_limit: "1000m"
    web_memory_request: "1Gi"
    web_memory_limit: "2Gi"
```

### How It Works

1. **Job Submission**: When a job is submitted with `forks: 100`
2. **Fork Enforcement**: Operator checks `max_forks_per_task: 50` and limits it
3. **HPA Monitoring**: Kubernetes HPA monitors task pod CPU/memory
4. **Auto-scaling**: If CPU > 70%, HPA scales up task pods (within bounds)
5. **Cooldown**: After scaling, waits 5 minutes before next action

### Benefits
- **Prevents Crashes**: No more OOM kills from excessive forks
- **Cost Efficiency**: Scales down during low utilization
- **Performance**: Scales up during peak loads
- **Resource Fairness**: Prevents one job from starving others

---

## 3. S3/Cloud Backup Support

### Overview
Enterprise-grade backup solution with support for AWS S3, Azure Blob Storage, and Google Cloud Storage.

### Features

#### Multi-Cloud Support
- **AWS S3**: Native S3 and S3-compatible storage (MinIO, Ceph)
- **Azure Blob Storage**: Microsoft Azure cloud storage
- **Google Cloud Storage**: GCP storage buckets
- **Local Storage**: Traditional PVC-based backups (fallback)

#### Backup Management
- **Automated Scheduling**: Cron-based automatic backups
- **Retention Policies**: Time-based and count-based retention
- **Compression**: Gzip compression to reduce storage costs
- **Encryption**: Client-side encryption for sensitive data
- **Point-in-Time Recovery**: Restore from any backup snapshot

#### Storage Features
- **S3 Storage Classes**: Use GLACIER or INTELLIGENT_TIERING for cost savings
- **Server-Side Encryption**: Automatic encryption at rest
- **Multi-Region**: Cross-region replication support
- **Versioning**: Keep multiple versions of same backup

### Configuration Examples

#### AWS S3 Backup
```yaml
apiVersion: awx.ansible.com/v1beta1
kind: AWXBackup
metadata:
  name: awx-daily-backup
spec:
  deployment_name: awx-demo
  
  cloud_backup:
    storage_type: s3
    
    s3_config:
      bucket: my-company-awx-backups
      region: us-east-1
      prefix: production
      storage_class: INTELLIGENT_TIERING
      encryption: true
      access_key_secret: aws-credentials
    
    # Retention policy
    retention_days: 90
    max_backups: 30
    
    # Schedule (daily at 2 AM)
    schedule: "0 2 * * *"
    
    # Compression and encryption
    compress: true
    encryption_key_secret: backup-encryption-key
```

#### Azure Blob Backup
```yaml
apiVersion: awx.ansible.com/v1beta1
kind: AWXBackup
metadata:
  name: awx-azure-backup
spec:
  deployment_name: awx-demo
  
  cloud_backup:
    storage_type: azure
    
    azure_config:
      storage_account: awxstorageaccount
      container: awx-backups
      prefix: prod
      connection_string_secret: azure-storage-connection
    
    retention_days: 60
    schedule: "0 3 * * *"
```

#### Google Cloud Storage Backup
```yaml
apiVersion: awx.ansible.com/v1beta1
kind: AWXBackup
metadata:
  name: awx-gcs-backup
spec:
  deployment_name: awx-demo
  
  cloud_backup:
    storage_type: gcs
    
    gcs_config:
      bucket: awx-backups-gcs
      project_id: my-gcp-project
      prefix: production
      credentials_secret: gcp-service-account
    
    retention_days: 30
    compress: true
```

#### MinIO (S3-Compatible) Backup
```yaml
apiVersion: awx.ansible.com/v1beta1
kind: AWXBackup
metadata:
  name: awx-minio-backup
spec:
  deployment_name: awx-demo
  
  cloud_backup:
    storage_type: s3
    
    s3_config:
      bucket: awx-backups
      region: us-east-1
      endpoint_url: "https://minio.company.internal:9000"
      access_key_secret: minio-credentials
      prefix: backups
    
    retention_days: 14
    schedule: "0 */6 * * *"  # Every 6 hours
```

### Backup Process

1. **Kubernetes Job Creation**: Operator creates a backup Job pod
2. **Database Dump**: PostgreSQL database dumped with `pg_dump`
3. **Compression**: Archive compressed with gzip (optional)
4. **Encryption**: Archive encrypted with AES-256 (optional)
5. **Cloud Upload**: Archive uploaded to configured cloud storage
6. **Verification**: Upload verified and metrics recorded
7. **Cleanup**: Old backups removed per retention policy

### Restore Process

```yaml
apiVersion: awx.ansible.com/v1beta1
kind: AWXRestore
metadata:
  name: awx-restore-from-s3
spec:
  deployment_name: awx-demo
  
  # Restore from cloud backup
  cloud_restore:
    storage_type: s3
    s3_config:
      bucket: my-company-awx-backups
      region: us-east-1
      prefix: production
      access_key_secret: aws-credentials
    
    # Specific backup to restore
    backup_name: awx-backup-awx-demo-20240203-020000.tar.gz
```

### Cost Optimization

#### S3 Storage Classes
- **STANDARD**: Frequent access ($0.023/GB)
- **INTELLIGENT_TIERING**: Automatic optimization ($0.0025-0.023/GB)
- **GLACIER**: Long-term archival ($0.004/GB)
- **DEEP_ARCHIVE**: Cheapest, slow retrieval ($0.00099/GB)

#### Retention Strategy
```yaml
# Cost-effective retention strategy
retention_policy:
  # Daily backups for 7 days
  daily_backups: 7
  
  # Weekly backups for 4 weeks
  weekly_backups: 4
  
  # Monthly backups for 12 months
  monthly_backups: 12
  
  # Yearly backups for 7 years
  yearly_backups: 7
```

### Security

#### Encryption Options
1. **Server-Side Encryption (SSE)**: Cloud provider manages keys
2. **Client-Side Encryption**: Encrypt before upload (most secure)
3. **KMS Integration**: AWS KMS, Azure Key Vault, GCP KMS

#### Credentials Management
All cloud credentials stored in Kubernetes Secrets:

```bash
# AWS credentials
kubectl create secret generic aws-credentials \
  --from-literal=AWS_ACCESS_KEY_ID=AKIA... \
  --from-literal=AWS_SECRET_ACCESS_KEY=...

# Azure connection string
kubectl create secret generic azure-storage-connection \
  --from-literal=AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https..."

# GCP service account
kubectl create secret generic gcp-service-account \
  --from-file=credentials.json=./service-account-key.json
```

---

## Integration

All three features integrate seamlessly:

```yaml
apiVersion: awx.ansible.com/v1beta1
kind: AWX
metadata:
  name: production-awx
spec:
  # Core configuration
  image_version: "24.6.1"
  admin_user: admin
  
  # Feature 1: Metrics & Health
  monitoring:
    prometheus_enabled: true
    health_check_interval: 60
  
  # Feature 2: Auto-scaling
  autoscaling:
    enabled: true
    min_task_replicas: 3
    max_task_replicas: 20
    max_forks_per_task: 75
  
  # Feature 3: Cloud Backup
  backup:
    storage_type: s3
    s3_config:
      bucket: prod-awx-backups
      region: us-east-1
    schedule: "0 2 * * *"
    retention_days: 90
```

## Testing

Run comprehensive tests:

```bash
# Test auto-scaling
cd operator
pytest tests/unit/test_autoscaler.py -v

# Test cloud backup
pytest tests/unit/test_cloud_backup.py -v

# Test metrics (requires prometheus_client)
pytest tests/unit/test_metrics.py -v

# Integration tests
pytest tests/integration/ -v
```

## Monitoring Setup

### Deploy Prometheus
```bash
kubectl apply -f deploy/monitoring/prometheus.yaml
```

### Deploy Grafana
```bash
kubectl apply -f deploy/monitoring/grafana.yaml
kubectl apply -f deploy/monitoring/grafana-dashboard.json
```

### View Metrics
```bash
# Port-forward Grafana
kubectl port-forward svc/grafana 3000:3000 -n monitoring

# Open browser to http://localhost:3000
# Username: admin, Password: admin
```

## Production Recommendations

1. **Metrics Retention**: Configure Prometheus retention for 30+ days
2. **Backup Testing**: Regularly test restore procedures
3. **Resource Limits**: Start conservative, tune based on actual usage
4. **Multi-Region Backups**: Use cross-region replication for DR
5. **Alerting**: Set up alerts for failed backups, high error rates, capacity issues

## Future Enhancements

Potential additions for future releases:
- Backup encryption with HashiCorp Vault integration
- Advanced scheduling with SLA-based prioritization
- Multi-cluster federation support
- Integration with external monitoring (Datadog, New Relic)
- Predictive auto-scaling using ML models
