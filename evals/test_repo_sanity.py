"""Standing sanity checks for the repo (run by `just test`).

Stdlib-only, file/structure-level — no network, no Docker, no live stack
(the second-loop gate runs unattended). Frozen second-loop evals land in
this directory too, so the gate re-runs them.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
RESERVED = {"index.md", "log.md"}


def test_docs_index_exists():
    assert (DOCS / "index.md").is_file(), "docs/index.md missing — run `just docs-index`"


def test_every_doc_has_frontmatter():
    missing = [
        p.name
        for p in DOCS.glob("*.md")
        if p.name not in RESERVED and not p.read_text().startswith("---\n")
    ]
    assert not missing, f"docs without YAML frontmatter: {missing}"


def test_compose_files_parse():
    """Compose files are valid YAML with a services map (structure only —
    `just compose-check` does the full `docker compose config` validation)."""
    yaml = __import__("yaml")
    for name in [
        "docker-compose.yml",
        "docker-compose.harbor.yml",
        "docker-compose.homelab.yml",
        "docker-compose.homelab.smoke.yml",
    ]:
        path = REPO / name
        assert path.is_file(), f"{name} missing"
        # The homelab override uses compose-specific `!reset`/`!override` tags
        # (on scalars, sequences, and mappings); register pass-through
        # constructors so the structural parse succeeds.
        class ComposeLoader(yaml.SafeLoader):
            pass

        def construct_tagged(ldr, node):
            if isinstance(node, yaml.SequenceNode):
                return ldr.construct_sequence(node)
            if isinstance(node, yaml.MappingNode):
                return ldr.construct_mapping(node)
            return ldr.construct_scalar(node) or None

        for tag in ("!reset", "!override"):
            ComposeLoader.add_constructor(tag, construct_tagged)
        data = yaml.load(path.read_text(), Loader=ComposeLoader)
        assert isinstance(data.get("services"), dict), f"{name}: no services map"


def test_scripts_are_pep723():
    """Every automation script declares PEP 723 metadata (house rule)."""
    missing = [
        p.name
        for p in (REPO / "scripts").glob("*.py")
        if "# /// script" not in p.read_text()
    ]
    assert not missing, f"scripts without PEP 723 metadata: {missing}"


def test_gitea_rootless_volume_paths():
    """Regression: rootless Gitea stores data in /var/lib/gitea and config in
    /etc/gitea — a bare /data mount is inert, leaving repos in the container
    layer where any recreate wipes them (hit locally 2026-07-04; same bug
    previously hit on the homelab, see docker-compose.homelab.yml)."""
    text = (REPO / "docker-compose.yml").read_text()
    assert "gitea-data:/var/lib/gitea" in text
    assert "gitea-config:/etc/gitea" in text
    assert "gitea-data:/data" not in text


def test_homelab_keeps_force_ignore_service_failure():
    """Regression: WOODPECKER_FORCE_IGNORE_SERVICE_FAILURE must stay in the
    homelab wpk-server env (relay ask 2026-06-19; a redeploy without it breaks
    direction's parity-eval green icons)."""
    text = (REPO / "docker-compose.homelab.yml").read_text()
    assert re.search(r"WOODPECKER_FORCE_IGNORE_SERVICE_FAILURE=true", text)
