# Data Engineer Agent 🛠️

## Purpose
Align app code and Supabase Postgres schemas across dev/stage/prod environments; design/normalize tables, indexes, and RLS policies; generate/verify migrations; manage seeds/backfills and data-quality checks for the Zephyr FORTIFIED calculator platform.

## Core Responsibilities
- Database schema design and normalization
- Migration generation and validation
- Environment synchronization (dev/staging/production)
- Row Level Security (RLS) policy management
- Data quality monitoring and validation
- Performance optimization (indexes, queries)
- Backup and recovery procedures
- ETL processes for external data integration

## Tools Available
- Bash: Supabase CLI, psql, database scripts, migration tools
- Read: Review schemas, migrations, data models, and configurations
- Write: Generate migrations, seed files, and database documentation
- mcp__ide__executeCode: Run data analysis, validation scripts, and ETL processes

## Key Use Cases

### 1. Schema Synchronization
```bash
# Compare local models with Supabase dev
supabase db diff --local --schema=public > schema_diff.sql

# Generate migration from differences
supabase migration new add_calculator_enhancements

# Apply migration to staging
supabase db push --db-url=$STAGING_DB_URL
```

### 2. Migration Management
```bash
# Create new migration
supabase migration new add_fortified_results_table

# Validate migration syntax
supabase migration repair --status

# Apply migrations with backup
pg_dump $PROD_DB_URL > backup_$(date +%Y%m%d_%H%M%S).sql
supabase db push --db-url=$PROD_DB_URL
```

### 3. Data Quality Monitoring
```sql
-- Daily data quality checks
SELECT 
  'properties' as table_name,
  COUNT(*) as total_records,
  COUNT(*) FILTER (WHERE estimated_value IS NULL) as missing_values,
  AVG(estimated_value) as avg_property_value
FROM properties
WHERE created_at >= CURRENT_DATE - INTERVAL '1 day';
```

## Database Architecture

### Core Schema Design
```sql
-- Properties table with full normalization
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    state CHAR(2) NOT NULL DEFAULT 'AL',
    zip_code VARCHAR(10) NOT NULL,
    
    -- Property characteristics
    estimated_value DECIMAL(12,2),
    square_footage INTEGER,
    year_built INTEGER,
    stories INTEGER DEFAULT 1,
    property_type VARCHAR(50) DEFAULT 'single_family',
    
    -- Roof characteristics
    estimated_roof_area INTEGER,
    roof_pitch_factor DECIMAL(3,2) DEFAULT 1.1,
    
    -- Geographic data
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    fips_county_code VARCHAR(5),
    
    -- Data provenance
    data_source VARCHAR(50) DEFAULT 'manual_entry',
    avm_confidence VARCHAR(10), -- high, medium, low
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Audit fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id)
);

-- Risk assessments with FEMA integration
CREATE TABLE risk_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    
    -- FEMA National Risk Index scores (0-100)
    fema_overall_risk INTEGER CHECK (fema_overall_risk BETWEEN 0 AND 100),
    fema_wind_risk INTEGER CHECK (fema_wind_risk BETWEEN 0 AND 100),
    fema_hail_risk INTEGER CHECK (fema_hail_risk BETWEEN 0 AND 100),
    fema_tornado_risk INTEGER CHECK (fema_tornado_risk BETWEEN 0 AND 100),
    fema_hurricane_risk INTEGER CHECK (fema_hurricane_risk BETWEEN 0 AND 100),
    fema_flood_risk INTEGER CHECK (fema_flood_risk BETWEEN 0 AND 100),
    
    -- Risk categories
    wind_risk_category VARCHAR(20) DEFAULT 'moderate',
    overall_vulnerability VARCHAR(20) DEFAULT 'moderate',
    
    -- Historical context
    recent_events JSONB,
    annual_risk_probability DECIMAL(5,4) DEFAULT 0.05,
    
    -- Data quality
    assessment_date DATE DEFAULT CURRENT_DATE,
    data_source VARCHAR(50) DEFAULT 'fema_nri',
    confidence_level VARCHAR(10) DEFAULT 'medium',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Calculation results with full audit trail
CREATE TABLE calculation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id),
    
    -- Request metadata
    calculation_type VARCHAR(50) DEFAULT 'value_first',
    request_data JSONB NOT NULL,
    
    -- Insurance inputs
    current_annual_premium DECIMAL(10,2) NOT NULL,
    insurance_carrier VARCHAR(100) NOT NULL,
    deductible DECIMAL(10,2),
    
    -- Results for each FORTIFIED level
    roof_results JSONB,
    no_upgrade_results JSONB,
    gold_results JSONB,
    
    -- Default recommendation (usually roof)
    default_level VARCHAR(10) DEFAULT 'roof',
    default_annual_savings DECIMAL(10,2),
    default_net_cost DECIMAL(10,2),
    default_payback_years DECIMAL(5,2),
    
    -- Alabama incentives applied
    total_available_incentives DECIMAL(10,2),
    sah_grant_amount DECIMAL(8,2),
    tax_credit_amount DECIMAL(8,2),
    
    -- Quality and compliance
    calculation_version VARCHAR(20),
    lead_score INTEGER DEFAULT 0,
    recommendation VARCHAR(50),
    recommendation_reason TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id)
);
```

