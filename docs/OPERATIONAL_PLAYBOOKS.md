# GoAI Sovereign Platform — Operational Playbooks

## Standardized Maintenance Procedures

> This document provides **step-by-step procedures** for all operational tasks. Every procedure is designed for auditability and compliance with banking and regulatory requirements.

---

## Playbook Index

| Playbook | Frequency | Time | Risk |
|----------|-----------|------|------|
| [Model Upgrade](#1-model-upgrade-guide) | As needed | 2-4 hours | Medium |
| [System Restart](#2-restart-procedure) | As needed | 15-30 min | Low |
| [Log Rotation](#3-log-rotation) | Daily | 5 min | Low |
| [Backup Process](#4-backup-process) | Daily | 30-60 min | Low |
| [Restore Test](#5-restore-test) | Monthly | 2-4 hours | Medium |
| [Index Rebuild](#6-index-rebuild) | As needed | 1-4 hours | Medium |
| [Container Versioning](#7-container-versioning) | As needed | 1 hour | Medium |
| [GPU Monitoring](#8-gpu-monitoring-thresholds) | Continuous | - | - |

---

## 1. Model Upgrade Guide

### 1.1 Pre-Upgrade Checklist

```yaml
pre_upgrade:
  approval:
    - [ ] Change request ticket created: CR-XXXX
    - [ ] Model evaluation complete (bias, security, performance)
    - [ ] Approval from: Model Governance Board
    - [ ] Maintenance window scheduled
    - [ ] Stakeholders notified (24h advance)
    
  technical:
    - [ ] New model weights downloaded and verified
    - [ ] GPU memory requirements confirmed
    - [ ] vLLM configuration prepared
    - [ ] Rollback plan documented
    - [ ] Monitoring alerts paused
```

### 1.2 Upgrade Procedure

```bash
#!/bin/bash
# Playbook: Model Upgrade
# Author: Platform Team
# Last Updated: 2025-01-15

set -e  # Exit on error

# Configuration
NEW_MODEL="meta-llama/Llama-3.2-70B-Instruct"
NEW_VERSION="v2.0"
CURRENT_VERSION="v1.0"
CANARY_PERCENTAGE=10
MONITORING_PERIOD=1800  # 30 minutes

echo "=========================================="
echo "MODEL UPGRADE PLAYBOOK"
echo "=========================================="
echo "Current: $CURRENT_VERSION"
echo "Target:  $NEW_VERSION"
echo "Model:   $NEW_MODEL"
echo "=========================================="

# Step 1: Verify prerequisites
echo "[1/8] Verifying prerequisites..."
./scripts/verify_model.sh $NEW_MODEL
./scripts/check_gpu_memory.sh $NEW_MODEL

# Step 2: Deploy to GREEN environment
echo "[2/8] Deploying to GREEN environment..."
docker-compose -f docker-compose.green.yml up -d \
  --env MODEL_NAME=$NEW_MODEL \
  --env MODEL_VERSION=$NEW_VERSION

# Step 3: Wait for model loading
echo "[3/8] Waiting for model to load..."
sleep 300  # 5 minutes for 70B model
until curl -s http://green:8002/health | grep -q "ok"; do
    echo "Waiting for GREEN health check..."
    sleep 30
done

# Step 4: Run smoke tests
echo "[4/8] Running smoke tests..."
python scripts/smoke_test.py --endpoint http://green:8002 --verbose
if [ $? -ne 0 ]; then
    echo "ERROR: Smoke tests failed. Aborting upgrade."
    docker-compose -f docker-compose.green.yml down
    exit 1
fi

# Step 5: Canary deployment
echo "[5/8] Starting canary deployment ($CANARY_PERCENTAGE%)..."
./scripts/update_load_balancer.sh --green-weight $CANARY_PERCENTAGE

# Step 6: Monitor canary
echo "[6/8] Monitoring canary for $MONITORING_PERIOD seconds..."
python scripts/monitor_canary.py \
    --duration $MONITORING_PERIOD \
    --error-threshold 0.01 \
    --latency-threshold 10

if [ $? -ne 0 ]; then
    echo "ERROR: Canary metrics exceeded thresholds. Rolling back..."
    ./scripts/update_load_balancer.sh --green-weight 0
    docker-compose -f docker-compose.green.yml down
    exit 1
fi

# Step 7: Full rollout
echo "[7/8] Canary successful. Proceeding with full rollout..."
./scripts/update_load_balancer.sh --green-weight 100

# Step 8: Cleanup
echo "[8/8] Marking BLUE for retirement (keep for 24h)..."
echo "BLUE_RETIRE_AT=$(date -d '+24 hours' +%Y-%m-%dT%H:%M:%S)" >> .env

echo "=========================================="
echo "MODEL UPGRADE COMPLETE"
echo "New Version: $NEW_VERSION"
echo "Rollback available for 24 hours"
echo "=========================================="
```

### 1.3 Rollback Procedure

```bash
#!/bin/bash
# Playbook: Model Rollback
# Use: In case of issues after upgrade

echo "=========================================="
echo "MODEL ROLLBACK PLAYBOOK"
echo "=========================================="

# Step 1: Redirect traffic to BLUE
echo "[1/3] Redirecting all traffic to BLUE..."
./scripts/update_load_balancer.sh --blue-weight 100 --green-weight 0

# Step 2: Stop GREEN
echo "[2/3] Stopping GREEN environment..."
docker-compose -f docker-compose.green.yml down

# Step 3: Verify
echo "[3/3] Verifying BLUE is healthy..."
curl -s http://blue:8001/health | jq

echo "=========================================="
echo "ROLLBACK COMPLETE"
echo "System is running on previous version"
echo "=========================================="
```

### 1.4 Post-Upgrade Verification

```yaml
post_upgrade:
  immediate:
    - [ ] Health check passing
    - [ ] Metrics flowing to Grafana
    - [ ] Sample queries successful
    - [ ] No error spikes in logs
    
  24_hours:
    - [ ] Error rate normal (<1%)
    - [ ] Latency within SLA
    - [ ] User feedback positive
    - [ ] Decommission BLUE environment
    
  documentation:
    - [ ] Update model registry
    - [ ] Update runbooks
    - [ ] Close change request
    - [ ] Update version in documentation
```

---

## 2. Restart Procedure

### 2.1 Graceful Restart (No Downtime)

```bash
#!/bin/bash
# Playbook: Graceful Restart
# Use: Restart services without downtime

echo "=========================================="
echo "GRACEFUL RESTART PLAYBOOK"
echo "=========================================="

# Step 1: Check current status
echo "[1/5] Current service status..."
docker-compose ps

# Step 2: Drain connections (gateway)
echo "[2/5] Draining connections..."
kubectl annotate ingress goai-ingress nginx.ingress.kubernetes.io/service-upstream=true

# Step 3: Rolling restart
echo "[3/5] Performing rolling restart..."
docker-compose up -d --no-deps --scale gateway=3 gateway
sleep 10

# Restart one service at a time
for service in rag-service agent-service memory-service; do
    echo "Restarting $service..."
    docker-compose restart $service
    sleep 30
    # Verify health
    until docker-compose exec $service curl -s localhost:8000/health | grep -q "ok"; do
        sleep 5
    done
done

# Step 4: Verify all services
echo "[4/5] Verifying all services..."
docker-compose ps
curl -s http://localhost:8000/health | jq

# Step 5: Resume traffic
echo "[5/5] Resuming normal traffic..."
kubectl annotate ingress goai-ingress nginx.ingress.kubernetes.io/service-upstream-

echo "=========================================="
echo "GRACEFUL RESTART COMPLETE"
echo "=========================================="
```

### 2.2 Full Restart (With Downtime)

```bash
#!/bin/bash
# Playbook: Full Restart
# Use: Complete system restart (requires maintenance window)

echo "=========================================="
echo "FULL RESTART PLAYBOOK"
echo "=========================================="
echo "WARNING: This will cause downtime"
read -p "Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Step 1: Enable maintenance mode
echo "[1/6] Enabling maintenance mode..."
./scripts/maintenance_mode.sh enable

# Step 2: Stop all services
echo "[2/6] Stopping all services..."
docker-compose down

# Step 3: Clear caches
echo "[3/6] Clearing caches..."
redis-cli FLUSHALL

# Step 4: Start services
echo "[4/6] Starting services..."
docker-compose up -d

# Step 5: Wait for health
echo "[5/6] Waiting for services to be healthy..."
sleep 60
./scripts/health_check_all.sh

# Step 6: Disable maintenance mode
echo "[6/6] Disabling maintenance mode..."
./scripts/maintenance_mode.sh disable

echo "=========================================="
echo "FULL RESTART COMPLETE"
echo "=========================================="
```

### 2.3 GPU Node Restart

```bash
#!/bin/bash
# Playbook: GPU Node Restart
# Use: Restart GPU inference servers

echo "=========================================="
echo "GPU NODE RESTART PLAYBOOK"
echo "=========================================="

# Step 1: Check GPU status
echo "[1/5] Current GPU status..."
nvidia-smi

# Step 2: Drain node from load balancer
echo "[2/5] Draining node from load balancer..."
./scripts/update_load_balancer.sh --exclude-node $HOSTNAME

# Step 3: Wait for in-flight requests
echo "[3/5] Waiting for in-flight requests (60s)..."
sleep 60

# Step 4: Restart vLLM container
echo "[4/5] Restarting vLLM container..."
docker-compose restart vllm-70b

# Step 5: Wait for model load and re-add to LB
echo "[5/5] Waiting for model to load..."
until curl -s http://localhost:8001/health | grep -q "ok"; do
    echo "Loading model..."
    sleep 30
done
./scripts/update_load_balancer.sh --include-node $HOSTNAME

echo "=========================================="
echo "GPU NODE RESTART COMPLETE"
echo "=========================================="
```

---

## 3. Log Rotation

### 3.1 Log Rotation Configuration

```bash
# /etc/logrotate.d/goai
/var/log/goai/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 goai goai
    sharedscripts
    postrotate
        docker-compose kill -s USR1 gateway
    endscript
}

# Audit logs (longer retention)
/var/log/goai/audit/*.log {
    daily
    rotate 365
    compress
    delaycompress
    missingok
    notifempty
    create 0640 goai goai
}
```

### 3.2 Log Rotation Playbook

```bash
#!/bin/bash
# Playbook: Log Rotation
# Frequency: Daily (automated via cron)

echo "=========================================="
echo "LOG ROTATION PLAYBOOK"
echo "=========================================="

# Step 1: Check disk usage before
echo "[1/5] Disk usage before rotation..."
df -h /var/log/goai

# Step 2: Run logrotate
echo "[2/5] Running logrotate..."
logrotate -v /etc/logrotate.d/goai

# Step 3: Archive old logs to cold storage
echo "[3/5] Archiving to cold storage..."
find /var/log/goai -name "*.gz" -mtime +7 -exec \
    aws s3 cp {} s3://goai-logs-archive/$(date +%Y/%m)/ \;

# Step 4: Clean up archived files
echo "[4/5] Cleaning archived files..."
find /var/log/goai -name "*.gz" -mtime +30 -delete

# Step 5: Check disk usage after
echo "[5/5] Disk usage after rotation..."
df -h /var/log/goai

echo "=========================================="
echo "LOG ROTATION COMPLETE"
echo "=========================================="
```

### 3.3 Log Retention Policy

| Log Type | Hot Storage | Warm Storage | Cold Storage | Total |
|----------|-------------|--------------|--------------|-------|
| Application | 7 days | 30 days | 1 year | 1 year |
| Audit | 30 days | 90 days | 7 years | 7 years |
| Access | 7 days | 30 days | 1 year | 1 year |
| Error | 30 days | 90 days | 2 years | 2 years |
| Debug | 3 days | - | - | 3 days |

---

## 4. Backup Process

### 4.1 Backup Schedule

| Component | Frequency | Retention | Method |
|-----------|-----------|-----------|--------|
| PostgreSQL | Hourly | 7 days | pg_dump |
| FAISS Indexes | Daily | 30 days | File copy |
| Model Weights | On change | Forever | S3 sync |
| Configuration | On change | 90 days | Git + S3 |
| Redis | Hourly | 24 hours | RDB snapshot |

### 4.2 Backup Playbook

```bash
#!/bin/bash
# Playbook: Full Backup
# Frequency: Daily at 02:00 UTC

set -e

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/${BACKUP_DATE}"
S3_BUCKET="s3://goai-backups"

echo "=========================================="
echo "BACKUP PLAYBOOK"
echo "Date: $BACKUP_DATE"
echo "=========================================="

mkdir -p $BACKUP_DIR

# Step 1: PostgreSQL backup
echo "[1/6] Backing up PostgreSQL..."
pg_dump -Fc -h localhost -U goai goai_db > $BACKUP_DIR/postgres.dump
pg_dump -Fc -h localhost -U goai goai_audit > $BACKUP_DIR/audit.dump

# Verify backup
pg_restore --list $BACKUP_DIR/postgres.dump > /dev/null
echo "PostgreSQL backup verified."

# Step 2: FAISS indexes
echo "[2/6] Backing up FAISS indexes..."
tar -czf $BACKUP_DIR/faiss_indexes.tar.gz /data/indexes/

# Step 3: Configuration files
echo "[3/6] Backing up configuration..."
tar -czf $BACKUP_DIR/config.tar.gz \
    /etc/goai/*.yaml \
    /etc/goai/*.yml \
    .env

# Step 4: Redis snapshot
echo "[4/6] Backing up Redis..."
redis-cli BGSAVE
sleep 10
cp /var/lib/redis/dump.rdb $BACKUP_DIR/redis.rdb

# Step 5: Create manifest
echo "[5/6] Creating backup manifest..."
cat > $BACKUP_DIR/manifest.json << EOF
{
    "backup_date": "$BACKUP_DATE",
    "components": {
        "postgres": "postgres.dump",
        "audit": "audit.dump",
        "faiss": "faiss_indexes.tar.gz",
        "config": "config.tar.gz",
        "redis": "redis.rdb"
    },
    "sizes": {
        "postgres": $(stat -f%z $BACKUP_DIR/postgres.dump),
        "faiss": $(stat -f%z $BACKUP_DIR/faiss_indexes.tar.gz),
        "config": $(stat -f%z $BACKUP_DIR/config.tar.gz)
    },
    "checksum": "$(sha256sum $BACKUP_DIR/* | sha256sum | cut -d' ' -f1)"
}
EOF

# Step 6: Upload to S3
echo "[6/6] Uploading to S3..."
aws s3 sync $BACKUP_DIR $S3_BUCKET/$BACKUP_DATE/ --sse AES256

# Cleanup local backup (keep latest only)
find /backup -maxdepth 1 -type d -mtime +1 -exec rm -rf {} \;

echo "=========================================="
echo "BACKUP COMPLETE"
echo "Location: $S3_BUCKET/$BACKUP_DATE/"
echo "Manifest: $BACKUP_DIR/manifest.json"
echo "=========================================="
```

### 4.3 Backup Verification

```bash
#!/bin/bash
# Playbook: Backup Verification
# Frequency: After every backup

BACKUP_PATH=$1

echo "=========================================="
echo "BACKUP VERIFICATION"
echo "=========================================="

# Step 1: Check file existence
echo "[1/4] Checking backup files..."
for file in postgres.dump audit.dump faiss_indexes.tar.gz config.tar.gz manifest.json; do
    if [ ! -f "$BACKUP_PATH/$file" ]; then
        echo "ERROR: Missing $file"
        exit 1
    fi
done
echo "All files present."

# Step 2: Verify PostgreSQL backup
echo "[2/4] Verifying PostgreSQL backup..."
pg_restore --list $BACKUP_PATH/postgres.dump > /dev/null
echo "PostgreSQL backup valid."

# Step 3: Verify tar archives
echo "[3/4] Verifying tar archives..."
tar -tzf $BACKUP_PATH/faiss_indexes.tar.gz > /dev/null
tar -tzf $BACKUP_PATH/config.tar.gz > /dev/null
echo "Archives valid."

# Step 4: Verify manifest checksum
echo "[4/4] Verifying checksum..."
expected_checksum=$(cat $BACKUP_PATH/manifest.json | jq -r '.checksum')
actual_checksum=$(sha256sum $BACKUP_PATH/* 2>/dev/null | sha256sum | cut -d' ' -f1)
if [ "$expected_checksum" != "$actual_checksum" ]; then
    echo "WARNING: Checksum mismatch"
fi

echo "=========================================="
echo "BACKUP VERIFICATION COMPLETE"
echo "=========================================="
```

---

## 5. Restore Test

### 5.1 Restore Test Procedure

```bash
#!/bin/bash
# Playbook: Restore Test
# Frequency: Monthly
# Duration: 2-4 hours

set -e

BACKUP_DATE=${1:-$(aws s3 ls s3://goai-backups/ | tail -1 | awk '{print $2}' | tr -d '/')}
TEST_ENV="restore-test"

echo "=========================================="
echo "RESTORE TEST PLAYBOOK"
echo "Backup: $BACKUP_DATE"
echo "Environment: $TEST_ENV"
echo "=========================================="

# Step 1: Create test environment
echo "[1/8] Creating test environment..."
docker-compose -f docker-compose.test.yml up -d

# Step 2: Download backup
echo "[2/8] Downloading backup..."
aws s3 sync s3://goai-backups/$BACKUP_DATE /tmp/restore_test/

# Step 3: Verify backup integrity
echo "[3/8] Verifying backup integrity..."
./scripts/verify_backup.sh /tmp/restore_test/

# Step 4: Restore PostgreSQL
echo "[4/8] Restoring PostgreSQL..."
docker exec -i postgres-test pg_restore -d goai_db /tmp/restore_test/postgres.dump

# Step 5: Restore FAISS indexes
echo "[5/8] Restoring FAISS indexes..."
tar -xzf /tmp/restore_test/faiss_indexes.tar.gz -C /tmp/test_data/

# Step 6: Restore configuration
echo "[6/8] Restoring configuration..."
tar -xzf /tmp/restore_test/config.tar.gz -C /tmp/test_config/

# Step 7: Start application
echo "[7/8] Starting application..."
docker-compose -f docker-compose.test.yml restart app

# Step 8: Run verification tests
echo "[8/8] Running verification tests..."
./scripts/restore_verification_tests.sh

# Generate report
cat > /tmp/restore_test_report.json << EOF
{
    "test_date": "$(date -Iseconds)",
    "backup_date": "$BACKUP_DATE",
    "result": "PASS",
    "duration_minutes": $SECONDS/60,
    "tests_passed": $(./scripts/count_passed_tests.sh),
    "tests_failed": $(./scripts/count_failed_tests.sh)
}
EOF

# Cleanup
echo "Cleaning up test environment..."
docker-compose -f docker-compose.test.yml down -v

echo "=========================================="
echo "RESTORE TEST COMPLETE"
echo "Result: PASS"
echo "Report: /tmp/restore_test_report.json"
echo "=========================================="
```

### 5.2 Restore Test Checklist

```yaml
restore_test_checklist:
  pre_test:
    - [ ] Maintenance window scheduled
    - [ ] Test environment provisioned
    - [ ] Latest backup identified
    
  verification:
    - [ ] PostgreSQL tables restored
    - [ ] Row counts match (within 0.1%)
    - [ ] FAISS indexes loadable
    - [ ] Vector search returns results
    - [ ] Configuration valid
    - [ ] Application starts
    - [ ] API endpoints responding
    - [ ] Sample queries successful
    
  documentation:
    - [ ] Test report generated
    - [ ] Issues documented
    - [ ] Sign-off from DBA
    - [ ] Compliance ticket closed
```

---

## 6. Index Rebuild

### 6.1 FAISS Index Rebuild

```bash
#!/bin/bash
# Playbook: FAISS Index Rebuild
# Use: When index corruption detected or optimization needed

echo "=========================================="
echo "FAISS INDEX REBUILD PLAYBOOK"
echo "=========================================="

NAMESPACE=${1:-"global"}
BACKUP_BEFORE_REBUILD=true

# Step 1: Pre-rebuild checks
echo "[1/7] Pre-rebuild checks..."
./scripts/check_index_health.sh $NAMESPACE
CURRENT_VECTORS=$(./scripts/count_vectors.sh $NAMESPACE)
echo "Current vector count: $CURRENT_VECTORS"

# Step 2: Backup existing index
if [ "$BACKUP_BEFORE_REBUILD" = true ]; then
    echo "[2/7] Backing up existing index..."
    cp /data/indexes/${NAMESPACE}.faiss /data/indexes/${NAMESPACE}.faiss.bak
    cp /data/indexes/${NAMESPACE}.pkl /data/indexes/${NAMESPACE}.pkl.bak
fi

# Step 3: Put namespace in read-only mode
echo "[3/7] Enabling read-only mode for $NAMESPACE..."
curl -X POST "http://localhost:8000/api/v1/admin/namespace/$NAMESPACE/readonly" \
    -H "Authorization: Bearer $ADMIN_TOKEN"

# Step 4: Export vectors to temporary storage
echo "[4/7] Exporting vectors..."
python scripts/export_vectors.py --namespace $NAMESPACE --output /tmp/vectors_export.jsonl

# Step 5: Rebuild index
echo "[5/7] Rebuilding index..."
python scripts/rebuild_index.py \
    --input /tmp/vectors_export.jsonl \
    --output /data/indexes/${NAMESPACE}_new.faiss \
    --index-type "IVF4096,PQ64" \
    --train-size 100000

# Step 6: Swap indexes
echo "[6/7] Swapping indexes..."
mv /data/indexes/${NAMESPACE}.faiss /data/indexes/${NAMESPACE}.faiss.old
mv /data/indexes/${NAMESPACE}_new.faiss /data/indexes/${NAMESPACE}.faiss

# Step 7: Re-enable write mode and verify
echo "[7/7] Re-enabling write mode and verifying..."
curl -X POST "http://localhost:8000/api/v1/admin/namespace/$NAMESPACE/readwrite" \
    -H "Authorization: Bearer $ADMIN_TOKEN"

# Verify
NEW_VECTORS=$(./scripts/count_vectors.sh $NAMESPACE)
echo "New vector count: $NEW_VECTORS"

if [ "$CURRENT_VECTORS" -ne "$NEW_VECTORS" ]; then
    echo "WARNING: Vector count mismatch!"
fi

# Run search test
python scripts/test_search.py --namespace $NAMESPACE

echo "=========================================="
echo "INDEX REBUILD COMPLETE"
echo "Namespace: $NAMESPACE"
echo "Vectors: $NEW_VECTORS"
echo "=========================================="
```

### 6.2 PostgreSQL Index Rebuild

```bash
#!/bin/bash
# Playbook: PostgreSQL Index Rebuild
# Use: Periodic maintenance or after bulk operations

echo "=========================================="
echo "POSTGRESQL INDEX REBUILD"
echo "=========================================="

# Step 1: Analyze tables
echo "[1/4] Analyzing tables..."
psql -d goai_db -c "ANALYZE VERBOSE;"

# Step 2: Reindex
echo "[2/4] Reindexing..."
psql -d goai_db -c "REINDEX DATABASE goai_db;"

# Step 3: Vacuum
echo "[3/4] Running VACUUM ANALYZE..."
psql -d goai_db -c "VACUUM ANALYZE;"

# Step 4: Update statistics
echo "[4/4] Updating statistics..."
psql -d goai_db -c "ANALYZE;"

echo "=========================================="
echo "POSTGRESQL INDEX REBUILD COMPLETE"
echo "=========================================="
```

---

## 7. Container Versioning

### 7.1 Version Management

```yaml
# Container version policy
versioning:
  format: "v{MAJOR}.{MINOR}.{PATCH}-{BUILD}"
  
  tags:
    - latest       # Current production
    - stable       # Last known good
    - v1.2.3       # Specific version
    - v1.2.3-123   # With build number
    
  registry: "registry.company.com/goai"
  
  retention:
    production: "forever"
    staging: "30 days"
    development: "7 days"
```

### 7.2 Container Update Playbook

```bash
#!/bin/bash
# Playbook: Container Version Update
# Use: Update containers to new version

NEW_VERSION=${1:-"latest"}

echo "=========================================="
echo "CONTAINER UPDATE PLAYBOOK"
echo "Target Version: $NEW_VERSION"
echo "=========================================="

# Step 1: Pull new images
echo "[1/5] Pulling new images..."
docker-compose pull

# Step 2: Verify images
echo "[2/5] Verifying images..."
docker images | grep goai

# Step 3: Tag current as rollback
echo "[3/5] Tagging current version for rollback..."
for service in gateway rag-service agent-service; do
    docker tag goai/$service:latest goai/$service:rollback
done

# Step 4: Update containers
echo "[4/5] Updating containers..."
docker-compose up -d --no-deps

# Step 5: Verify
echo "[5/5] Verifying deployment..."
./scripts/health_check_all.sh

echo "=========================================="
echo "CONTAINER UPDATE COMPLETE"
echo "Version: $NEW_VERSION"
echo "Rollback: docker-compose up -d --no-deps (with :rollback tag)"
echo "=========================================="
```

### 7.3 Version Rollback

```bash
#!/bin/bash
# Playbook: Container Rollback

echo "=========================================="
echo "CONTAINER ROLLBACK PLAYBOOK"
echo "=========================================="

# Step 1: Switch to rollback images
echo "[1/3] Switching to rollback images..."
for service in gateway rag-service agent-service; do
    docker tag goai/$service:rollback goai/$service:latest
done

# Step 2: Restart containers
echo "[2/3] Restarting containers..."
docker-compose up -d --no-deps

# Step 3: Verify
echo "[3/3] Verifying rollback..."
./scripts/health_check_all.sh

echo "=========================================="
echo "ROLLBACK COMPLETE"
echo "=========================================="
```

---

## 8. GPU Monitoring Thresholds

### 8.1 GPU Health Metrics

```yaml
# GPU monitoring thresholds
gpu_thresholds:
  utilization:
    normal: "50-85%"
    warning: ">85%"
    critical: ">95%"
    
  memory:
    normal: "<90%"
    warning: "90-95%"
    critical: ">95%"
    
  temperature:
    normal: "<75°C"
    warning: "75-85°C"
    critical: ">85°C"
    
  power:
    normal: "<300W"  # For L40S
    warning: "300-350W"
    critical: ">350W"
    
  ecc_errors:
    normal: "0"
    warning: "1-10"
    critical: ">10"
```

### 8.2 GPU Monitoring Script

```bash
#!/bin/bash
# Playbook: GPU Health Check
# Frequency: Every 1 minute (via cron)

OUTPUT_FILE="/var/log/goai/gpu_health.json"

# Collect metrics
GPU_DATA=$(nvidia-smi --query-gpu=index,name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw,ecc.errors.corrected.aggregate.total --format=csv,noheader,nounits)

# Parse and check thresholds
echo "{\"timestamp\": \"$(date -Iseconds)\", \"gpus\": [" > $OUTPUT_FILE

first=true
while IFS=',' read -r index name util_gpu util_mem mem_used mem_total temp power ecc; do
    # Check thresholds
    status="ok"
    alerts=()
    
    if (( $(echo "$util_gpu > 95" | bc -l) )); then
        status="critical"
        alerts+=("GPU utilization critical: ${util_gpu}%")
    elif (( $(echo "$util_gpu > 85" | bc -l) )); then
        status="warning"
        alerts+=("GPU utilization high: ${util_gpu}%")
    fi
    
    mem_percent=$(echo "scale=2; $mem_used / $mem_total * 100" | bc)
    if (( $(echo "$mem_percent > 95" | bc -l) )); then
        status="critical"
        alerts+=("Memory critical: ${mem_percent}%")
    fi
    
    if (( $(echo "$temp > 85" | bc -l) )); then
        status="critical"
        alerts+=("Temperature critical: ${temp}°C")
    fi
    
    if [ "$first" = true ]; then
        first=false
    else
        echo "," >> $OUTPUT_FILE
    fi
    
    cat >> $OUTPUT_FILE << EOF
{
    "index": $index,
    "name": "$name",
    "utilization_gpu": $util_gpu,
    "utilization_memory": $util_mem,
    "memory_used_mb": $mem_used,
    "memory_total_mb": $mem_total,
    "temperature_c": $temp,
    "power_w": $power,
    "ecc_errors": $ecc,
    "status": "$status",
    "alerts": $(printf '%s\n' "${alerts[@]}" | jq -R . | jq -s .)
}
EOF

done <<< "$GPU_DATA"

echo "]}" >> $OUTPUT_FILE

# Send alerts if critical
if grep -q '"status": "critical"' $OUTPUT_FILE; then
    ./scripts/send_alert.sh "GPU Critical Alert" "$(cat $OUTPUT_FILE)"
fi
```

### 8.3 GPU Alert Rules

```yaml
# Prometheus alert rules for GPU
groups:
  - name: gpu_alerts
    rules:
      - alert: GPUHighUtilization
        expr: DCGM_FI_DEV_GPU_UTIL > 95
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "GPU {{ $labels.gpu }} utilization > 95%"
          
      - alert: GPUMemoryExhausted
        expr: DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL * 100 > 95
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "GPU {{ $labels.gpu }} memory > 95%"
          
      - alert: GPUHighTemperature
        expr: DCGM_FI_DEV_GPU_TEMP > 85
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "GPU {{ $labels.gpu }} temperature > 85°C"
          
      - alert: GPUECCErrors
        expr: DCGM_FI_DEV_ECC_DBE_AGG_TOTAL > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "GPU {{ $labels.gpu }} ECC errors detected"
```

---

## Quick Reference: Playbook Index

| Situation | Playbook | Time | Impact |
|-----------|----------|------|--------|
| New model version | Model Upgrade | 2-4h | Medium |
| Service unresponsive | Graceful Restart | 15m | None |
| Major issue | Full Restart | 30m | Downtime |
| GPU node issue | GPU Node Restart | 10m | Partial |
| Disk space low | Log Rotation | 5m | None |
| Nightly backup | Backup Process | 30m | None |
| Monthly DR test | Restore Test | 2-4h | None |
| Search degradation | Index Rebuild | 1-4h | Partial |
| Security update | Container Update | 1h | Minimal |
| GPU throttling | Check GPU Thresholds | - | - |

---

**GoAI Sovereign Platform v1** — Operational Playbooks 🔧

