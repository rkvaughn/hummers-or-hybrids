# Claude Code Hooks for Zephyr

This directory contains hooks that enable automatic skill activation and file tracking in the Zephyr project.

## Installed Hooks

### 1. skill-activation-prompt (UserPromptSubmit)
**Purpose:** Automatically suggests relevant skills based on your prompts

**How it works:**
- Analyzes your prompt when you hit enter
- Checks `skill-rules.json` for matching patterns
- Displays recommended skills BEFORE Claude responds
- Ensures you use the right skill at the right time

**Example:**
```
You: "Let's implement the new calculator feature"

🎯 SKILL ACTIVATION CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ CRITICAL SKILLS (REQUIRED):
  → test-driven-development

📚 RECOMMENDED SKILLS:
  → writing-plans

ACTION: Use Skill tool BEFORE responding
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 2. post-tool-use-tracker (PostToolUse)
**Purpose:** Tracks file modifications across the codebase

**How it works:**
- Monitors Edit, Write, and MultiEdit operations
- Detects which part of the project was modified (backend/frontend)
- Builds a cache of affected files for potential build checks
- Skips markdown files automatically

## Enabling Hooks

Add this to your Claude Code settings (`~/.claude/settings.json`):

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/skill-activation-prompt.sh"
      }]
    }],
    "PostToolUse": [{
      "matcher": "Edit|MultiEdit|Write",
      "hooks": [{
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post-tool-use-tracker.sh"
      }]
    }]
  }
}
```

**Or add to project-specific settings (`.claude/settings.json`):**

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "./hooks/skill-activation-prompt.sh",
        "cwd": "$CLAUDE_PROJECT_DIR/.claude"
      }]
    }],
    "PostToolUse": [{
      "matcher": "Edit|MultiEdit|Write",
      "hooks": [{
        "type": "command",
        "command": "./hooks/post-tool-use-tracker.sh",
        "cwd": "$CLAUDE_PROJECT_DIR/.claude"
      }]
    }]
  }
}
```

## Customizing Skill Rules

Edit `.claude/skills/skill-rules.json` to customize when skills are suggested:

```json
{
  "skills": {
    "your-skill-name": {
      "type": "domain",           // or "guardrail"
      "enforcement": "suggest",   // or "warn", "block"
      "priority": "critical",     // or "high", "medium", "low"
      "promptTriggers": {
        "keywords": [              // Simple string matching
          "implement",
          "build feature"
        ],
        "intentPatterns": [        // Regex patterns
          "let'?s (implement|build)",
          "can you (add|create)"
        ]
      }
    }
  }
}
```

### Priority Levels
- **critical** → ⚠️ CRITICAL SKILLS (REQUIRED)
- **high** → 📚 RECOMMENDED SKILLS
- **medium** → 💡 SUGGESTED SKILLS
- **low** → 📌 OPTIONAL SKILLS

## Testing Hooks

Test the skill activation hook manually:

```bash
cd .claude/hooks
echo '{"prompt": "let'\''s implement a new feature", "cwd": "/project"}' | ./skill-activation-prompt.sh
```

## Troubleshooting

**Hook not running:**
- Check executable permissions: `ls -la .claude/hooks/*.sh`
- Run `chmod +x .claude/hooks/*.sh` if needed
- Verify settings.json syntax is valid JSON

**Dependencies missing:**
```bash
cd .claude/hooks
npm install
```

**Hook errors:**
- Check logs in Claude Code console
- Test hook manually with echo command above
- Verify skill-rules.json is valid JSON

## Files

- `skill-activation-prompt.sh` - Shell wrapper for TypeScript hook
- `skill-activation-prompt.ts` - Main skill activation logic
- `post-tool-use-tracker.sh` - File modification tracker
- `package.json` - Node.js dependencies (tsx, @types/node)
- `.claude/skills/skill-rules.json` - Skill trigger configuration

## Credits

Based on [claude-code-infrastructure-showcase](https://github.com/diet103/claude-code-infrastructure-showcase) by diet103.