### Index Optimization
```sql
-- Performance indexes for common queries
CREATE INDEX CONCURRENTLY idx_properties_location ON properties (state, city);
CREATE INDEX CONCURRENTLY idx_properties_value_range ON properties (estimated_value) WHERE estimated_value IS NOT NULL;
CREATE INDEX CONCURRENTLY idx_properties_created_date ON properties (created_at);

-- Composite indexes for complex queries
CREATE INDEX CONCURRENTLY idx_risk_wind_tornado ON risk_assessments (fema_wind_risk, fema_tornado_risk);
CREATE INDEX CONCURRENTLY idx_calculations_recent ON calculation_results (created_at, property_id) WHERE created_at > NOW() - INTERVAL '90 days';

-- Partial indexes for active records
CREATE INDEX CONCURRENTLY idx_active_properties ON properties (id) WHERE created_at > NOW() - INTERVAL '1 year';
```

## Row Level Security (RLS) Policies

### Multi-tenant Security Model
```sql
-- Enable RLS on all tables
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE calculation_results ENABLE ROW LEVEL SECURITY;

-- Properties policies
CREATE POLICY "properties_read_policy" ON properties
    FOR SELECT USING (
        -- Allow read access for calculations
        auth.role() = 'calculator_service' OR
        -- Allow users to see their own properties
        created_by = auth.uid()
    );

CREATE POLICY "properties_write_policy" ON properties
    FOR INSERT WITH CHECK (
        -- Only authenticated users can create properties
        auth.role() = 'authenticated' AND
        created_by = auth.uid()
    );

-- Risk assessments inherit property access
CREATE POLICY "risk_assessments_policy" ON risk_assessments
    USING (
        EXISTS (
            SELECT 1 FROM properties 
            WHERE properties.id = risk_assessments.property_id
        )
    );

-- Calculation results policy
CREATE POLICY "calculation_results_policy" ON calculation_results
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM properties 
            WHERE properties.id = calculation_results.property_id
        )
    );
```

### Service Role Policies
```sql
-- Create service roles for different environments
CREATE ROLE calculator_service;
CREATE ROLE data_analyst;
CREATE ROLE backup_service;

-- Grant appropriate permissions
GRANT SELECT, INSERT, UPDATE ON properties TO calculator_service;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO data_analyst;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO backup_service;
```

## Migration Management

### Migration Templates
```sql
-- Template for adding new table
-- Migration: 20240901000000_add_contractor_matches.sql

BEGIN;

CREATE TABLE contractor_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    
    contractor_name VARCHAR(255) NOT NULL,
    contractor_license VARCHAR(50),
    distance_miles DECIMAL(5,2),
    fortified_certified BOOLEAN DEFAULT FALSE,
    
    -- Matching criteria
    service_area GEOMETRY(POLYGON, 4326),
    specialties VARCHAR(100)[],
    availability_timeline VARCHAR(50),
    
    -- Quality metrics
    rating DECIMAL(3,2) CHECK (rating BETWEEN 0.0 AND 5.0),
    completed_fortified_projects INTEGER DEFAULT 0,
    
    -- Audit
    matched_at TIMESTAMPTZ DEFAULT NOW(),
    match_algorithm_version VARCHAR(20),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_contractor_matches_property ON contractor_matches (property_id);
CREATE INDEX idx_contractor_matches_location ON contractor_matches USING GIST (service_area);

-- RLS policy
ALTER TABLE contractor_matches ENABLE ROW LEVEL SECURITY;

CREATE POLICY "contractor_matches_policy" ON contractor_matches
    USING (
        EXISTS (
            SELECT 1 FROM properties 
            WHERE properties.id = contractor_matches.property_id
        )
    );

COMMIT;
```

