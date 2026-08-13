# Testing and evidence guide

The test strategy follows the biological and publication risks of the tool:
small unit tests for exact semantics, source-derived fixture goldens for caller
dialects, failure injection for transaction boundaries, and independent tools
for container/index verification.

## Fast local loop

```bash
uv sync --locked --all-extras
uv run ruff check .
uv run mypy src/vcf_sv_stats
uv run pytest -q
```

The current suite includes API, CLI, schema, adapter, event, genotype/CN,
normalization, recovery, documentation, package, scanner, fixture, and MultiQC
producer-contract tests.

## Supported Python matrix

```bash
uv run --isolated --locked --all-extras --python 3.11 pytest -q
uv run --isolated --locked --all-extras --python 3.12 pytest -q
uv run --isolated --locked --all-extras --python 3.13 pytest -q
```

The isolated form proves that each interpreter resolves from the committed lock
rather than reusing the active development environment.

## Coverage gate

```bash
uv run coverage run -m pytest -q
uv run coverage report -m --fail-under=70
```

Coverage is a floor, not an acceptance argument. Exact behavioral assertions,
goldens, schema validation, and failure injection carry more weight than a raw
percentage.

## Fixture contract

```bash
uv run python tools/verify_test_data.py --test-data-dir test_data
```

The verifier independently checks:

- the exact expected file set;
- manifest and index SHA-256 values;
- record counts and corpus budgets;
- exactly one sample column named `HG002` in every VCF and BCF;
- absence of other common reference-subject token patterns;
- source-digest links to the inspected single-HG002 corpus;
- the exact-digest redistribution-review policy and status for every fixture;
- plain/compressed and VCF/BCF parity artifacts.

`tests/test_fixtures.py` then runs the application over every role and compares
adapter selection, callset grain, statistics, and diagnostic codes with the
committed goldens.

## Independent HTSlib validation

CI installs bcftools/HTSlib 1.24 independently of pysam and validates every
compressed fixture, plain VCF, BCF, TBI, and CSI. This catches container and
index problems that an application-only test could share with its own reader.

Warnings that represent deliberately retained caller quirks remain expected
only when a diagnostic golden and fixture-governance decision cover them.

## Documentation contract

```bash
uv run pytest -q tests/test_documentation.py
```

This test executes and compares documentation claims against the codebase:

- every relative Markdown link resolves;
- the README showcase equals statistics computed from its named fixture;
- the example identity sidecar validates and resolves `HG002` explicitly;
- the example configuration passes the strict loader;
- every documented command path has executable help;
- the documented adapter matrix matches the live registry;
- fixture counts and dependency claims match the manifest and project metadata.

The goal is to prevent a polished README from becoming a parallel, stale
product specification.

## Transaction and failure injection

Normalization tests cover:

- source/output lexical aliases;
- symlink and hard-link aliases;
- unrelated existing files and directories;
- incomplete prior artifact sets;
- invalid prior receipts;
- each publication rename boundary;
- parent-directory synchronization failure;
- backup movement and restoration;
- input and index digest preservation;
- VCF.gz and BCF semantic parity.

The invariant is stronger than “the command raised”: after any injected
failure, there is either no final artifact set or the exact prior verified set.

## Determinism and performance qualification

```bash
benchmark_dir=$(mktemp -d)
uv run python tools/benchmark_streaming.py \
  --input test_data/vcf/manta.native.hg002.subset.vcf.gz \
  --input test_data/vcf/sniffles2.native.hg002.subset.vcf.gz \
  --output "$benchmark_dir/result.json" \
  --repetitions 3 \
  --source-commit "$(git rev-parse HEAD)"
```

The harness runs every sample in a fresh child process and records monotonic
elapsed time, process peak RSS, temporary-disk peak, throughput, record count,
canonical payload digest, and a minimal-reader baseline while exposing only
input basenames. Repeated payload digests must match.

The committed [performance qualification](benchmarks/20260813_streaming_qualification.md)
covers deterministic neutral inputs from 100,000 through 10,000,000 records,
multi-sample and long-contig cases, fixed-worker digest parity, approximately
linear temporary storage, bounded RSS, and interruption recovery for `SIGINT`,
`SIGTERM`, file-size exhaustion, and untrappable termination. Its JSON receipts
validate against embedded schemas and bind the exact implementation commit.

## Distribution qualification

The [distribution guide](distribution.md) defines the supported OS,
architecture, Python, archive, Conda, OCI, and Apptainer matrix. The dedicated
workflow installs wheel and source-archive candidates without package-index
access, runs the self-contained install verifier, reconciles 24 receipts,
audits both OCI architectures and attestations, and produces SBOM, checksum,
license, and provenance evidence. Qualification never publishes an artifact.

## Package reproducibility

```bash
build_dir=$(mktemp -d)
SOURCE_DATE_EPOCH=315532800 uv build --out-dir "$build_dir"
uv run python tools/normalize_sdist.py \
  --sdist "$build_dir"/*.tar.gz --epoch 315532800
uv run python tools/build_sbom.py \
  --wheel "$build_dir"/*.whl --output "$build_dir/sbom.json"
```

Two independent builds must produce byte-identical wheel, normalized source
archive, and SBOM files. Building is a validation action; publishing remains a
separate approval gate.

## Content and history scans

```bash
uv run python tools/scan_tokens.py \
  --root . --policy policy/forbidden-token-hashes.json --git
uv run python tools/scan_tokens.py \
  --root . --policy policy/neutrality-token-hashes.json --structural
```

Policies store token lengths and SHA-256 digests, not prohibited plaintext. The
scanner checks filenames, decoded file contents, nested archives, BCF rendered
content, refs, commit messages, and every reachable Git object. The release
audit additionally scans repository metadata, review text, release text, and
completed workflow logs.

## Adding a caller fixture

Do not copy a convenient VCF into `test_data/`. A new fixture requires:

1. explicit source and redistribution review;
2. a source digest and single-subject identity inspection;
3. deterministic behavior selection with relationship closure;
4. header and record-body sanitization;
5. neutral identifier and relationship rewriting;
6. regenerated index and independent HTSlib validation;
7. verifier, scanner, and application golden success;
8. adapter evidence tests and a ledger row.

The builder has no source-directory default and must stage outside the checkout.
See [fixture governance](fixture-governance.md) for the complete procedure.
