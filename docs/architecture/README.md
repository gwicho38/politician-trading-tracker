# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) documenting significant
technical decisions made in the Politician Trading Tracker project.

## What is an ADR?

An ADR is a document that captures an important architectural decision along with
its context and consequences. ADRs help:

- Document the "why" behind technical decisions
- Onboard new contributors faster
- Avoid revisiting decisions without new information
- Track the evolution of the architecture

## ADR Index

| ID | Title | Status | Date |
|----|-------|--------|------|
| 001 | [Async-First Architecture](001-async-first-architecture.md) | Accepted | 2024-12 |
| 002 | [Supabase as Backend](002-supabase-backend.md) | Accepted | 2024-12 |
| 003 | [Scraper Module Organization](003-scraper-organization.md) | Proposed | 2024-12 |
| 004 | [Streamlit UI Structure](004-streamlit-ui-structure.md) | Proposed | 2024-12 |
| 005 | [Error Handling Strategy](005-error-handling.md) | Accepted | 2024-12 |

## ADR Status Lifecycle

- **Proposed**: Under discussion, not yet accepted
- **Accepted**: Decision has been made and is in effect
- **Deprecated**: Decision is no longer relevant
- **Superseded**: Replaced by a newer ADR

## Template

Use the following template for new ADRs:

```markdown
# ADR-NNN: Title

## Status
Proposed | Accepted | Deprecated | Superseded by ADR-XXX

## Context
What is the issue we're addressing?

## Decision
What is the change we're proposing/making?

## Consequences
What are the positive and negative effects?
```