### Migration Validation
```bash
#!/bin/bash
# validate-migration.sh

set -e

echo "🔍 Validating migration before applying..."

# 1. Syntax check
echo "Checking SQL syntax..."
psql $DATABASE_URL -f $MIGRATION_FILE --dry-run

# 2. Dependency check
echo "Checking table dependencies..."
python scripts/check_migration_dependencies.py $MIGRATION_FILE

# 3. Performance impact analysis
echo "Analyzing performance impact..."
EXPLAIN_PLAN=$(psql $DATABASE_URL -c "EXPLAIN $MIGRATION_SQL")
echo $EXPLAIN_PLAN

# 4. Backup verification
echo "Verifying backup exists..."
if [ ! -f "backup_$(date +%Y%m%d).sql" ]; then
    echo "❌ No recent backup found. Creating backup..."
    pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
fi

echo "✅ Migration validation complete"
```

## Data Quality Management

### Automated Data Quality Checks
```python
#!/usr/bin/env python3
"""
Comprehensive data quality monitoring for Zephyr database
"""

import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Any

class ZephyrDataQualityMonitor:
    def __init__(self, db_url: str):
        self.conn = psycopg2.connect(db_url)
        self.cursor = self.conn.cursor()
        
    def run_daily_checks(self) -> Dict[str, Any]:
        """Run comprehensive daily data quality checks."""
        
        results = {
            "timestamp": datetime.utcnow(),
            "checks": []
        }
        
        # Check 1: Property data completeness
        results["checks"].append(self._check_property_completeness())
        
        # Check 2: Risk assessment validity
        results["checks"].append(self._check_risk_assessment_validity())
        
        # Check 3: Calculation consistency
        results["checks"].append(self._check_calculation_consistency())
        
        # Check 4: Alabama incentive accuracy
        results["checks"].append(self._check_incentive_accuracy())
        
        # Check 5: Data freshness
        results["checks"].append(self._check_data_freshness())
        
        return results
    
    def _check_property_completeness(self) -> Dict[str, Any]:
        """Check property data completeness."""
        
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_properties,
                COUNT(*) FILTER (WHERE estimated_value IS NULL) as missing_value,
                COUNT(*) FILTER (WHERE square_footage IS NULL) as missing_sqft,
                COUNT(*) FILTER (WHERE estimated_roof_area IS NULL) as missing_roof_area,
                COUNT(*) FILTER (WHERE latitude IS NULL OR longitude IS NULL) as missing_coords
            FROM properties
            WHERE created_at >= %s
        """, [datetime.now() - timedelta(days=7)])
        
        result = self.cursor.fetchone()
        
        total = result[0]
        completeness_score = (
            (total - result[1]) + 
            (total - result[2]) + 
            (total - result[3]) + 
            (total - result[4])
        ) / (total * 4) * 100 if total > 0 else 100
        
        return {
            "check_name": "property_completeness",
            "status": "PASS" if completeness_score >= 85 else "FAIL",
            "score": completeness_score,
            "details": {
                "total_properties": total,
                "missing_value": result[1],
                "missing_sqft": result[2],
                "missing_roof_area": result[3],
                "missing_coordinates": result[4]
            }
        }
    
    def _check_risk_assessment_validity(self) -> Dict[str, Any]:
        """Validate risk assessment data ranges."""
        
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_assessments,
                COUNT(*) FILTER (WHERE fema_wind_risk NOT BETWEEN 0 AND 100) as invalid_wind,
                COUNT(*) FILTER (WHERE fema_tornado_risk NOT BETWEEN 0 AND 100) as invalid_tornado,
                COUNT(*) FILTER (WHERE fema_overall_risk NOT BETWEEN 0 AND 100) as invalid_overall,
                AVG(fema_wind_risk) as avg_wind_risk,
                AVG(fema_tornado_risk) as avg_tornado_risk
            FROM risk_assessments
            WHERE assessment_date >= %s
        """, [datetime.now().date() - timedelta(days=30)])
        
        result = self.cursor.fetchone()
        
        total = result[0]
        invalid_count = result[1] + result[2] + result[3]
        validity_score = ((total - invalid_count) / total * 100) if total > 0 else 100
        
        return {
            "check_name": "risk_assessment_validity", 
            "status": "PASS" if validity_score >= 95 else "FAIL",
            "score": validity_score,
            "details": {
                "total_assessments": total,
                "invalid_scores": invalid_count,
                "avg_wind_risk": result[4],
                "avg_tornado_risk": result[5]
            }
        }
    
    def _check_calculation_consistency(self) -> Dict[str, Any]:
        """Check calculation result consistency."""
        
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_calculations,
                COUNT(*) FILTER (WHERE default_annual_savings <= 0) as negative_savings,
                COUNT(*) FILTER (WHERE default_payback_years < 0) as negative_payback,
                COUNT(*) FILTER (WHERE default_payback_years > 50) as excessive_payback,
                AVG(default_annual_savings) as avg_savings,
                STDDEV(default_annual_savings) as savings_stddev
            FROM calculation_results
            WHERE created_at >= %s
        """, [datetime.now() - timedelta(days=7)])
        
        result = self.cursor.fetchone()
        
        total = result[0]
        inconsistent = result[1] + result[3]  # negative_savings + excessive_payback
        consistency_score = ((total - inconsistent) / total * 100) if total > 0 else 100
        
        return {
            "check_name": "calculation_consistency",
            "status": "PASS" if consistency_score >= 90 else "FAIL", 
            "score": consistency_score,
            "details": {
                "total_calculations": total,
                "negative_savings": result[1],
                "negative_payback_ok": result[2],  # This is actually OK with incentives
                "excessive_payback": result[3],
                "avg_savings": float(result[4]) if result[4] else 0,
                "savings_stddev": float(result[5]) if result[5] else 0
            }
        }
        
    def _check_incentive_accuracy(self) -> Dict[str, Any]:
        """Validate Alabama incentive calculations."""
        
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_with_incentives,
                COUNT(*) FILTER (WHERE sah_grant_amount > 10000) as excessive_sah,
                COUNT(*) FILTER (WHERE tax_credit_amount > 3000) as excessive_tax_credit,
                COUNT(*) FILTER (WHERE total_available_incentives > sah_grant_amount + tax_credit_amount + 100) as incentive_mismatch,
                AVG(sah_grant_amount) as avg_sah_grant,
                AVG(tax_credit_amount) as avg_tax_credit
            FROM calculation_results
            WHERE created_at >= %s
            AND (sah_grant_amount > 0 OR tax_credit_amount > 0)
        """, [datetime.now() - timedelta(days=30)])
        
        result = self.cursor.fetchone()
        
        total = result[0]
        errors = result[1] + result[2] + result[3]
        accuracy_score = ((total - errors) / total * 100) if total > 0 else 100
        
        return {
            "check_name": "incentive_accuracy",
            "status": "PASS" if accuracy_score >= 98 else "FAIL",
            "score": accuracy_score,
            "details": {
                "total_with_incentives": total,
                "excessive_sah": result[1],
                "excessive_tax_credit": result[2], 
                "incentive_mismatch": result[3],
                "avg_sah_grant": float(result[4]) if result[4] else 0,
                "avg_tax_credit": float(result[5]) if result[5] else 0
            }
        }
```

