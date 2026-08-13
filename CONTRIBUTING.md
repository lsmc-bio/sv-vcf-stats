# Contributing

`vcf-sv-stats` treats biological meaning, provenance, and failure behavior as
part of the public API. A good change does more than make a test green: it makes
the evidence for a claim reviewable.

## Design rules

- **Name the grain.** A source record, alternate allele, breakend, resolved
  event, genotype call, and analysis unit are different objects.
- **Preserve provenance.** Caller and merger support describe origin, not
  accuracy or truth concordance.
- **Require evidence.** Do not infer producer, reference, ploidy, identity,
  mate relationships, or missing configuration from convenient strings.
- **Fail closed.** Unsupported rewrites, incomplete artifact sets, unknown
  configuration, and missing identity mappings must not degrade into a fallback.
- **Keep the library embeddable.** Public API calls return immutable result
  models or structured exceptions; they never terminate the host process.
- **Keep the product portable.** Do not add private registries, hosted services,
  deployment assumptions, credentials, customer data, or machine-specific paths.

## Development setup

```bash
uv sync --locked --all-extras
uv run vcf-sv-stats info
uv run pytest -q
```

Supported interpreters are Python 3.11, 3.12, and 3.13. Dependencies must come
from public package indexes and remain represented in `uv.lock`.

## Choose the right proof

| Change | Minimum focused evidence |
|---|---|
| Parser or canonical observation | unit case plus source-derived fixture golden |
| Event resolution | reciprocal, orphan, ambiguous, and ordering cases |
| Statistics | exact numerator, denominator, missingness, and grain assertions |
| Adapter | evidence ranking, version state, native fixture, and rewrite policy |
| Schema or output field | schema test, producer test, consumer test, and compatibility note |
| Normalization | semantic parity, index validation, digest graph, and failure injection |
| CLI | command-policy and `cli-core-yo` conformance tests |
| Documentation | executable example or documentation-contract assertion |
| Fixture | provenance, redistribution review, HG002-only verification, and scanners |

Do not replace a focused semantic assertion with a broad snapshot. Snapshots
are useful only when the contract explains why every captured field matters.

## Local quality gate

```bash
uv run ruff check .
uv run mypy src/vcf_sv_stats
uv run pytest -q
uv run coverage run -m pytest -q
uv run coverage report -m --fail-under=70
uv run python tools/verify_test_data.py --test-data-dir test_data
uv run python tools/scan_tokens.py \
  --root . --policy policy/forbidden-token-hashes.json --git
uv run python tools/scan_tokens.py \
  --root . --policy policy/neutrality-token-hashes.json --structural
```

For the interpreter matrix, independent HTSlib checks, package reproducibility,
SBOM generation, and container validation, follow the [testing guide](docs/testing.md).

## Fixture changes

Raw source and intermediate VCFs must never enter the checkout or Git history.
The fixture builder requires an explicit `--source-dir`, writes into a temporary
stage, closes record selection over relationship groups, rebuilds headers and
identifiers through allowlists, and publishes only after all gates pass.

Every derived fixture requires its own redistribution decision. Failure blocks
that fixture; it is not permission to substitute a different source. See
[fixture governance](docs/fixture-governance.md).

## Contract changes

Before changing a schema, adapter identity, diagnostic code, metric contract,
normalization rule, or `vcf_sv_stats.api.v1` model:

1. identify the affected acceptance criterion in the normative specification;
2. state whether the change is compatible, additive, or breaking;
3. update producer and consumer tests together;
4. update examples and narrative documentation;
5. add evidence and disposition to the controlling ledger under `docs/plans/`.

Never reuse a stable identifier for different semantics. Add a versioned
identity when scope, denominator, unit, interpretation, or compatibility
changes.

## Pull request checklist

- [ ] The change has one clear biological or operational claim.
- [ ] Tests cover success, malformed input, and the relevant failure boundary.
- [ ] No identity, relationship, reference, or producer evidence is guessed.
- [ ] Output and diagnostics avoid raw genomic values and private paths.
- [ ] Examples and command documentation match executable behavior.
- [ ] Fixture provenance and redistribution status are unchanged or re-reviewed.
- [ ] The local quality gate passes from the committed lock.
- [ ] The implementation ledger records new evidence and remaining blockers.

Keep commits reviewable and do not mix unrelated refactors with a semantic
change. Public visibility, package or container publication, upstream
contributions, and release tags each remain separately approved actions.
