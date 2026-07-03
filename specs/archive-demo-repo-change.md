# Archive the completed OpenSpec change add-demo-repository

## Description

Backlog issue ac/siai#3. The OpenSpec change `openspec/changes/add-demo-repository/`
(shipped as v0.3.4, all 11 tasks checked) was never archived. Move it into
`openspec/changes/archive/` following the existing dated-directory convention
(see `openspec/changes/archive/2025-11-29-add-python-automation/` and siblings):
the archive directory is named `<completion-date>-<change-name>`. This change
completed 2025-11-29 (same era as the two existing 2025-11-29 archives; ROADMAP
v0.3.4 ✅), so the target is
`openspec/changes/archive/2025-11-29-add-demo-repository/`. Use `git mv`; do not
modify any file contents — this is a pure relocation.

## Acceptance Criteria

- The directory `openspec/changes/add-demo-repository` no longer exists
- The directory `openspec/changes/archive/2025-11-29-add-demo-repository` exists and contains `proposal.md`, `design.md`, `tasks.md`, and a `specs/` subdirectory
- The file `openspec/changes/archive/2025-11-29-add-demo-repository/tasks.md` contains exactly 11 lines starting with `- [x]` and none starting with `- [ ]`