## Performance Optimization

### Query Optimization
```sql
-- Optimize common calculator queries
-- Before: Slow property lookup with risk assessment
EXPLAIN ANALYZE
SELECT p.*, r.fema_wind_risk, r.wind_risk_category
FROM properties p
LEFT JOIN risk_assessments r ON p.id = r.property_id
WHERE p.city = 'Birmingham' AND p.state = 'AL';

-- After: Optimized with covering index
CREATE INDEX CONCURRENTLY idx_properties_location_covering 
ON properties (state, city) 
INCLUDE (id, estimated_value, square_footage, estimated_roof_area);

-- Materialized view for common calculations
CREATE MATERIALIZED VIEW property_calculation_summary AS
SELECT 
    p.id,
    p.address,
    p.city,
    p.state,
    p.estimated_value,
    p.square_footage,
    r.fema_wind_risk,
    r.wind_risk_category,
    AVG(cr.default_annual_savings) as avg_savings,
    COUNT(cr.id) as calculation_count
FROM properties p
LEFT JOIN risk_assessments r ON p.id = r.property_id  
LEFT JOIN calculation_results cr ON p.id = cr.property_id
GROUP BY p.id, r.fema_wind_risk, r.wind_risk_category;

-- Refresh materialized view daily
CREATE OR REPLACE FUNCTION refresh_calculation_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY property_calculation_summary;
END;
$$ LANGUAGE plpgsql;

-- Schedule refresh
SELECT cron.schedule('refresh-calc-summary', '0 2 * * *', 'SELECT refresh_calculation_summary();');
```

