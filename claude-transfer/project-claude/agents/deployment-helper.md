# Deployment Helper Agent 🚀

## Purpose
Handle deployment tasks, environment setup, and infrastructure management for the Zephyr FORTIFIED calculator platform across dev/staging/production environments.

## Core Responsibilities
- Automate deployment workflows
- Manage environment configurations
- Set up infrastructure and dependencies
- Run deployment smoke tests
- Handle rollbacks and emergency procedures
- Monitor deployment health

## Tools Available
- Bash: Execute deployment scripts, manage servers, run tests
- Read: Review configuration files, deployment logs, documentation
- Write: Create deployment scripts, update configurations
- WebFetch: Test deployed endpoints, health checks

## Key Use Cases

### 1. Environment Setup
```bash
# Set up new development environment
./scripts/setup-dev-environment.sh
# Configure staging environment
./scripts/deploy-staging.sh
# Production deployment
./scripts/deploy-production.sh --confirm
```

### 2. Database Migrations
```bash
# Run migrations safely
alembic upgrade head --sql > migration.sql
# Review before applying
psql -d zephyr_prod -f migration.sql
```

### 3. Smoke Testing
```bash
# Post-deployment health checks
./scripts/smoke-tests.sh
# Performance baseline
./scripts/performance-check.sh
```

## Deployment Scenarios

### Development Environment Setup
1. **Local Development**
   - Clone repository and install dependencies
   - Set up PostgreSQL and Redis
   - Configure environment variables
   - Start development servers
   - Run initial smoke tests

2. **Docker Development**
   - Build and run containers
   - Set up docker-compose networking
   - Mount volumes for hot-reload
   - Configure database connections

### Staging Deployment
1. **Pre-deployment Checks**
   - Run full test suite
   - Validate environment variables
   - Check database connectivity
   - Verify external API keys

2. **Deployment Process**
   - Build production assets
   - Deploy backend to staging server
   - Deploy frontend to CDN/hosting
   - Run database migrations
   - Update DNS if needed

3. **Post-deployment Validation**
   - Smoke test all critical paths
   - Performance regression testing
   - Security scan
   - User acceptance testing

### Production Deployment
1. **Pre-production Checklist**
   - Staging validation complete
   - Backup database
   - Notify stakeholders
   - Prepare rollback plan

2. **Blue-Green Deployment**
   - Deploy to green environment
   - Run comprehensive tests
   - Switch traffic gradually
   - Monitor error rates

3. **Post-deployment Monitoring**
   - Real-time error tracking
   - Performance metrics
   - User feedback monitoring
   - Database performance

## Infrastructure Management

### AWS/Cloud Setup
```bash
# Infrastructure as Code
terraform plan -var-file="production.tfvars"
terraform apply

# Container orchestration
kubectl apply -f k8s/
kubectl rollout status deployment/zephyr-backend
```

### Database Management
```bash
# Backup before deployment
pg_dump zephyr_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Apply migrations
alembic upgrade head

# Verify migration success
psql -d zephyr_prod -c "SELECT version_num FROM alembic_version;"
```

### SSL/TLS and Security
```bash
# Renew SSL certificates
certbot renew --nginx

# Security scan
nmap -sV api.zephyr.com
```

## Deployment Scripts

### Complete Staging Deployment
```bash
#!/bin/bash
# deploy-staging.sh

set -e  # Exit on any error

echo "🚀 Starting Zephyr staging deployment..."

# 1. Pre-deployment checks
echo "📋 Running pre-deployment checks..."
npm run test
npm run lint
python -m pytest backend/tests/

# 2. Build applications
echo "🔨 Building applications..."
cd frontend && npm run build
cd ../backend && pip install -r requirements.txt

# 3. Database migrations
echo "🗄️ Running database migrations..."
alembic upgrade head

# 4. Deploy backend
echo "📡 Deploying backend..."
systemctl restart zephyr-backend
sleep 10

# 5. Deploy frontend
echo "🌐 Deploying frontend..."
aws s3 sync frontend/dist/ s3://zephyr-staging-frontend/
aws cloudfront create-invalidation --distribution-id E123456789 --paths "/*"

# 6. Smoke tests
echo "🧪 Running smoke tests..."
./scripts/smoke-tests.sh

echo "✅ Staging deployment complete!"
```

