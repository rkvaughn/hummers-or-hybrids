# Claude Skills & Config Transfer Package

## What's Inside:

### 1. global-skills/
Your personal skills from ~/.claude/skills/
- These go in ~/.claude/skills/ on the new machine
- Available across ALL repos

### 2. project-claude/
Zephyr's .claude/ folder contents
- These go in .claude/ folder in the new repo
- Project-specific configuration

## How to Use:

### Install Global Skills (on new machine):
```bash
# Copy skills to home directory
cp -r global-skills/* ~/.claude/skills/
```

### Install Project Config (in new repo):
```bash
# Copy to your new repo's .claude folder
mkdir -p .claude
cp -r project-claude/* .claude/
git add .claude
git commit -m "feat: add Claude configuration from Zephyr"
```

## What's Included:

**Global Skills (available everywhere):**
$(ls -1 global-skills/)

**Project Configuration:**
$(ls -1 project-claude/)

Created: $(date)
