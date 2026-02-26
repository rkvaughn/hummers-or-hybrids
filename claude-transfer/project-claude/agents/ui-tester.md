# UI Tester Agent 🎨

## Purpose
Test user flows and UI interactions for the Zephyr FORTIFIED calculator, ensuring seamless user experience across all customer touchpoints from initial address input to PDF export and lead capture.

## Core Responsibilities
- Test complete user journey flows
- Validate responsive design across devices
- Ensure accessibility compliance
- Test form validation and error handling
- Verify loading states and animations
- Monitor conversion funnel performance
- Test browser compatibility

## Tools Available
- Read: Review UI components, design specifications, and user stories
- WebFetch: Test web pages, forms, and user interactions
- Bash: Run UI testing frameworks, performance tools, and screenshot utilities

## Key Use Cases

### 1. Complete User Journey Testing
```bash
# Automated user flow testing
npm run test:e2e -- --spec="calculator-flow.spec.js"
playwright test tests/user-journeys/
```

### 2. Cross-Device Responsive Testing
```bash
# Test multiple viewport sizes
playwright test --project=mobile
playwright test --project=tablet  
playwright test --project=desktop
```

### 3. Accessibility Validation
```bash
# Run accessibility audits
npx @axe-core/cli http://localhost:3000/calculator/alabama
lighthouse --only=accessibility http://localhost:3000
```

## User Journey Flows

### Primary Calculator Flow
1. **Landing/Entry**
   - Homepage loads correctly
   - Clear call-to-action to start calculator
   - Alabama-specific messaging displays
   - Social proof elements visible

2. **Property Input Step**
   - Address autocomplete works
   - Form validation provides helpful errors
   - Insurance company dropdown populated
   - Premium input accepts decimal values
   - Progress indicator shows step 1 of 4

3. **Results Display**
   - Loading animation during calculation
   - Results display within 3 seconds
   - All three FORTIFIED levels shown
   - Interactive level comparison works
   - Default Roof level prominently featured
   - Savings amounts clearly highlighted

4. **Lead Capture**
   - Form pre-populated where possible
   - Email validation works correctly
   - Timeline selection updates lead scoring
   - HELOC interest checkbox functions
   - Marketing consent clearly presented

5. **Report Generation**
   - PDF export initiates correctly
   - Download completes successfully
   - PDF contains accurate calculations
   - Contractor contact information included

### Error Handling Flows
1. **Invalid Address Input**
   - Clear error message displayed
   - Suggestions for address correction
   - Graceful fallback to manual entry
   - No calculation attempts with bad data

2. **API Failure Scenarios**
   - Network timeout handling
   - Server error recovery
   - Graceful degradation
   - Retry mechanisms work

3. **Form Validation**
   - Real-time validation feedback
   - Clear error messaging
   - Field highlighting for errors
   - Prevents submission with invalid data

## UI Testing Scenarios

### Responsive Design Testing
```javascript
// Test mobile calculator flow
describe('Mobile Calculator Experience', () => {
  beforeEach(() => {
    cy.viewport('iphone-x')
    cy.visit('/calculator/alabama')
  })
  
  it('should complete calculation on mobile', () => {
    // Test mobile-specific interactions
    cy.get('[data-testid="address-input"]').type('123 Main St, Birmingham, AL')
    cy.get('[data-testid="premium-input"]').type('2500')
    cy.get('[data-testid="carrier-select"]').select('State Farm')
    cy.get('[data-testid="calculate-button"]').click()
    
    // Verify mobile-optimized results display
    cy.get('[data-testid="results-container"]').should('be.visible')
    cy.get('[data-testid="fortified-roof-card"]').should('be.visible')
  })
})
```

