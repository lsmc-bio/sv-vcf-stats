# Output contract

This guide describes how to consume `vcf-sv-stats` artifacts without reopening
the source VCF. The embedded schemas remain authoritative for exact structural
validation; the [normative specification](specifications/vcf-sv-stats-1.0.0.md)
defines semantics.

## Summary envelope

A summary is a UTF-8 JSON object with:

| Field | Meaning |
|---|---|
| `schema_name` | `vcf-sv-stats.summary` |
| `schema_version` | Exact artifact schema version |
| `content_signature` | `vcf-sv-stats:summary:1` |
| `producer` | Tool name and implementation version |
| `input` | Container, safe display name, completeness, size, and SHA-256 |
| `callset` | Input grain, exact sample columns, producer evidence, and callset ID |
| `validation` | State axes and diagnostic counts |
| `statistics` | Callset-level descriptive metrics and metric contracts |
| `reports` | One record per unresolved or explicitly mapped analysis unit |
| `payload_sha256` | RFC 8785 digest of the object without this field |

Consumers MUST validate the supported schema major, exact embedded schema,
content signature, and payload digest before using statistics. A filename alone
is not sufficient discovery evidence.

`content_signature` is a format discriminator, not a digital signature. The
payload digest detects change and enables deterministic deduplication; by
itself, it does not authenticate who produced the artifact. Authenticity needs
an external signing or attestation system outside this contract.

## Metric contracts

Each stable metric family includes a contract with:

- `scope`: the grain being counted;
- `denominator`: the included population;
- `unit`: records, alleles, breakends, events, sample calls, or base pairs;
- `comparability`: the versioned policy needed for cross-report comparison.

For example, event counts use `event-resolution/1`, while length histograms use
`vss-bins/1`. Reports with different comparability identities must not be merged
as though their values were defined identically.

## Validation states

The summary reports these state axes independently:

| State | Question answered |
|---|---|
| `container_state` | Was the byte container recognized and accepted? |
| `parse_state` | Did records parse through the selected reader? |
| `vcf_conformance_state` | Did declarations and cardinalities conform? |
| `sv_semantic_state` | Were declared types and SV representations consistent? |
| `operation_safety_state` | Is the requested operation safe? |
| `statistics_state` | Are statistics complete for the selected input? |

Do not collapse these into a single “valid VCF” boolean. A parseable input can
be nonconformant; a statistically reportable callset can still be unsafe to
normalize.

## Statistics grains

| Path | Grain | Important interpretation rule |
|---|---|---|
| `source_records` | VCF rows | Not a universal variant count |
| `alleles` | ALT alleles | Multiallelic rows contribute more than one |
| `breakends` | Junction endpoints | Includes reciprocal and unresolved endpoints |
| `events` | Resolved events | Never inferred from missing relationship evidence |
| `genotypes` | VCF sample calls | Preserves no-call, ploidy, and phase states |
| `copy_number` | Declared CN calls | Not automatically gain/loss/neutral |
| `length_bp` | Applicable ALT alleles | Missing and not-applicable are not zero |
| `filters` | Source rows | Multiple filter labels can coexist |
| `qual` | Source rows with declared QUAL | Uses a separately labeled distribution |
| `merged_support` | Merged ALT alleles | Provenance support only; not concordance or truth |

## Histograms

`vss-bins/1` defines half-open length bins:

```text
[0,50) [50,100) [100,500) [500,1000) [1000,5000)
[5000,10000) [10000,50000) [50000,100000)
[100000,1000000) [1000000,10000000) [10000000,+inf)
```

Histogram consumers should reconcile `sum(counts)` with `n` and retain
`missing`, `invalid`, and `not_applicable` as separate values. Non-finite JSON
numbers are prohibited.

## Analysis context

A VCF sample column is not an analysis identity. Without an identity sidecar,
statistics still succeed and `analysis_unit.status` is `unresolved`.

An identity sidecar uses generic fields only:

```json
{
  "schema_name": "vcf-sv-stats.identity",
  "schema_version": "1.0.0",
  "analysis_units": [
    {
      "analysis_unit_id": "analysis-001",
      "display_id": "HG002 demonstration",
      "algorithm_id": "manta-1.6.0",
      "mapped_vcf_sample_ids": ["HG002"],
      "external_identifiers": [
        {"namespace": "study", "value": "example-study"}
      ]
    }
  ]
}
```

The executable version is [examples/identity-context.json](examples/identity-context.json).
Mappings must name exact VCF sample columns. Filenames and directories never
resolve identity. Distinct analysis units remain distinct even when they map to
the same genotype column.

## Diagnostics

Every diagnostic contains a stable code plus:

- severity and category;
- privacy-safe location where available;
- implicated field and specification reference;
- fixability classification;
- statistics and normalization blockers;
- adapter/version evidence where relevant.

Diagnostics intentionally omit raw ALT alleles, genotypes, command lines, and
absolute source paths. Use `vcf-sv-stats diagnostics explain <code>` to inspect
the catalog definition.

Discrepancy reports support JSON, JSONL, and TSV. Their `counts` must reconcile
with the number and severities of emitted findings. `complete=false` means a
consumer must not treat absence of a code as evidence that the condition was
checked across the whole input.

## Normalization manifest

The transform manifest binds:

- request digest and adapter identity;
- source display name, digest, record count, and optional index digest;
- output data and index names, digests, and record count;
- normalization profile and target VCF version;
- reference status or explicit reference identity;
- schema URNs;
- one source-to-output mapping per emitted record.

For the conservative profile, input, output, and mapping cardinalities match.
For canonical VCF 4.5 output, one source row may map to multiple split output
rows; every mapping records source record and allele ordinals, output ID, and
the lossless transform class. The mapping list is provenance, not permission to
infer a missing relationship.

## Source-manifest comparison

An optional `vcf-sv-stats.source-manifest` binds a merged input to explicit
local source files by SHA-256, adapter URN, and source role. The comparator
matches source observations to merged support evidence and reports exactly one
of `preserved`, `not_preserved`, `not_found`, or `ambiguous`; counts reconcile
to exhaustive per-observation results. It never infers identity from filenames,
opens a remote resource, or proposes absent evidence for reinsertion.

A source manifest is required before canonical rewriting of a merger-produced
callset. Unsafe, ambiguous, digest-mismatched, aliased, or incomplete source
evidence blocks that rewrite.

## Receipt

The receipt is the ownership and completion proof for an artifact set. It binds:

1. the normalization request digest;
2. the transform-manifest digest;
3. the data, index, and manifest artifact digests.

Force replacement is rejected unless the prior receipt validates and names the
exact existing artifact set. A receipt proves integrity and ownership; it does
not prove scientific truth or clinical validity.

## Multi-report consumers

Consumers such as MultiQC should:

1. discover only `*.vcf-sv-stats.json` files;
2. require the summary content signature;
3. validate schema major, exact schema, and payload digest;
4. use `report_id` only as the display/deduplication key;
5. preserve analysis-unit and VCF-sample fields independently;
6. deduplicate byte-equivalent payloads;
7. reject conflicting payloads under the same `report_id`;
8. label all values as descriptive callset statistics, never accuracy.

See [MultiQC producer integration](multiqc-integration.md) for the executable
reference consumer.

## Compatibility rule

Schema major versions define compatibility. Unknown majors are rejected.
Consumers may ignore documented optional fields within a supported major only
when the embedded schema permits their absence. They must not guess renamed
fields, coerce invalid values, or silently substitute another artifact type.
