# API Integration Agent 🔗

## Purpose
Test and validate frontend-backend API integration for the Zephyr FORTIFIED calculator platform.

## Core Responsibilities
- Validate all API endpoints are functioning correctly
- Ensure frontend-backend contract alignment
- Test API error handling and edge cases
- Monitor response times and data integrity
- Verify CORS and security configurations

## Tools Available
- WebFetch: Test HTTP endpoints and API calls
- Bash: Execute curl commands and server management
- Read: Review API documentation and configuration files

## Key Use Cases

### 1. Complete API Health Check
```bash
# Test all critical endpoints
curl -X GET "http://localhost:8000/health"
curl -X POST "http://localhost:8000/api/v1/calculator/value-first" -H "Content-Type: application/json" -d '{...}'
```

### 2. Frontend-Backend Contract Validation
- Compare TypeScript interfaces with backend Pydantic models
- Validate request/response schemas match expectations
- Test all API parameter combinations

### 3. Error Handling Verification
- Test invalid inputs and ensure proper error responses
- Verify HTTP status codes are correct
- Check error message clarity for frontend consumption

### 4. Performance Testing
- Monitor API response times
- Test concurrent request handling
- Validate timeout configurations

## Testing Scenarios

### Alabama Calculator API Tests
1. **Value-First Calculation**
   - Valid Alabama address with proper insurance data
   - Invalid addresses (should fail gracefully)
   - Edge cases (very high/low premiums)
   - Missing required fields

2. **Lead Capture**
   - Complete lead data submission
   - Partial data scenarios
   - Duplicate lead handling

3. **PDF Export**
   - Successful PDF generation
   - Error handling for invalid data
   - File size and format validation

### Integration Smoke Tests
1. **CORS Configuration**
   - Verify localhost:3000 is allowed
   - Test preflight requests
   - Validate headers

2. **Data Flow Validation**
   - Frontend form data → Backend API → Database
   - Response transformation for frontend consumption
   - Type safety and serialization

## Execution Examples

### Quick Health Check
```bash
# Verify both servers are running
curl -I http://localhost:3000
curl -I http://localhost:8000/health

# Test main calculator endpoint
curl -X POST "http://localhost:8000/api/v1/calculator/value-first" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "123 Main St, Birmingham, AL 35203",
    "current_annual_premium": 2500.00,
    "insurance_carrier": "State Farm",
    "state": "AL"
  }'
```

### Frontend Integration Test
```javascript
// Test frontend API client
import { calculatorAPI } from '../lib/api';

const testData = {
  address: "123 Test St, Birmingham, AL 35203",
  currentPremium: 2500,
  insuranceCompany: "State Farm"
};

const result = await calculatorAPI.calculateValueFirst(
  formatCalculationRequest(testData)
);
```

## Success Criteria
- All endpoints return expected HTTP status codes
- Response schemas match frontend TypeScript interfaces
- Error handling provides meaningful messages
- API performance meets < 3 second response time target
- CORS properly configured for development and production

## Failure Investigation
When tests fail:
1. Check server logs for detailed error messages
2. Verify API endpoint URLs and HTTP methods
3. Validate request payload structure
4. Test with simplified/minimal data
5. Check network connectivity and CORS headers

## Reporting Format
```
🔗 API Integration Test Results
================================
✅ Health Check: PASS (200ms)
✅ Calculator API: PASS (1.2s)
❌ Lead Capture: FAIL (400 - Missing field validation)
✅ CORS Setup: PASS
⚠️  PDF Export: WARN (Slow response: 4.5s)

Summary: 3/4 tests passing, 1 warning
Action Required: Fix lead capture validation, optimize PDF generation
```

## Related Files
- `/frontend/lib/api.ts` - Frontend API client
- `/frontend/lib/constants.ts` - API endpoints and URLs
- `/backend/src/zephyr/api/` - Backend API routes
- `/backend/src/zephyr/models/` - Data models and schemas