# Contributing

Contributions should preserve the public-neutral boundary and fail clearly when
required evidence is absent. Do not add private registries, hosted services,
deployment assumptions, credentials, customer data, or machine-specific paths.

Before submitting a change, run:

```bash
uv sync --locked --all-extras
uv run ruff check .
uv run mypy src/vcf_sv_stats
uv run pytest
uv run python tools/verify_test_data.py --test-data-dir test_data
```

Changes to schemas, adapters, diagnostics, normalization, statistics, or fixture
selection require focused tests and an update to the controlling ledger under
`docs/plans/`. Raw fixture sources must never be added to Git.