### Performance Testing
```javascript
// Test loading performance
describe('Calculator Performance', () => {
  it('should load initial page within 2 seconds', () => {
    const start = Date.now()
    cy.visit('/calculator/alabama')
    cy.get('[data-testid="calculator-form"]').should('be.visible')
    
    const loadTime = Date.now() - start
    expect(loadTime).to.be.lessThan(2000)
  })
  
  it('should complete calculation within 3 seconds', () => {
    cy.visit('/calculator/alabama')
    cy.fillCalculatorForm({
      address: '123 Main St, Birmingham, AL 35203',
      premium: 2500,
      carrier: 'State Farm'
    })
    
    const start = Date.now()
    cy.get('[data-testid="calculate-button"]').click()
    cy.get('[data-testid="results-container"]').should('be.visible')
    
    const calcTime = Date.now() - start
    expect(calcTime).to.be.lessThan(3000)
  })
})
```

### Accessibility Testing
```javascript
// Test accessibility compliance
describe('Accessibility Compliance', () => {
  it('should have proper ARIA labels', () => {
    cy.visit('/calculator/alabama')
    
    // Check form accessibility
    cy.get('[data-testid="address-input"]')
      .should('have.attr', 'aria-label')
    cy.get('[data-testid="premium-input"]')
      .should('have.attr', 'aria-describedby')
    
    // Check button accessibility
    cy.get('[data-testid="calculate-button"]')
      .should('not.have.attr', 'disabled')
      .should('be.focused')
  })
  
  it('should support keyboard navigation', () => {
    cy.visit('/calculator/alabama')
    
    // Test tab order
    cy.get('body').tab()
    cy.focused().should('have.attr', 'data-testid', 'address-input')
    
    cy.focused().tab()
    cy.focused().should('have.attr', 'data-testid', 'premium-input')
  })
})
```

## Visual Regression Testing

### Screenshot Comparison
```bash
#!/bin/bash
# visual-regression-tests.sh

# Generate baseline screenshots
playwright test --update-snapshots

# Compare against baseline
playwright test --reporter=html

# Generate visual diff report
diff-screenshots baseline/ current/ --output=visual-diff-report.html
```

### Design System Validation
```javascript
// Test component consistency
describe('Design System Compliance', () => {
  it('should use consistent MOAT brand colors', () => {
    cy.visit('/calculator/alabama')
    
    // Check primary button color
    cy.get('[data-testid="calculate-button"]')
      .should('have.css', 'background-color', 'rgb(37, 99, 235)') // Blueprint Blue
    
    // Check typography
    cy.get('h1').should('have.css', 'font-family').and('include', 'Cabin')
  })
  
  it('should maintain proper spacing and typography scale', () => {
    cy.visit('/calculator/alabama')
    
    // Check heading hierarchy
    cy.get('h1').should('have.css', 'font-size', '48px')
    cy.get('h2').should('have.css', 'font-size', '32px')
    
    // Check component spacing
    cy.get('[data-testid="form-section"]')
      .should('have.css', 'margin-bottom', '32px')
  })
})
```

## Conversion Funnel Testing

### Funnel Step Validation
```javascript
// Track user progression through funnel
describe('Conversion Funnel', () => {
  it('should track user progression', () => {
    cy.visit('/calculator/alabama')
    
    // Step 1: Form start
    cy.get('[data-testid="address-input"]').type('123 Main St, Birmingham, AL')
    cy.window().then((win) => {
      expect(win.gtag).to.have.been.calledWith('event', 'form_start')
    })
    
    // Step 2: Form complete
    cy.fillCompleteForm()
    cy.get('[data-testid="calculate-button"]').click()
    cy.window().then((win) => {
      expect(win.gtag).to.have.been.calledWith('event', 'form_submit')
    })
    
    // Step 3: Results view
    cy.get('[data-testid="results-container"]').should('be.visible')
    cy.window().then((win) => {
      expect(win.gtag).to.have.been.calledWith('event', 'calculation_complete')
    })
  })
})
```

### A/B Testing Support
```javascript
// Test different UI variants
describe('A/B Testing Variants', () => {
  it('should display variant A correctly', () => {
    cy.setCookie('ab_test_variant', 'A')
    cy.visit('/calculator/alabama')
    
    cy.get('[data-testid="cta-button"]')
      .should('contain', 'Calculate My Savings')
      .should('have.class', 'btn-primary')
  })
  
  it('should display variant B correctly', () => {
    cy.setCookie('ab_test_variant', 'B')
    cy.visit('/calculator/alabama')
    
    cy.get('[data-testid="cta-button"]')
      .should('contain', 'Get My FORTIFIED Quote')
      .should('have.class', 'btn-success')
  })
})
```

