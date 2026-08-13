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


def test_archive_scanner_does_not_treat_compressed_bytes_as_text(tmp_path: Path) -> None:
    archive_path = tmp_path / "artifact.whl"
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("payload.txt", b"semantic archive content")
    archive_path.write_bytes(payload.getvalue())

    labels = [label for label, _data in scan_tokens._file_payloads(tmp_path, archive_path)]

    assert labels == ["artifact.whl!payload.txt"]


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


def test_github_administrative_exception_is_narrow() -> None:
    organization = b"hosting-org"
    policy = (_digest(organization),)
    runner_home = b"/" + b"home" + b"/runner"
    administrative = (
        b"repository hosting-org/project at "
        b"https://github.com/hosting-org/project under "
        + runner_home
        + b"/work/project"
    )
    normalized = scan_tokens.neutralize_github_administrative_context(
        "hosting-org/project",
        "github:workflow-log:7!test.txt",
        administrative,
    )

    assert not scan_tokens.contains_token(normalized, policy)
    assert not scan_tokens.contains_structural_marker(normalized)
    assert scan_tokens.contains_token(
        scan_tokens.neutralize_github_administrative_context(
            "hosting-org/project",
            "github:issues",
            b"product output names hosting-org without a repository coordinate",
        ),
        policy,
    )
    assert scan_tokens.contains_structural_marker(
        scan_tokens.neutralize_github_administrative_context(
            "hosting-org/project",
            "github:workflow-log:7!test.txt",
            b"product output names /" + b"mnt" + b"/private/output",
        )
    )


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
