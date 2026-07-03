# Rubric — archive-demo-repo-change (ac/siai#3)

Feature: archive the completed OpenSpec change `add-demo-repository` into
`openspec/changes/archive/2025-11-29-add-demo-repository/` via `git mv`,
with no file-content modifications.

## T1 — automated (evals/archive-demo-repo-change_eval.py)

- **AC1 — old directory gone**
  `test_old_change_directory_removed`
  Asserts `openspec/changes/add-demo-repository` no longer exists.

- **AC2 — archive directory exists with expected contents**
  `test_archived_change_directory_has_expected_contents`
  Asserts `openspec/changes/archive/2025-11-29-add-demo-repository/` is a
  directory containing `proposal.md`, `design.md`, `tasks.md`, and a
  `specs/` subdirectory.

- **AC3 — all 11 tasks checked**
  `test_archived_tasks_all_checked`
  Asserts `tasks.md` in the archived directory has exactly 11 lines
  matching `- [x]` and zero lines matching `- [ ]`.

## T2 — none

This repo declares no T2 tier (see AGENTS.md loop runbook); no T2 tests
were written.

## T3 — subjective / non-executable

- **Pure relocation, no content drift**
  The move must be a `git mv` (or content-preserving equivalent) — the
  archived `proposal.md`, `design.md`, `tasks.md`, and `specs/` files should
  be byte-identical to their pre-move versions. Verify with
  `git diff --stat` after the move showing only renames, no content hunks.

- **Naming matches the dated-archive convention**
  The archive directory name `2025-11-29-add-demo-repository` should read
  as consistent with siblings `2025-11-29-add-python-automation` and
  `2025-11-29-add-setup-wizard` (same completion era, same
  `<date>-<change-name>` pattern) — a human skim of
  `openspec/changes/archive/` should not flag this entry as out of place.

- **No stray references left behind**
  Any other doc/index that lists active OpenSpec changes (e.g. `docs/`
  index, ROADMAP) should not still point at the old
  `openspec/changes/add-demo-repository` path after the move — a quick
  grep for `add-demo-repository` outside the new archive path should turn
  up nothing surprising.