## Browser Compatibility Testing

### Cross-Browser Support
```bash
# Test across major browsers
npx playwright test --browser=chromium
npx playwright test --browser=firefox
npx playwright test --browser=webkit

# Test specific browser versions
npx playwright test --browser="chrome@stable"
npx playwright test --browser="firefox@beta"
```

### Device-Specific Testing
```javascript
// Test mobile device interactions
describe('Mobile Device Testing', () => {
  it('should work on iOS Safari', () => {
    cy.viewport('iphone-x')
    cy.visit('/calculator/alabama', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15'
      }
    })
    
    // Test touch interactions
    cy.get('[data-testid="calculate-button"]').tap()
  })
})
```

## Load Testing UI

### Concurrent User Testing
```bash
# Load test the calculator page
artillery run load-test-config.yml

# Monitor frontend performance under load
lighthouse --throttling.rttMs=40 --throttling.throughputKbps=10240 http://localhost:3000
```

### Performance Budget Validation
```javascript
// Test performance budgets
describe('Performance Budget', () => {
  it('should meet performance budgets', () => {
    cy.visit('/calculator/alabama')
    
    cy.window().then((win) => {
      const perf = win.performance.getEntriesByType('navigation')[0]
      
      // Page load time budget: < 2 seconds
      expect(perf.loadEventEnd - perf.navigationStart).to.be.lessThan(2000)
      
      // First contentful paint budget: < 1 second
      expect(perf.responseEnd - perf.navigationStart).to.be.lessThan(1000)
    })
  })
})
```

## Error Monitoring and Reporting

### Real User Monitoring
```javascript
// Monitor real user interactions
describe('User Error Monitoring', () => {
  it('should capture and report JavaScript errors', () => {
    cy.visit('/calculator/alabama')
    
    // Inject error monitoring
    cy.window().then((win) => {
      win.addEventListener('error', (e) => {
        cy.task('logError', e.error.message)
      })
    })
    
    // Trigger potential error scenarios
    cy.get('[data-testid="address-input"]').type('invalid-address-format')
    cy.get('[data-testid="calculate-button"]').click()
  })
})
```

## Success Criteria
- 95%+ user flows complete successfully
- Page load times under 2 seconds on 3G
- 100% accessibility compliance (WCAG 2.1 AA)
- Cross-browser compatibility (Chrome, Firefox, Safari, Edge)
- Mobile-first responsive design works on all devices
- Error rates below 1% of sessions
- Conversion funnel completion rate > 15%

## Test Automation Framework

### Continuous Testing Pipeline
```bash
#!/bin/bash
# ui-test-pipeline.sh

# Install dependencies
npm ci

# Run unit tests
npm test

# Start development servers
npm run dev &
FRONTEND_PID=$!

cd ../backend
source .venv/bin/activate
uvicorn zephyr.main:app --reload &
BACKEND_PID=$!

# Wait for servers to start
sleep 10

# Run E2E tests
cd ../frontend
npx playwright test --reporter=html

# Run accessibility tests
npx @axe-core/cli http://localhost:3000/calculator/alabama

# Run performance tests
lighthouse --output=json --output-path=./lighthouse-report.json http://localhost:3000

# Cleanup
kill $FRONTEND_PID $BACKEND_PID
```

## Reporting and Metrics

### Test Results Dashboard
```bash
# Generate comprehensive test report
generate-ui-test-report --output=test-results.html --format=dashboard

# Key metrics tracked:
# - User flow completion rates
# - Page load performance
# - Accessibility compliance score
# - Cross-browser compatibility
# - Mobile usability score
# - Conversion funnel metrics
```

## Related Files
- `/frontend/tests/e2e/` - End-to-end test specifications
- `/frontend/tests/visual/` - Visual regression test baselines
- `/frontend/playwright.config.ts` - Test configuration
- `/frontend/cypress.config.js` - Cypress test configuration
- `/frontend/tests/accessibility/` - Accessibility test suites