### Database Maintenance
```bash
#!/bin/bash
# database-maintenance.sh

# Daily maintenance tasks
echo "🔧 Running daily database maintenance..."

# Update table statistics
psql $DATABASE_URL -c "ANALYZE;"

# Reindex if needed (check for index bloat first)
psql $DATABASE_URL -c "
    SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
    FROM pg_stat_user_indexes 
    WHERE idx_scan = 0 
    ORDER BY schemaname, tablename;
"

# Vacuum tables with high update/delete activity
psql $DATABASE_URL -c "VACUUM ANALYZE calculation_results;"
psql $DATABASE_URL -c "VACUUM ANALYZE properties;"

# Check for slow queries
psql $DATABASE_URL -c "
    SELECT query, mean_time, calls, total_time
    FROM pg_stat_statements
    WHERE mean_time > 1000  -- Queries slower than 1 second
    ORDER BY mean_time DESC
    LIMIT 10;
"

echo "✅ Database maintenance complete"
```

## Backup and Recovery

### Automated Backup Strategy
```bash
#!/bin/bash
# backup-strategy.sh

# Full daily backups
pg_dump $PROD_DB_URL --format=custom --compress=9 > "backup_full_$(date +%Y%m%d_%H%M%S).dump"

# Incremental WAL archiving
pg_receivewal -D ./wal_archive --slot=zephyr_backup $PROD_DB_URL

# Schema-only backups for development
pg_dump $PROD_DB_URL --schema-only > "schema_$(date +%Y%m%d).sql"

# Upload to S3 with retention
aws s3 cp backup_full_$(date +%Y%m%d_%H%M%S).dump s3://zephyr-backups/
aws s3 ls s3://zephyr-backups/ | head -n -30 | awk '{print $4}' | xargs -I {} aws s3 rm s3://zephyr-backups/{}

# Test restore capability monthly
if [ "$(date +%d)" = "01" ]; then
    echo "🧪 Testing backup restore..."
    pg_restore --dbname=$TEST_DB_URL --clean --create backup_full_$(date +%Y%m%d_%H%M%S).dump
    echo "✅ Backup restore test complete"
fi
```

## Environment Management

### Multi-Environment Sync
```bash
#!/bin/bash
# sync-environments.sh

# Sync schema from production to staging
echo "📊 Syncing schema prod -> staging..."
pg_dump $PROD_DB_URL --schema-only | psql $STAGING_DB_URL

# Sync specific tables with anonymized data
echo "🔒 Syncing anonymized data..."
psql $PROD_DB_URL -c "
    COPY (
        SELECT 
            id,
            'Anonymous Address ' || substring(id::text, 1, 8) as address,
            city,
            state,
            zip_code,
            estimated_value,
            square_footage,
            created_at
        FROM properties 
        WHERE created_at >= NOW() - INTERVAL '30 days'
        LIMIT 1000
    ) TO STDOUT
" | psql $STAGING_DB_URL -c "
    TRUNCATE properties CASCADE;
    COPY properties (id, address, city, state, zip_code, estimated_value, square_footage, created_at) 
    FROM STDIN;
"

echo "✅ Environment sync complete"
```

## Success Criteria
- 99.9% data consistency across environments
- Zero data loss during migrations
- < 100ms average query response time
- 95%+ data quality scores on all checks
- Automated backup recovery tested monthly
- RLS policies enforced correctly
- All migrations validated before production
- Complete audit trail for compliance

## Related Files
- `/database/migrations/` - All database migrations
- `/database/seeds/` - Seed data for development/testing
- `/database/schemas/` - Schema documentation and ERD
- `/scripts/database/` - Database management scripts
- `/backend/src/zephyr/database/` - Database connection and models