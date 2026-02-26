# Code Quality Standards

## Non-Negotiable Rules

### Security
- **NEVER** commit secrets, API keys, or credentials
- **ALWAYS** validate user input
- **ALWAYS** use parameterized queries (no SQL injection)
- **ALWAYS** sanitize outputs (XSS prevention)

### Error Handling
- **NEVER** silently fail
- **ALWAYS** log errors with context
- **ALWAYS** return user-friendly messages
- **ALWAYS** use structured error responses

### Code Organization
- **Single Responsibility:** One function, one purpose
- **DRY:** Extract repeated logic
- **Naming:** Clear, descriptive, consistent
- **Comments:** Explain WHY, not WHAT

## Language-Specific Standards

### Python (Backend)
- Type hints on all functions
- Docstrings for public APIs
- Black formatter (line length 100)
- Imports: stdlib → third-party → local

### TypeScript (Frontend)
- Strict TypeScript mode
- Props interfaces for all components
- Avoid `any` type
- Prettier formatter

## Code Review Checklist

- [ ] Tests written and passing
- [ ] No hardcoded values (use config)
- [ ] Error handling implemented
- [ ] Logging added for debugging
- [ ] Documentation updated
