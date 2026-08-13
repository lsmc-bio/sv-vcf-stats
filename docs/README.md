# Documentation

`vcf-sv-stats` documentation is split by decision, not by implementation
module. Start with the question you are trying to answer.

## I want to use the tool

| Question | Document |
|---|---|
| What problem does this solve? | [Project README](../README.md) |
| How do I install the public release wheel? | [Distribution guide](distribution.md#github-release-wheel) |
| How do I inspect, validate, summarize, or normalize a callset? | [Operator guide](operator-guide.md) |
| What commands and exit behaviors exist? | [Command reference](command-reference.md) |
| What does each output field mean? | [Output contract](output-contract.md) |
| How do I provide analysis context without guessing identity? | [Identity example](examples/identity-context.json) and [output contract](output-contract.md#analysis-context) |

## I want to understand the design

| Question | Document |
|---|---|
| Where are the trust boundaries and processing phases? | [Architecture](architecture.md) |
| What is normative and what is an implementation detail? | [Normative specification](specifications/vcf-sv-stats-1.0.0.md) |
| How are record, allele, breakend, event, and sample grains separated? | [Architecture: domain grains](architecture.md#domain-grains) |
| How does transactional normalization work? | [Architecture: publication protocol](architecture.md#publication-protocol) |
| How should an aggregate-report consumer ingest summaries? | [MultiQC integration](multiqc-integration.md) |

## I want to contribute or audit evidence

| Question | Document |
|---|---|
| Which checks should I run? | [Testing guide](testing.md) |
| What performance claims have executable evidence? | [Performance qualification](benchmarks/20260813_streaming_qualification.md) |
| Which installation targets and artifact proofs are required? | [Distribution guide](distribution.md) |
| What exactly is in the public installable release? | [1.0.1 release notes](releases/1.0.1.md) |
| What was retained from the private 1.0.0 candidate? | [1.0.0 release notes](releases/1.0.0.md) |
| How were the HG002 fixtures selected and sanitized? | [Fixture governance](fixture-governance.md) |
| Which acceptance criteria are complete? | [Implementation ledger](plans/20260813T065930Z_sv_vcf_stats_v1_implementation_ledger.md) |
| What contribution rules apply? | [Contributing guide](../CONTRIBUTING.md) |
| How should a vulnerability be reported? | [Security policy](../SECURITY.md) |

## Contract hierarchy

When documents disagree, use this order:

1. the current normative specification;
2. embedded schemas and the versioned `vcf_sv_stats.api.v1` interface;
3. the controlling implementation ledger;
4. operator and integration guides;
5. examples and narrative material.

Examples are executable documentation, not a second specification. Tests bind
the README showcase, identity sidecar, command catalog, adapter matrix, and
relative links to current implementation behavior.

## Stability labels

- **Stable identity** means a name or semantic boundary is versioned and may be
  consumed as documented during release-candidate qualification.
- **Supported** means fixture-backed interpretation exists for the named
  producer/version. It does not mean all transformations are enabled.
- **Provisional** means detection and diagnostics exist but rewrite is disabled.
- **Unsupported** means the identity is known but no native fixture has passed
  the support gate.
- **1.0 release** means the stable implementation target is complete. Public
  GitHub visibility and the uploaded wheel are release actions; registry and
  external-upstream publication remain separately controlled actions.

## Documentation checks

```bash
uv run pytest -q tests/test_documentation.py
uv run python tools/scan_tokens.py \
  --root . --policy policy/forbidden-token-hashes.json --git
uv run python tools/scan_tokens.py \
  --root . --policy policy/neutrality-token-hashes.json --structural \
  --source-github-repository lsmc-bio/sv-vcf-stats
```

The documentation test fails on broken relative links, stale fixture showcase
numbers, invalid example configuration, invalid identity context, missing CLI
commands, or adapter-matrix drift.
