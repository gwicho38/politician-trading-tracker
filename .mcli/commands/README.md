# MCLI Custom Workflows

This directory contains custom workflow commands for repository: politician-trading-tracker.

## Quick Start

### Create a New Workflow

```bash
# Python workflow
mcli workflow add my-workflow

# Shell workflow
mcli workflow add my-script --language shell
```

### List Workflows

```bash
mcli workflow list --custom-only
```

### Execute a Workflow

```bash
mcli workflows my-workflow
```

### Edit a Workflow

```bash
mcli workflow edit my-workflow
```

### Export/Import Workflows

```bash
# Export all workflows
mcli workflow export workflows-backup.json

# Import workflows
mcli workflow import workflows-backup.json
```

## Directory Structure

```
commands/
├── README.md              # This file
├── commands.lock.json     # Lockfile for workflow state
└── *.json                 # Individual workflow definitions
```

## Workflow Format

Workflows are stored as JSON files with the following structure:

```json
{
  "name": "workflow-name",
  "description": "Workflow description",
  "code": "Python or shell code",
  "language": "python",
  "group": "workflow",
  "version": "1.0",
  "created_at": "2025-10-30T...",
  "updated_at": "2025-10-30T..."
}
```

## Scope

- **Scope**: Local (repository-specific)
- **Location**: `/Users/lefv/repos/politician-trading-tracker/.mcli/commands`
- **Git Repository**: `/Users/lefv/repos/politician-trading-tracker`

## Documentation

- [MCLI Documentation](https://github.com/gwicho38/mcli)
- [Workflow Guide](https://github.com/gwicho38/mcli/blob/main/docs/features/LOCAL_VS_GLOBAL_COMMANDS.md)

---

*Initialized: 2025-10-30 16:41:38*
