# Operator guide

This guide is the shortest path from an unfamiliar structural-variant callset
to an auditable result. For exact flags, use the [command reference](command-reference.md);
for field semantics, use the [output contract](output-contract.md).

## Operating model

Treat the workflow as a sequence of progressively stronger claims:

1. **Inspect** identifies the container, header, samples, producer evidence, and
   obvious structural features.
2. **Validate** decides whether the callset is conformant, semantically
   consistent, safe for the requested operation, and complete for statistics.
3. **Report** emits deterministic statistics or exhaustive diagnostics.
4. **Normalize** publishes a new indexed artifact only when the implemented
   profile can prove the rewrite safe.

Opening a file successfully proves only that its container was readable. It
does not prove SV semantics, event completeness, or normalization safety.

## Install from a checkout

The package is intentionally unpublished during private pre-1.0 development.
Python 3.11 through 3.13 is supported.

```bash
uv sync --locked --all-extras
uv run vcf-sv-stats --help
uv run vcf-sv-stats info
```

`info` is the fastest environment receipt: it reports the tool, Python,
`cli-core-yo`, pysam, HTSlib, schema, and adapter-registry versions.

## First response for an unfamiliar callset

Start without writing output:

```bash
uv run vcf-sv-stats --json inspect calls.vcf.gz --max-records 100 \
  > inspection.json
uv run vcf-sv-stats --json adapters detect calls.vcf.gz --all-candidates \
  > adapter-evidence.json
uv run vcf-sv-stats --json validate calls.vcf.gz \
  > validation.json
```

Use `inspect --max-records` only for reconnaissance; its result is marked
incomplete. Adapter detection is evidence-ranked. An unknown producer is not an
error: the generic adapter interprets only standards-level fields and leaves
caller-specific values unavailable. Ambiguous or provisional evidence remains
visible and must not be silently overridden.

Validation reports six independent states:

| State | Question answered |
|---|---|
| `container_state` | Can the bytes be read as the declared format? |
| `parse_state` | Can records and declared fields be parsed? |
| `vcf_conformance_state` | Do declarations and values satisfy VCF rules? |
| `sv_semantic_state` | Are SV alleles and relationships internally coherent? |
| `operation_safety_state` | Is the requested rewrite safe? |
| `statistics_state` | Is the selected statistical scope complete? |

Do not compress those states into a single informal “valid VCF” label.

## Choose the right artifact

| Need | Command | Primary artifact |
|---|---|---|
| A compact machine summary | `stats` | `*.vcf-sv-stats.json` |
| Every actionable finding | `discrepancies` | JSON, JSONL, or TSV |
| CI pass/fail plus retained evidence | `discrepancies --fail-on` | report first, policy exit second |
| A portable report directory | `run` | atomic directory bundle |
| A rewritten, indexed callset | `normalize` | VCF.gz or BCF plus index and sidecars |

### Statistics

```bash
uv run vcf-sv-stats stats calls.vcf.gz \
  --mode standard \
  --output calls.vcf-sv-stats.json
```

Statistics are descriptive. They do not imply truth-set concordance, accuracy,
clinical meaning, or caller quality. Each stable metric names its scope,
denominator, unit, and comparability group.

### Exhaustive discrepancies in CI

```bash
uv run vcf-sv-stats discrepancies calls.vcf.gz \
  --output findings.jsonl \
  --format jsonl \
  --fail-on error
```

The report is committed before `--fail-on` changes the process exit. A failed
job therefore retains the evidence needed to explain the gate. Use stable
diagnostic codes for automation; messages are for humans.

### Atomic report bundle

```bash
uv run vcf-sv-stats run calls.vcf.gz --output-dir report
```

`run` stages the complete report in a sibling temporary directory and renames
it into place only after validation. Add `--normalize` only when a normalized
callset belongs in the same publication unit.

## Explicit analysis context

A VCF sample column is a genotype namespace, not automatically a biological
sample, library, case, or analysis. Provide optional context through an exact
sidecar mapping:

```bash
uv run vcf-sv-stats stats calls.vcf.gz \
  --identity-context docs/examples/identity-context.json \
  --output attributed.vcf-sv-stats.json
```

The sidecar maps exact VCF sample IDs to generic analysis units. No identity is
inferred from filenames, directory names, or sample-like strings. Without a
sidecar, callset statistics still succeed and report
`analysis_unit.status=unresolved`.

## Regional statistics