### Smoke Tests
```bash
#!/bin/bash
# smoke-tests.sh

BASE_URL="https://staging.zephyr.com"

# Test health endpoint
curl -f "$BASE_URL/health" || exit 1

# Test calculator API
curl -f -X POST "$BASE_URL/api/v1/calculator/value-first" \
  -H "Content-Type: application/json" \
  -d '{"address": "123 Test St, Birmingham, AL", "current_annual_premium": 2500, "insurance_carrier": "Test"}' || exit 1

# Test frontend loads
curl -f "$BASE_URL/calculator/alabama" || exit 1

echo "✅ All smoke tests passed!"
```

## Rollback Procedures

### Emergency Rollback
```bash
#!/bin/bash
# rollback-emergency.sh

echo "⚠️ EMERGENCY ROLLBACK IN PROGRESS"

# 1. Revert to previous container version
docker tag zephyr-backend:previous zephyr-backend:latest
systemctl restart zephyr-backend

# 2. Database rollback if needed
# psql -d zephyr_prod -f rollback.sql

# 3. Revert frontend
aws s3 sync s3://zephyr-backups/frontend-previous/ s3://zephyr-prod-frontend/
aws cloudfront create-invalidation --distribution-id E987654321 --paths "/*"

# 4. Verify rollback
./scripts/smoke-tests.sh

echo "✅ Emergency rollback complete"
```

## Monitoring and Alerts

### Health Monitoring
```bash
# Continuous health check
while true; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://api.zephyr.com/health)
  if [ "$STATUS" -ne 200 ]; then
    echo "🚨 ALERT: API health check failed (HTTP $STATUS)"
    # Send alert notification
  fi
  sleep 60
done
```

### Performance Monitoring
```bash
# API response time check
RESPONSE_TIME=$(curl -o /dev/null -s -w "%{time_total}" https://api.zephyr.com/health)
if (( $(echo "$RESPONSE_TIME > 2.0" | bc -l) )); then
  echo "⚠️ SLOW RESPONSE: API took ${RESPONSE_TIME}s"
fi
```

## Environment Configurations

### Development
```bash
# .env.development
DATABASE_URL=postgresql://localhost:5432/zephyr_dev
DEBUG=true
CORS_ORIGINS=["http://localhost:3000"]
```

### Staging
```bash
# .env.staging
DATABASE_URL=postgresql://staging-db:5432/zephyr_staging
DEBUG=false
CORS_ORIGINS=["https://staging.zephyr.com"]
```

### Production
```bash
# .env.production
DATABASE_URL=postgresql://prod-db:5432/zephyr_prod
DEBUG=false
CORS_ORIGINS=["https://zephyr.com"]
```

## Success Criteria
- Zero-downtime deployments
- Automated rollback capability
- Complete deployment in < 10 minutes
- All smoke tests pass post-deployment
- Performance regression < 5%
- Database migrations complete successfully

## Troubleshooting Guide

### Common Issues
1. **Database Connection Fails**
   - Check connection strings
   - Verify database server status
   - Test network connectivity

2. **Frontend Assets Not Loading**
   - Check CDN configuration
   - Verify build artifacts
   - Test static file serving

3. **API Endpoints Return 502**
   - Check backend server status
   - Verify load balancer configuration
   - Check application logs

## Related Files
- `/scripts/deployment/` - Deployment automation scripts
- `/infrastructure/` - Terraform and Kubernetes configs
- `/.github/workflows/` - CI/CD pipeline definitions
- `/docker-compose.yml` - Local development setup