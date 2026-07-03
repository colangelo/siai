"""Acceptance evals for backlog ac/siai#3: archive the completed OpenSpec
change `add-demo-repository` into `openspec/changes/archive/`.

Stdlib-only, file/structure-level — no network, no Docker (per repo runbook).
These evals describe the *future* state and MUST fail against the current,
unarchived tree.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OLD_CHANGE = REPO / "openspec" / "changes" / "add-demo-repository"
NEW_CHANGE = REPO / "openspec" / "changes" / "archive" / "2025-11-29-add-demo-repository"


def test_old_change_directory_removed():
    """AC1: the pre-archive location no longer exists."""
    assert not OLD_CHANGE.exists(), (
        f"{OLD_CHANGE} still exists — expected it to be moved into "
        f"openspec/changes/archive/"
    )


def test_archived_change_directory_has_expected_contents():
    """AC2: the dated archive directory exists with the standard change files."""
    assert NEW_CHANGE.is_dir(), f"{NEW_CHANGE} does not exist"
    for name in ("proposal.md", "design.md", "tasks.md"):
        assert (NEW_CHANGE / name).is_file(), f"{NEW_CHANGE / name} missing"
    assert (NEW_CHANGE / "specs").is_dir(), f"{NEW_CHANGE / 'specs'} missing"


def test_archived_tasks_all_checked():
    """AC3: tasks.md has exactly 11 checked tasks and none unchecked."""
    tasks_path = NEW_CHANGE / "tasks.md"
    assert tasks_path.is_file(), f"{tasks_path} missing"
    lines = tasks_path.read_text().splitlines()
    checked = [line for line in lines if re.match(r"^- \[x\]", line)]
    unchecked = [line for line in lines if re.match(r"^- \[ \]", line)]
    assert len(checked) == 11, f"expected 11 checked tasks, found {len(checked)}"
    assert not unchecked, f"found unchecked tasks: {unchecked}"