Indexed inputs support region selection directly:

```bash
uv run vcf-sv-stats stats calls.vcf.gz --regions chr1:100000-200000
```

For an unindexed input, scanning must be explicit:

```bash
uv run vcf-sv-stats stats calls.vcf --regions chr1 --regions-scan
```

Every regional result is marked partial. Normalization rejects regional scope
because a partial rewrite could masquerade as a complete callset.

## Normalization

Use `conservative` when record cardinality and representation must remain
unchanged:

```bash
uv run vcf-sv-stats normalize calls.vcf \
  --output calls.normalized.vcf.gz \
  --profile conservative
```

A successful publication contains one verified set:

```text
calls.normalized.vcf.gz
calls.normalized.vcf.gz.tbi
calls.normalized.vcf.gz.transforms.json
calls.normalized.vcf.gz.receipt.json
```

BCF output receives a CSI index. The source bytes are never changed. The tool
rejects input/output aliases, unrelated existing paths, incomplete force
targets, provisional or unsupported rewrites, and any diagnostic that blocks
normalization.

Use `canonical` only for a finalized VCF 4.5 input whose adapter and field
declarations prove lossless multiallelic splitting:

```bash
uv run vcf-sv-stats normalize finalized.vcf.gz \
  --output finalized.canonical.vcf.gz \
  --profile canonical
```

The canonical planner projects `Number=A/R/G/P/LA/LR/LG`, GT, arbitrary
ploidy, and phase state; rewrites IDs, mates, and events; and records every
source-to-output mapping. A merged callset also needs `--source-manifest` with
digest-bound local source files. Missing or ambiguous evidence fails before
publication.

`caller-lossless` remains a reserved contract name and fails with a complete
safety assessment. Every `--authorize-loss` value is rejected because no lossy
transform is implemented.

### Publication and recovery

The request digest is embedded in the output header. The transformation
manifest binds input, data, index, mappings, and schemas. The receipt binds the
request, manifest, and published artifacts.

If publication is interrupted, no final data path is left as a false completion
marker. A force replacement restores the exact prior verified set when a later
publication step fails. Never treat the presence of only the data file as
success; verify the complete set and receipt.

## Public reference retrieval

Most operations are reference-free. Plan the one supported pinned profile
without network or cache mutation:

```bash
uv run vcf-sv-stats --dry-run reference fetch \
  --assembly GRCh38.p14 \
  --distribution ncbi-refseq
```

A real retrieval requires confirmation or `--yes`. `--offline` verifies an
existing cache and never opens the network. No reference genome is bundled.

## Strict configuration

Start from the packaged template, then inspect the effective result:

```bash
uv run vcf-sv-stats config init
uv run vcf-sv-stats config validate
uv run vcf-sv-stats config show
```

Configuration is strict YAML. Duplicate keys, unknown keys, unsupported schema
versions, and invalid enum values fail. Environment overrides are limited to
the documented `VCF_SV_STATS_*` variables; missing paths are not discovered or
guessed. See [examples/config.yaml](examples/config.yaml).

## Troubleshooting by symptom

| Symptom | First evidence to inspect | Safe next action |
|---|---|---|
| Producer is unknown | `adapters detect --all-candidates` | Continue generically or supply an exact matching adapter URN. |
| Producer is provisional | selected adapter status and version evidence | Inspect and report; do not rewrite. |
| Statistics are blocked | diagnostics with `blocks_statistics=true` | Correct the source contract or narrow the question without mutating the source. |
| Normalization is blocked | diagnostics with `blocks_normalization=true` and fixability | Provide the missing evidence or leave the callset unchanged. |
| Region access fails | index presence and input format | Add a valid index or opt into `--regions-scan`. |
| Output already exists | complete artifact set and receipt | Choose a new path; use `--force` only for a complete verified replacement. |
| A prior run was interrupted | final paths, receipt, and sibling staging paths | Trust only a receipt-bound complete set; rerun after preserving evidence. |

## Privacy-preserving support

Genomic rows, genotypes, identifiers, and local paths may be sensitive. For bug
reports, prefer:

- tool and schema versions from `info`;
- input and artifact digests;
- record ordinals rather than full records;
- stable diagnostic codes and field names;
- the smallest sanitized reproduction that preserves the failure.

Do not paste genomic rows, credentials, private paths, or unsanitized headers
into an issue. Follow the [security policy](../SECURITY.md) for vulnerabilities.
