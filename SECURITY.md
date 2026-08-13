# Security policy

## Reporting a vulnerability

During private development, report suspected vulnerabilities to a repository
administrator through a previously established private channel. When the
repository becomes public, use its private vulnerability-reporting interface.

Do not open a public issue for an undisclosed vulnerability. Do not attach
genomic data, complete VCF rows, credentials, private paths, command histories,
or unsanitized headers. A useful minimal report contains:

- affected version or commit;
- input format and compression type;
- stable diagnostic or exception class;
- the smallest synthetic or sanitized reproducer;
- expected and observed behavior;
- security impact without exploit data that exposes a real subject.

## Supported versions

Published release notes will list supported versions. During pre-1.0
development, only the current default branch receives security fixes. No
pre-1.0 artifact should be treated as a long-term-supported release.

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
