# Testing Requirements

## Test-Driven Development (TDD)

**Required for:**
- All calculator logic changes
- New API endpoints
- Database schema changes
- Business logic functions

**RED-GREEN-REFACTOR cycle:**
1. Write failing test first
2. Implement minimum code to pass
3. Refactor with tests still passing

## Coverage Targets

- **Backend:** 80% minimum coverage
- **Frontend:** 70% minimum coverage
- **Calculator logic:** 90+ % coverage (critical path)

## Test Categories

### Unit Tests
- Pure functions and utilities
- Component logic
- Service methods

### Integration Tests
- API endpoint flows
- Database operations
- External service mocks

### E2E Tests
- Critical user journeys (calculator flow)
- Lead capture process
- Error states and recovery

## When to Write Tests

**BEFORE implementing:**
- New features
- Bug fixes
- Refactoring

**Test file naming:**
- Backend: `test_<module>.py`
- Frontend: `<component>.test.tsx`
