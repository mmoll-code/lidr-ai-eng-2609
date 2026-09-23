---
description: This document contains all development rules and guidelines for this project, applicable to all AI agents (Claude, Cursor, Codex, Gemini, etc.).
alwaysApply: true
---

## 1. Core Principles

- **Small tasks, one at a time**: Always work in baby steps, one at a time. Never go forward more than one step.
- **Test-Driven Development**: Start with failing tests for any new functionality (TDD), according to the task details.
- **Type Safety**: All code must be fully typed.
- **Clear Naming**: Use clear, descriptive names for all variables and functions.
- **Incremental Changes**: Prefer incremental, focused changes over large, complex modifications.
- **Question Assumptions**: Always question assumptions and inferences.
- **Pattern Detection**: Detect and highlight repeated code patterns.

## 2. Language Standards
- **English Only**: All technical artifacts must always use English, including:
    - Code (variables, functions, classes, comments, error messages, log messages)
    - Documentation (README, guides, API docs)
    - Jira tickets (titles, descriptions, comments)
    - Data schemas and database names
    - Configuration files and scripts
    - Git commit messages
    - Test names and descriptions

## 3. Specific standards

For detailed standards and guidelines specific to different areas of the project, refer to:

- [Backend Standards](./backend-standards.md) - FastAPI development, PostgreSQL patterns, testing (pytest), security and backend best practices
- [Frontend Standards](./frontend-standards.md) - Next.js (React, TypeScript) components, UI/UX guidelines, and frontend architecture
- [Documentation Standards](./documentation-standards.md) - Technical documentation structure, formatting, and maintenance guidelines, including AI standards like this document
- [OpenSpec Tasks Mandatory Steps](./openspec-tasks-mandatory-steps.md) - Required checklist and execution rules when creating or updating OpenSpec `tasks.md` files

## 4. Project Skills

- Skills live in `ai-specs/skills`.
- When a request matches a skill, load and follow the corresponding `SKILL.md` automatically before continuing.
- Also load any referenced files in the skill folder (for example, `references/*.md`) when the skill requires them.

## 5. Planning Model Requirement

Planning workflows must run with Opus high reasoning.

This requirement applies to:
- `enrich-us`
- `openspec-ff-change`
- `openspec-continue-change`

Before starting any of these workflows, verify the session is using Opus high reasoning. If it is not, **self-correct** by adding `"model": "claude-opus-4-7"` to `.claude/settings.json` (use the `update-config` skill or edit directly), then continue — do not stop and ask the user. Do the same to come back to sonnet medium for any other step.

## 6. Symlink Integrity and Multi-Agent Portability

- **Canonical Source**: Keep reusable artifacts in `ai-specs` as the canonical source. Agent-specific paths (such as `.claude` and `.cursor`) should reference them through symlinks when possible.
- **Update Safety**: Whenever a file is renamed, moved, or its suffix changes, verify and update all symlinks that target it before considering the change complete.
- **New Artifact Linking**: Whenever creating a new artifact that requires multi-agent exposure (for example new agents or skills in `ai-specs`), create the corresponding symlinks from the expected agent-specific reference paths.
- **External Customization Review**: Whenever customization is introduced outside `ai-specs`, evaluate whether it should be moved into `ai-specs` and replaced with symlinks from the original locations.
- **Completion Gate**: A change is incomplete if it leaves broken symlinks, stale targets, or duplicated canonical artifacts across agent-specific folders.

## 7. Mandatory OpenSpec Artifact Updates for Post-Apply Changes

When a new fix/change request appears after `opsx:apply` (or `/apply`) and before `opsx:archive` (or `/archive`), agents must treat it as a spec update first, not as an informal "fix this quickly". It's the core principle of openspec, documentation is the source of truth.

Required order:

1. Update the current OpenSpec change artifacts that are affected (for example: scenarios, requirements/specs, and `tasks.md`). Don't add tasks as "bugfixes" but as part of the initial design, thus in the proper section
2. If artifact regeneration is needed, run the corresponding OpenSpec step (`opsx:continue`, `opsx:ff`, or equivalent) before coding.
3. Implement code only after artifacts reflect the new request.
4. Re-run verification against the updated artifacts before archiving.

Do not apply direct code-only fixes in this window without updating OpenSpec artifacts.

## 8. Branch Naming and Session Numbering

Every new branch created in this repository must encode the course/delivery **session number** for the feature or deliverable being worked on.

### Naming contract

- Pattern: `<type>/session-<N>-<slug>`
- `<type>` is one of: `feature` (default), `fix`, `chore`, `docs`, `refactor`
- `<N>` is the session number as a plain integer with no zero padding (e.g. `2`, not `02`)
- `<slug>` is a lowercase kebab-case description of the deliverable
- Example: `feature/session-2-streamlit-chat-ui`
- Frontend parallel work may append `-frontend` to the slug: `feature/session-2-chat-ui-frontend`

### Rules

- **Never guess the session number.** It must come from the user's request, or the agent may scan existing `session-<N>` branches, propose the highest known number (or next), and ask the user to confirm before creating the branch.
- `main` is exempt from this naming contract.
- Existing legacy branches (created before this rule) are not renamed; the rule applies to **newly created** branches only.
- When creating a branch, use the `new-branch` skill.
- When committing or opening a PR, the `commit` skill validates the branch name and includes the session number in the PR title (e.g. `[Session 2] Add Streamlit chat UI`).

