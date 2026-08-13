# vcf-sv-stats

`vcf-sv-stats` is a standards-aware command-line tool and Python library for
inspecting, validating, summarizing, and conservatively normalizing structural
variant and copy-number VCF/BCF callsets.

The project reports descriptive properties of a callset. It does not calculate
truth concordance, precision, recall, clinical validity, or variant pathogenicity.

## Status

The API and schemas are pre-1.0 and under active development. The repository is
kept private until the public-release audit is complete.

The current implementation deliberately fails closed for representation-changing
normalization. Canonical multiallelic splitting, digest-bound merged/source
comparison, the complete VCF 4.5 local-allele matrix, large-callset performance
qualification, a native MultiQC module, and distribution-channel recipes remain
release gates. The controlling ledger records their exact dispositions; no
pre-1.0 artifact should be described as the complete v1 contract.

## Development install

```bash
uv sync --all-extras
uv run vcf-sv-stats --help
uv run pytest
```

The supported Python versions are 3.11, 3.12, and 3.13. Runtime input is local
VCF, BGZF VCF, BCF, or standard input. Commands do not initiate network access;
the explicit `reference fetch` command is the sole exception.

## Examples

```bash
vcf-sv-stats inspect calls.vcf.gz
vcf-sv-stats --json validate calls.bcf
vcf-sv-stats stats calls.vcf.gz --output summary.json
vcf-sv-stats normalize calls.vcf.gz --output calls.normalized.vcf.gz
```

See `docs/specifications/vcf-sv-stats-1.0.0.md` for the normative contract and
`docs/operator-guide.md` for operational examples.

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.
