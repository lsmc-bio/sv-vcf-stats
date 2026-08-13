#!/usr/bin/env python3
"""Scan files, archives, Git objects, and repository-facing text using hashed tokens."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pysam

SKIP_PARTS = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__"}
SKIP_NAMES = {".coverage"}
STRUCTURAL_PATTERNS = (
    re.compile(rb"(?i)(?:s3|ssh|git\+ssh)://"),
    re.compile(rb"(?i)(?:^|[\s\"'])(?:/users|/home|/mnt|/scratch)/"),
    re.compile(rb"(?i)git@[a-z0-9.-]+:"),
)
TOKEN_CANDIDATE = re.compile(rb"[a-z0-9._@:/+\-]+")


@dataclass(frozen=True, slots=True)
class TokenDigest:
    length: int
    sha256: bytes


def load_policy(path: Path) -> tuple[TokenDigest, ...]:
    value = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if value.get("schema_version") != 1 or not isinstance(value.get("tokens"), list):
        raise ValueError(f"Invalid token policy: {path}")
    tokens = tuple(
        TokenDigest(int(item["length"]), bytes.fromhex(str(item["sha256"])))
        for item in value["tokens"]
    )
    if any(token.length < 1 or len(token.sha256) != 32 for token in tokens):
        raise ValueError(f"Invalid token policy entry: {path}")
    return tokens


def contains_token(data: bytes, tokens: tuple[TokenDigest, ...]) -> bool:
    folded = data.lower()
    digests_by_length: dict[int, set[bytes]] = {}
    for token in tokens:
        digests_by_length.setdefault(token.length, set()).add(token.sha256)
    for match in TOKEN_CANDIDATE.finditer(folded):
        candidate = match.group()
        for length, digests in digests_by_length.items():
            for start in range(0, len(candidate) - length + 1):
                if hashlib.sha256(candidate[start : start + length]).digest() in digests:
                    return True
    return False


def contains_structural_marker(data: bytes) -> bool:
    return any(pattern.search(data) for pattern in STRUCTURAL_PATTERNS)


def _archive_members(label: str, data: bytes) -> Iterator[tuple[str, bytes]]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for name in archive.namelist():
                if not name.endswith("/"):
                    yield f"{label}!{name}", archive.read(name)
            return
    except zipfile.BadZipFile:
        pass
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            for member in archive.getmembers():
                if member.isfile():
                    handle = archive.extractfile(member)
                    if handle is not None:
                        yield f"{label}!{member.name}", handle.read()
            return
    except tarfile.TarError:
        pass
    try:
        yield f"{label}!decompressed", gzip.decompress(data)
    except (gzip.BadGzipFile, EOFError, OSError):
        return


def _expanded_archive_members(
    label: str,
    data: bytes,
    *,
    depth: int = 0,
) -> Iterator[tuple[str, bytes]]:
    if depth >= 4:
        return
    for member_label, member_data in _archive_members(label, data):
        yield member_label, member_data
        yield from _expanded_archive_members(member_label, member_data, depth=depth + 1)


def _file_payloads(root: Path, path: Path) -> Iterator[tuple[str, bytes]]:
    label = str(path.relative_to(root))
    data = path.read_bytes()
    yield label, data
    if path.suffix == ".bcf":
        with pysam.VariantFile(str(path)) as variant:
            rendered = str(variant.header) + "".join(str(record) for record in variant)
        yield f"{label}!decoded", rendered.encode()
    if path.suffix in {".gz", ".tgz", ".zip", ".whl"} or ".tar" in path.name:
        yield from _expanded_archive_members(label, data)


def scan_tree(
    root: Path,
    tokens: tuple[TokenDigest, ...],
    *,
    structural: bool,
) -> set[str]:
    findings: set[str] = set()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        if path.name in SKIP_NAMES:
            continue
        label = str(relative)
        encoded_label = label.encode()
        if contains_token(encoded_label, tokens) or (
            structural and contains_structural_marker(encoded_label)
        ):
            findings.add(f"filename:{label}")
        if not path.is_file():
            continue
        for payload_label, data in _file_payloads(root, path):
            if contains_token(data, tokens) or (structural and contains_structural_marker(data)):
                findings.add(f"content:{payload_label}")
    return findings


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(("git", "-C", str(root), *args), check=True, capture_output=True)
    return result.stdout


def scan_git(root: Path, tokens: tuple[TokenDigest, ...], *, structural: bool) -> set[str]:
    findings: set[str] = set()
    refs = _git(root, "for-each-ref", "--format=%(refname)")
    messages = _git(root, "log", "--all", "--format=%H%x00%B")
    for label, payload in (("git:refs", refs), ("git:messages", messages)):
        if contains_token(payload, tokens) or (structural and contains_structural_marker(payload)):
            findings.add(label)
    object_lines = _git(root, "rev-list", "--objects", "--all").decode().splitlines()
    for line in object_lines:
        object_id, _, name = line.partition(" ")
        if name:
            name_bytes = name.encode()
            if contains_token(name_bytes, tokens) or (
                structural and contains_structural_marker(name_bytes)
            ):
                findings.add(f"git:filename:{name}")
        payload = _git(root, "cat-file", "-p", object_id)
        object_label = f"git:object:{name or object_id}"
        object_payloads = [(object_label, payload)]
        if name:
            object_payloads.extend(_expanded_archive_members(object_label, payload))
        for payload_label, object_payload in object_payloads:
            if contains_token(object_payload, tokens) or (
                structural and contains_structural_marker(object_payload)
            ):
                findings.add(payload_label)
    return findings


def _gh_json(repository: str, endpoint: str) -> Any:
    target = f"repos/{repository}" + (f"/{endpoint}" if endpoint else "")
    result = subprocess.run(
        ("gh", "api", "--paginate", "--slurp", target),
        check=True,
        capture_output=True,
    )
    pages = cast(list[Any], json.loads(result.stdout))
    if len(pages) == 1:
        return pages[0]
    if all(isinstance(page, list) for page in pages):
        return [item for page in pages for item in page]
    if all(isinstance(page, dict) for page in pages):
        merged = dict(pages[0])
        for key, value in tuple(merged.items()):
            if isinstance(value, list):
                merged[key] = [
                    item
                    for page in pages
                    for item in page.get(key, [])
                    if isinstance(page.get(key), list)
                ]
        return merged
    raise ValueError(f"Unexpected GitHub pagination result for {endpoint or 'repository'}")


def _gh_bytes(repository: str, endpoint: str) -> bytes:
    target = f"repos/{repository}" + (f"/{endpoint}" if endpoint else "")
    result = subprocess.run(
        ("gh", "api", target),
        check=True,
        capture_output=True,
    )
    return result.stdout


def _collect_fields(values: Iterable[dict[str, Any]], fields: tuple[str, ...]) -> list[str]:
    return [
        str(value[field]) for value in values for field in fields if value.get(field) is not None
    ]


def github_text(repository: str) -> dict[str, bytes]:
    repo = cast(dict[str, Any], _gh_json(repository, ""))
    issues = cast(list[dict[str, Any]], _gh_json(repository, "issues?state=all&per_page=100"))
    pulls = cast(list[dict[str, Any]], _gh_json(repository, "pulls?state=all&per_page=100"))
    releases = cast(list[dict[str, Any]], _gh_json(repository, "releases?per_page=100"))
    workflows_value = cast(dict[str, Any], _gh_json(repository, "actions/workflows?per_page=100"))
    runs_value = cast(dict[str, Any], _gh_json(repository, "actions/runs?per_page=100"))
    payloads = {
        "github:repository-metadata": json.dumps(
            {key: repo.get(key) for key in ("name", "description", "homepage", "topics")},
            sort_keys=True,
        ).encode(),
        "github:issues": "\n".join(_collect_fields(issues, ("title", "body"))).encode(),
        "github:pull-requests": "\n".join(_collect_fields(pulls, ("title", "body"))).encode(),
        "github:releases": "\n".join(
            _collect_fields(releases, ("name", "tag_name", "body"))
        ).encode(),
        "github:workflows": "\n".join(
            _collect_fields(workflows_value.get("workflows", []), ("name", "path"))
        ).encode(),
        "github:workflow-runs": "\n".join(
            _collect_fields(
                runs_value.get("workflow_runs", []),
                ("name", "display_title", "event", "head_branch"),
            )
        ).encode(),
    }
    for run in runs_value.get("workflow_runs", []):
        if run.get("status") != "completed" or not isinstance(run.get("id"), int):
            continue
        run_id = int(run["id"])
        archive = _gh_bytes(repository, f"actions/runs/{run_id}/logs")
        for label, data in _archive_members(f"github:workflow-log:{run_id}", archive):
            payloads[label] = data
    return payloads


def neutralize_github_administrative_context(
    repository: str,
    label: str,
    payload: bytes,
) -> bytes:
    """Remove only provider-owned coordinates from GitHub-facing scan input."""

    owner, separator, name = repository.partition("/")
    if not separator or not owner or not name or "/" in name:
        raise ValueError("GitHub repository must use the owner/name form")
    normalized = re.sub(
        re.escape(repository.encode()),
        b"{github-repository}",
        payload,
        flags=re.IGNORECASE,
    )
    if label.startswith("github:workflow-log:"):
        normalized = re.sub(
            rb"(?i)/home/runner(?=$|[/\s\"'])",
            b"/github-runner",
            normalized,
        )
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--git", action="store_true")
    parser.add_argument("--github-repository")
    parser.add_argument("--github-administrative-exception", action="store_true")
    parser.add_argument("--structural", action="store_true")
    args = parser.parse_args()
    if args.github_administrative_exception and not args.github_repository:
        parser.error("--github-administrative-exception requires --github-repository")
    root = args.root.resolve(strict=True)
    tokens = load_policy(args.policy.resolve(strict=True))
    findings = scan_tree(root, tokens, structural=args.structural)
    if args.git:
        findings.update(scan_git(root, tokens, structural=args.structural))
    if args.github_repository:
        for label, payload in github_text(args.github_repository).items():
            scan_payload = (
                neutralize_github_administrative_context(
                    args.github_repository,
                    label,
                    payload,
                )
                if args.github_administrative_exception
                else payload
            )
            if contains_token(scan_payload, tokens) or (
                args.structural and contains_structural_marker(scan_payload)
            ):
                findings.add(label)
    if findings:
        print("\n".join(sorted(findings)))
        raise SystemExit(1)
    print(json.dumps({"status": "pass", "findings": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
