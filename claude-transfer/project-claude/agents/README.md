# Zephyr Platform Agents 🤖

This directory contains specialized agents for automating various aspects of the Zephyr FORTIFIED calculator platform development, testing, and maintenance.

## Available Agents

### 1. **code-reviewer** 📝
- **Purpose**: Review code for quality, security, and best practices
- **Tools**: Full tool access for comprehensive code analysis
- **Use Case**: "Review this authentication function before committing"

### 2. **api-integration** 🔗
- **Purpose**: Test and validate frontend-backend API integration
- **Tools**: WebFetch, Bash, Read
- **Use Case**: "Verify all API endpoints work correctly and match frontend expectations"

### 3. **deployment-helper** 🚀
- **Purpose**: Handle deployment tasks, environment setup, and infrastructure
- **Tools**: Bash, Read, Write, WebFetch
- **Use Case**: "Deploy to staging and run smoke tests"

### 4. **data-validator** 📊
- **Purpose**: Validate property data, incentive calculations, and business logic
- **Tools**: Read, mcp__ide__executeCode, Bash
- **Use Case**: "Check that all Alabama incentive calculations are accurate"

### 5. **ui-tester** 🎨
- **Purpose**: Test user flows and UI interactions
- **Tools**: Read, WebFetch, Bash (Playwright integration)
- **Use Case**: "Test the complete user journey from address input to PDF export"

### 6. **data-engineer** 🛠️
- **Purpose**: Database schema management, migrations, and data quality
- **Tools**: Supabase CLI, psql, Alembic, Read, Write, Bash, mcp__ide__executeCode
- **Use Case**: "Compare models.py to Supabase dev, generate migration, test on staging"

### 7. **design-review** 🎨
- **Purpose**: Validate design compliance and user experience
- **Tools**: Read, browser automation
- **Use Case**: "Review UI changes against MOAT brand guidelines"

## How to Use Agents

Agents are invoked through the Task tool with the appropriate subagent type. Here are example invocations:

### Example: Code Review
```
Use the code-reviewer agent to review the new FORTIFIED calculation service for security issues and best practices.
```

### Example: API Testing
```
Use the api-integration agent to verify that all calculator endpoints are working correctly and the frontend can communicate with the backend.
```

### Example: Database Migration
```
Use the data-engineer agent to compare the current Pydantic models with the Supabase schema and generate any necessary migrations.
```

## Agent Capabilities Matrix

| Agent | Code Analysis | API Testing | Database | UI Testing | Deployment | Data Quality |
|-------|---------------|-------------|----------|------------|------------|--------------|
| code-reviewer | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| api-integration | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| deployment-helper | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |
| data-validator | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| ui-tester | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| data-engineer | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| design-review | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |

## Development Workflow Integration

### Pre-Commit
- **code-reviewer**: Review all changes before commit
- **data-validator**: Validate any calculation logic changes

### Pre-Deployment
- **api-integration**: Verify API contracts
- **ui-tester**: Run critical user flow tests
- **deployment-helper**: Handle deployment process

### Post-Deployment
- **deployment-helper**: Run smoke tests
- **data-validator**: Monitor data quality

### Database Changes
- **data-engineer**: Handle all schema changes and migrations
- **data-validator**: Verify data integrity after migrations

## Agent Communication

Agents can work together on complex tasks:

1. **data-engineer** creates new database schema
2. **code-reviewer** reviews the generated migration code
3. **api-integration** tests the new API endpoints
4. **ui-tester** validates the frontend integration
5. **deployment-helper** deploys to staging
6. **data-validator** confirms data quality

## Maintenance

### Adding New Agents
1. Create agent specification in this directory
2. Define clear purpose, tools, and use cases
3. Update this README with the new agent
4. Test agent functionality with sample tasks

### Updating Existing Agents
1. Modify the agent specification file
2. Update capabilities matrix in this README
3. Test changes with representative tasks
4. Document any breaking changes

## Best Practices

### Agent Selection
- Choose the most specialized agent for each task
- Use **general-purpose** agents for complex multi-step workflows
- Combine agents for comprehensive validation workflows

### Task Description
- Be specific about what you want the agent to accomplish
- Provide context about the current state of the system
- Specify success criteria and expected outputs

### Result Validation
- Review agent outputs for accuracy and completeness
- Cross-validate critical results with multiple agents
- Maintain audit trails for compliance and debugging

## Troubleshooting

### Common Issues
1. **Agent not responding appropriately**
   - Check agent specification for tool availability
   - Verify task description matches agent capabilities
   - Try breaking complex tasks into smaller steps

2. **Tool access errors**
   - Ensure required tools are listed in agent specification
   - Check file permissions and network access
   - Verify environment variables are set correctly

3. **Inconsistent results**
   - Review agent specification for ambiguities
   - Add more specific success criteria
   - Consider using multiple agents for validation

## Contributing

When adding new agents or modifying existing ones:
1. Follow the established format and structure
2. Include comprehensive use cases and examples
3. Test thoroughly before committing
4. Update documentation and capabilities matrix
5. Consider agent interactions and workflows

---

*This agent system is designed to accelerate Zephyr platform development while maintaining high quality and reliability standards.*