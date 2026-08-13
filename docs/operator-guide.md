# Operator guide

## Install and inspect

Python 3.11 through 3.13 is supported.

```bash
python -m pip install vcf-sv-stats
vcf-sv-stats --help
vcf-sv-stats info
vcf-sv-stats inspect calls.vcf.gz
vcf-sv-stats --json adapters detect calls.vcf.gz
```

An unknown producer is not an error. The generic adapter interprets only
standard fields and reports caller-specific values as unavailable.

## Validate and report discrepancies

```bash
vcf-sv-stats --json validate calls.bcf
vcf-sv-stats discrepancies calls.vcf.gz \
  --output findings.jsonl --format jsonl --fail-on error
```

The report is published before `--fail-on` changes the process exit. Parsing,
conformance, semantic consistency, operation safety, and statistics completeness
are separate states.

## Statistics and identity

```bash
vcf-sv-stats stats calls.vcf.gz --output cohort.vcf-sv-stats.json
vcf-sv-stats stats calls.vcf.gz \
  --identity-context analysis-units.json \
  --output attributed.vcf-sv-stats.json
```

The identity sidecar maps exact VCF sample columns to generic analysis units.
No identity is inferred from a filename or sample column. Without a sidecar,
callset statistics succeed with `analysis_unit.status=unresolved`.

Regional statistics require an index unless scanning is explicitly accepted:

```bash
vcf-sv-stats stats calls.vcf.gz --regions chr1:100000-200000
vcf-sv-stats stats calls.vcf --regions chr1 --regions-scan
```

Regional output is always marked partial.

## Conservative normalization

The pre-1.0 implementation performs only the `conservative` profile. The
`caller-lossless` and `canonical` names are reserved contracts and fail with a
complete safety assessment; they never silently copy the input while claiming
a representation-changing rewrite. No lossy transformation code is defined,
so every `--authorize-loss` value is rejected.

```bash
vcf-sv-stats normalize calls.vcf \
  --output calls.normalized.vcf.gz \
  --profile conservative
```

The operation writes data, index, transform manifest, and receipt. It refuses
findings that block normalization, input/output aliases, unrelated existing
paths, and incomplete force targets. The source bytes are never changed. A
request digest appears in the output header; the manifest and receipt form a
one-way digest graph.

If publication is interrupted, no final data path is left as a false completion
marker. A force replacement restores its prior verified set on failure. The
`run` command provides stronger group atomicity by staging and renaming one
complete report directory.

## References

Most operations are reference-free. To preflight the pinned public profile:

```bash
vcf-sv-stats --dry-run reference fetch \
  --assembly GRCh38.p14 --distribution ncbi-refseq
```

A real retrieval requires confirmation or `--yes`. `--offline` verifies an
existing cache and never opens the network. No reference is bundled.

## Configuration

Configuration is strict YAML. Duplicate or unknown keys fail. Supported
environment variables begin with `VCF_SV_STATS_`; use `vcf-sv-stats config show`
to inspect the effective values without secrets.

## Recovery and privacy

Do not paste genomic rows, genotypes, private paths, or credentials into issue
reports. Prefer artifact digests, record ordinals, diagnostic codes, and field
names. Use the repository security-advisory interface for suspected
vulnerabilities.
