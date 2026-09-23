---
name: new-branch
description: Create a new git branch that encodes the course/delivery session number. Use when creating a branch, starting a new feature, starting session N work, or beginning a new deliverable.
author: LIDR.co
version: 1.0.0
---
# new-branch Skill

Use when creating a new git branch for a feature, fix, or deliverable in this repository.

## Instructions

# Role

You create git branches that follow the project branch-naming contract so every deliverable is traceable to its course/delivery session.

# Arguments

**Optional.** `$ARGUMENTS` may contain:

- A session number (e.g. `2`, `session 2`, `session-2`)
- A short deliverable description used as the slug (e.g. `streamlit chat ui`)
- A branch type (`feature`, `fix`, `chore`, `docs`, `refactor`); default is `feature`
- Combinations of the above (e.g. `session 2 streamlit chat ui`)

# Goal

1. Resolve a confirmed session number (never invent one).
2. Build a branch name matching `<type>/session-<N>-<slug>`.
3. Create the branch from an up-to-date `main`.
4. Report the created branch and the session number it encodes.

# Process and rules

## 1. Resolve session number

- If `$ARGUMENTS` or the user message clearly includes a session number, use it.
- Otherwise:
  1. Run `git branch -a` and collect all matches of `session-<N>`.
  2. Propose the highest known `N` (or `N+1` if the user said "next session") to the user.
  3. **Stop and ask for confirmation.** Do not create the branch until the user confirms.
- **Never guess.** If no session number is available and the user has not confirmed a proposal, stop.

## 2. Resolve type and slug

- `<type>`: from arguments or context; default `feature`. Allowed: `feature`, `fix`, `chore`, `docs`, `refactor`.
- `<slug>`: lowercase kebab-case from the deliverable description (e.g. `Streamlit Chat UI` → `streamlit-chat-ui`).
- Frontend parallel work may append `-frontend` to the slug when applicable.
- Final name: `<type>/session-<N>-<slug>` (example: `feature/session-2-streamlit-chat-ui`).

## 3. Preconditions and create

1. Ensure the working tree is clean (`git status`). If it is not, report the dirty state and ask how to proceed; do not create the branch over uncommitted work unless the user explicitly allows it.
2. Check out `main` and update it (`git checkout main` then `git pull` if a remote exists).
3. Create and switch to the new branch: `git checkout -b <type>/session-<N>-<slug>`.
4. If a branch with that name already exists, stop and report it; do not overwrite.

## 4. Report

Tell the user:
- The branch name created
- The session number encoded
- That they are now on that branch

# References

- `docs/base-standards.md` section 8: Branch Naming and Session Numbering (authoritative contract)
- `ai-specs/skills/commit/SKILL.md`: validates branch names before commit/push and includes session in PR titles

# Notes

- `main` is exempt from the session naming contract; never rename `main`.
- Do not rename existing legacy branches that predate this rule.
- Do not force-push or run destructive git commands.
