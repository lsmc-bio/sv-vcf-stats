from __future__ import annotations

import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path
from typing import Any

from tools import scan_tokens


def _digest(value: bytes) -> scan_tokens.TokenDigest:
    return scan_tokens.TokenDigest(len(value), hashlib.sha256(value).digest())


def test_tree_scanner_reports_only_location_and_scans_archives(tmp_path: Path) -> None:
    token = b"private-marker"
    policy = (_digest(token),)
    archive_path = tmp_path / "artifact.whl"
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("payload.txt", b"prefix " + token.upper() + b" suffix")
    archive_path.write_bytes(payload.getvalue())

    findings = scan_tokens.scan_tree(tmp_path, policy, structural=False)

    assert findings == {"content:artifact.whl!payload.txt"}
    assert all(token.decode() not in finding for finding in findings)


def test_tree_scanner_expands_nested_container_layers(tmp_path: Path) -> None:
    token = b"nested-marker"
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("installed.txt", token)
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("layer.zip", inner.getvalue())
    (tmp_path / "container.tar").write_bytes(outer.getvalue())

    findings = scan_tokens.scan_tree(tmp_path, (_digest(token),), structural=False)

    assert "content:container.tar!layer.zip!installed.txt" in findings


def test_github_scanner_includes_completed_workflow_logs(
    monkeypatch: Any,
) -> None:
    log_archive = io.BytesIO()
    with zipfile.ZipFile(log_archive, "w") as archive:
        archive.writestr("test.txt", "neutral workflow output")

    def fake_json(_repository: str, endpoint: str) -> Any:
        if endpoint == "":
            return {"name": "repo", "description": None, "homepage": None, "topics": []}
        if endpoint.startswith("actions/workflows"):
            return {"workflows": []}
        if endpoint.startswith("actions/runs"):
            return {
                "workflow_runs": [
                    {"id": 7, "status": "completed", "name": "CI", "head_branch": "main"}
                ]
            }
        return [] if endpoint.startswith(("issues", "pulls", "releases")) else {}

    monkeypatch.setattr(scan_tokens, "_gh_json", fake_json)
    monkeypatch.setattr(
        scan_tokens,
        "_gh_bytes",
        lambda _repository, _endpoint: log_archive.getvalue(),
    )

    payloads = scan_tokens.github_text("owner/repo")

    assert payloads["github:workflow-log:7!test.txt"] == b"neutral workflow output"


def test_github_json_handles_root_endpoint_and_flattens_pages(monkeypatch: Any) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(args: tuple[str, ...], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=json.dumps([[{"id": 1}], [{"id": 2}]]).encode(),
            stderr=b"",
        )

    monkeypatch.setattr(scan_tokens.subprocess, "run", fake_run)

    assert scan_tokens._gh_json("owner/repository", "issues") == [{"id": 1}, {"id": 2}]
    assert calls[0][-1] == "repos/owner/repository/issues"

    calls.clear()
    monkeypatch.setattr(
        scan_tokens.subprocess,
        "run",
        lambda args, **_kwargs: subprocess.CompletedProcess(
            args,
            0,
            stdout=json.dumps([{"name": "repository"}]).encode(),
            stderr=b"",
        ),
    )
    assert scan_tokens._gh_json("owner/repository", "") == {"name": "repository"}
