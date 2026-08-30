# MultiQC producer integration

This document defines the boundary between `vcf-sv-stats` and its native
MultiQC consumer. The implementation and its neutral HG002 summary fixture are
merged in a maintained organization fork. Earlier public-upstream drafts were
closed without merge after the equivalent fork integration landed. Any future
external upstream proposal is a separately reviewed and approved action.

## Boundary

The consumer discovers only files named `*.vcf-sv-stats.json` with content
signature `vcf-sv-stats:summary:1`.

It does **not** read:

- VCF or BCF inputs;
- TBI or CSI indexes;
- transformation manifests or receipts;
- command logs, filenames, or directory structure as identity evidence.

This keeps aggregate reporting independent of HTSlib and prevents a reporting
layer from silently reinterpreting caller dialects.

## Prepare and render a native MultiQC report

Use an environment containing `vcf-sv-stats` and a maintained-fork MultiQC
release that registers the native module key `vcf_sv_stats`. Generate one
digest-bound summary for each callset, or for each explicit analysis-unit
grouping, and keep the required filename suffix:

```bash
mkdir -p results/vcf-sv-stats
vcf-sv-stats stats calls.vcf.gz \
  --output results/vcf-sv-stats/sample.vcf-sv-stats.json
```

Then point MultiQC at the containing results tree. Selecting the module
explicitly makes this a focused report run:

```bash
multiqc results/ \
  --module vcf_sv_stats \
  --outdir multiqc-report/
```

A normal all-module MultiQC scan can discover the same files automatically.
The native module writes `multiqc-report/multiqc_report.html` and exports its
parsed data as `multiqc-report/multiqc_data/multiqc_vcf_sv_stats.json`.

This is native module input, not MultiQC `custom_content`. Do not hand-edit,
reformat, or rename the summary after generation: the consumer requires the
`*.vcf-sv-stats.json` suffix and validates the schema, content signature, and
payload digest before displaying any value. One summary may contain multiple
`reports[]` entries; each becomes a deterministic MultiQC sample keyed by its
`report_id`.

## Executable reference contract

`vcf_sv_stats.multiqc.ingest_summaries` is the dependency-free producer-side
reference implementation. For every candidate path it:

1. requires the exact filename suffix;
2. parses JSON and rejects an unknown schema major;
3. validates the exact embedded schema when the version is `1.0.0`;
4. checks the content signature;
5. recomputes the canonical payload digest;
6. expands every `reports[]` entry into one immutable ingestion record;
7. sorts records deterministically by `report_id`.

The payload digest excludes only its own `payload_sha256` field and optional
execution metadata. Any other change invalidates the digest. This is an
integrity and determinism check, not proof of authorship.

## Identity and deduplication

Each report has two different identities:

| Field | Role |
|---|---|
| `report_id` | Stable compatibility key derived from callset digest and explicit analysis-unit ID. |
| `analysis_unit` | Authoritative generic context supplied by the producer sidecar. |
| `mapped_vcf_sample_ids` | Exact genotype-column mapping; never inferred. |
| `multiqc_sample` | Consumer compatibility key, deliberately equal to `report_id`. |

An identical report payload repeated under one `report_id` is deduplicated and
its additional source path is recorded. Different payloads under the same ID
are a hard conflict: neither version wins, and neither is silently renamed.

## Recommended display contract

A native module should present a compact callset overview without flattening
the statistical grains:

| Panel | Stable measures | Required caveat |
|---|---|---|
| Overview | resolved events, interpretable alleles, validation errors | Records, alleles, and events are not interchangeable. |
| SV spectrum | allele type and representation counts | Denominator is parsed alternate alleles. |
| Breakends | total, reciprocal pairs, orphan percentage | Pair resolution follows explicit graph evidence only. |
| Filters | PASS, missing, and filtered states | Denominator is source records. |
| Length | fixed `vss-bins/1` histogram | Missing, invalid, and not-applicable are separate. |
| Genotype/CN | genotype states, declared CN availability | Gain/loss is not inferred without an explicit baseline. |
| Provenance | producer, tested version, adapter status | Support is provenance, never accuracy. |
| Context | analysis-unit status and display ID | The compatibility key is not a biological identity. |

Every tooltip should state scope and denominator. A dashboard must not label
merged support counts as precision, recall, concordance, or truth evidence.

## Consumer pseudocode

```python
from pathlib import Path

from vcf_sv_stats.multiqc import ingest_summaries

paths = tuple(Path("results").glob("*.vcf-sv-stats.json"))
ingestion = ingest_summaries(paths)

for item in ingestion.records:
    report = item.report
    event_count = report["statistics"]["events"]["resolved"]
    add_report(item.multiqc_sample, event_count)
```

The native upstream implementation need not import this package. It must
reproduce the same discovery, schema, signature, digest, identity, conflict,
and deterministic-order behavior.

## Schema evolution

- Unknown major versions are rejected.
- A future compatible minor version may be accepted only through an explicit
  consumer policy; no best-effort field guessing is allowed.
- Unknown fields must not change the meaning of recognized metrics.
- A metric with a different scope, denominator, unit, or comparability group is
  a different metric even if its display label looks similar.

See the [output contract](output-contract.md) for exact artifact semantics.

## Maintained-fork boundary

The native module remains under the consumer project's license, review, typing,
snapshot, and strict-mode requirements. The maintained-fork implementation has
strict discovery and digest validation, deterministic conflict handling, 11
native report sections, focused tests, and a neutral fixture. Core
`vcf-sv-stats` code continues to provide the digest-bound producer artifact and
executable consumer-side reference contract without importing MultiQC.
