# Git Workflow Rules

## Commit Standards

### Conventional Commits Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples:**
```
feat(calculator): add Alabama tax credit calculation
fix(api): handle missing property data gracefully
docs(readme): update setup instructions
```

## Prohibited Actions

**NEVER:**
- Commit directly to `main` branch
- Force push to shared branches
- Commit `.env` files or secrets
- Skip pre-commit hooks
- Merge without review (except hotfixes)

## Branch Naming

- Feature: `feature/calculator-improvements`
- Bugfix: `fix/roi-calculation-error`
- Hotfix: `hotfix/security-patch`
- Docs: `docs/update-api-guide`

## Pull Request Requirements

- Clear title describing the change
- Description with context and testing notes
- Link to related issues
- All CI checks passing
- At least one approval (except emergencies)
