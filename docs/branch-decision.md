# ST-008 Branch naming decision

Status: Accepted
Date: 2026-04-19

## Decision

Keep the current default branch (`master`) unchanged for now.

## Rationale

- Active work is already happening on `feat/main-structure` and branch rename would add
  coordination overhead during ongoing task delivery.
- No remote-protection policy has been finalized yet, so renaming now could require repeated
  migration work (local clones, CI references, docs links).
- The team can revisit renaming to `main` when repository hosting and protection rules are stable.

## Follow-up trigger

Re-open this decision when remote branch protections and CI default-branch assumptions are in place.
