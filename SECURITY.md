# Security policy

## Reporting a vulnerability

Use this public repository's private vulnerability-reporting interface for
suspected vulnerabilities. If that interface is temporarily unavailable during
the visibility transition, report through a previously established private
maintainer channel.

Do not open a public issue for an undisclosed vulnerability. Do not attach
genomic data, complete VCF rows, credentials, private paths, command histories,
or unsanitized headers. A useful minimal report contains:

- affected version or commit;
- input format and compression type;
- stable diagnostic or exception class;
- the smallest synthetic or sanitized reproducer;
- expected and observed behavior;
- security impact without exploit data that exposes a real subject.

## Visibility-transition gate

The authenticated private-vulnerability-reporting status endpoint returned
`404` while this repository was non-public on 2026-08-13. That was the
pre-release platform boundary, not evidence that reporting was enabled.

Immediately after the explicitly approved public-visibility change, an
administrator must enable the feature and read it back before the public
GitHub release or announcement. An annotated tag and private Actions
qualification may precede the visibility change:

```bash
gh api --method PUT repos/OWNER/REPOSITORY/private-vulnerability-reporting
gh api repos/OWNER/REPOSITORY/private-vulnerability-reporting --jq '.enabled'
```

The second command must return `true`. A failed or unavailable read-back blocks
the release; a public issue is not an acceptable substitute for a confidential
reporting path.

## Supported versions

The latest published 1.x release and current default branch receive security
fixes. Historical candidate artifacts should not be treated as supported
installation releases.

## Security-relevant boundaries

- Runtime inputs are local files or standard input.
- The tool performs no telemetry and no remote input discovery.
- The only network-capable operation is an explicit, confirmed retrieval of a
  pinned public reference profile.
- Input size and decompression limits guard materialization.
- Strict YAML rejects duplicate and unknown configuration keys.
- Diagnostics redact raw values and report field names or record ordinals.
- Output publication is staged and receipt-bound; partial artifact sets are not
  valid completion markers.
- Input/output aliases and unsafe force-replacement targets are rejected.

These controls reduce risk but do not make genomic data non-sensitive. Operators
remain responsible for filesystem permissions, temporary-directory policy,
retention, and access to produced artifacts.

## Coordinated handling

Please allow maintainers to reproduce and assess the report before public
disclosure. A fix should include a regression test and, when relevant, an
advisory, release note, and rotated stable identifier. Credit is offered unless
the reporter prefers anonymity.
