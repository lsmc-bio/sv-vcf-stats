# Repository agent guide

This file applies to the entire repository. It is written for contributors and
automated coding agents working from a public checkout.

## Start here

Read these files before changing behavior:

1. `README.md` for the product boundary and supported workflows.
2. `CONTRIBUTING.md` for design rules and proof requirements.
3. `docs/architecture.md` and `docs/output-contract.md` for semantic contracts.
4. `docs/testing.md` for the maintained validation matrix.

For multi-step, release, or contract-changing work, create a dated ledger under
`docs/plans/` before implementation. Keep evidence and row states current; a
successful command is not a substitute for a completed acceptance criterion.

## Development environment

Use the committed lock and run tools through `uv`:

```bash
uv sync --locked --all-extras
uv run vcf-sv-stats --help
```

Supported interpreters are Python 3.11, 3.12, and 3.13. Do not edit
`src/vcf_sv_stats/_version.py`; the version is generated from Git metadata.

## Repository map

| Path | Purpose |
|---|---|
| `src/vcf_sv_stats/` | Library, CLI, schemas, adapters, and packaged data |
| `tests/` | Contract, semantic, failure-boundary, and distribution tests |
| `test_data/` | Reviewed, sanitized, digest-bound fixtures and expected outputs |
| `docs/` | Architecture, operator guidance, contracts, evidence, and release notes |
| `tools/` | Reproducible fixture, benchmark, audit, and release-evidence utilities |
| `policy/` | Public-content and forbidden-token scanner policies |

## Product contracts

- Name the grain. Source records, alleles, breakends, resolved events,
  genotypes, and analysis units are distinct objects and metrics.
- Preserve evidence. Producer, merger, reference, identity, and relationship
  claims must come from explicit supported evidence, never filenames or guesses.
- Fail closed. Missing configuration, unsupported rewrites, malformed inputs,
  incomplete artifact sets, and ambiguous relationships must produce clear
  failures rather than fallback behavior.
- Keep public API calls embeddable. They return immutable result objects or
  structured exceptions and do not terminate the host process.
- Keep outputs deterministic and schema-valid. Update producers, consumers,
  examples, and compatibility notes together when a contract changes.
- Keep semantic analysis serial unless a separately approved design changes the
  contract. `--threads` controls HTSlib/BGZF compressed-input decompression; it
  does not shard Python record analysis or cross-record relationship resolution.
- Preserve transactional publication. Stage, validate, index, and bind outputs
  before the completion receipt is committed.

## Data and public-repository safety

- Never commit raw genomic inputs, credentials, tokens, customer data,
  machine-specific paths, command histories, or unpublished source material.
- Use synthetic inputs or the reviewed fixtures in `test_data/`. Fixture changes
  require provenance, redistribution review, digest regeneration, and scanners.
- Diagnostics and examples should use record ordinals, field names, stable codes,
  and digests instead of raw alleles, genotypes, identifiers, or local paths.
- Keep documentation portable: no private registries, hosted-service assumptions,
  internal runbooks, workstation layouts, or organization-specific instructions.
- Do not weaken, bypass, or special-case the token scanners to make a change pass.

## Change workflow

1. Start from the current `origin/main` and inventory the files and contracts in
   scope. Preserve unrelated user changes.
2. Make the smallest coherent change. Do not add compatibility aliases,
   speculative fallbacks, dependency upgrades, or broad refactors unless the
   request explicitly includes them.
3. Add focused proof for the behavior and failure boundary. Prefer exact semantic
   assertions over broad snapshots.
4. Run the narrow local gate below. Let the unchanged pull-request CI run its
   full interpreter, package, container, HTSlib, dependency, and CodeQL checks.
5. Update user-facing documentation whenever CLI behavior, outputs, installation,
   or compatibility changes.

## Focused local gate

Choose the relevant tests, then run static checks on touched code:

```bash
uv run pytest -q tests/test_relevant_area.py
uv run ruff check path/to/touched.py tests/test_relevant_area.py
uv run mypy src/vcf_sv_stats
uv run python tools/scan_tokens.py \
  --root . --policy policy/forbidden-token-hashes.json --git
uv run python tools/scan_tokens.py \
  --root . --policy policy/neutrality-token-hashes.json --structural \
  --source-github-repository OWNER/REPOSITORY
git diff --check
```

Use the repository's actual owner and name for `OWNER/REPOSITORY`. Do not run a
broad local suite when a controlling plan explicitly asks for focused checks;
the existing pull-request workflow remains the full qualification gate.

## Proof by change type

| Change | Minimum focused proof |
|---|---|
| Variant input or canonical scan | compressed/plain/BCF coverage plus output parity |
| Event relationships | reciprocal, orphan, duplicate, event, and ordering cases |
| Statistics | exact grain, numerator, denominator, and missingness assertions |
| Adapter | evidence ranking, version state, native fixture, and rewrite policy |
| Schema or API | producer, consumer, validation, and compatibility tests |
| Normalization | semantic parity, index validation, digest graph, and failure injection |
| CLI | command policy, exit behavior, and library-boundary checks |
| Documentation | link resolution, executable examples, and public-content scanners |
| Distribution | exact artifact inventory, checksum, and fresh installation proof |

## Git and releases

- Use normal review branches and pull requests; do not force-push protected
  history or bypass required checks.
- Keep commits reviewable and separate unrelated refactors from semantic changes.
- Release tags are annotated, non-`v` semantic versions created from a clean,
  merged `main` commit. Never move a published version tag.
- Use the existing distribution workflow. Publishing a tag, release, registry
  artifact, signing record, or external contribution requires explicit maintainer
  authorization; one action does not imply the others.
- A release is complete only after the documented artifacts, checksums, fresh
  installation proof, and release receipts all agree on the exact tag and commit.

When instructions conflict, preserve the public API and safety contracts, stop
at the narrowest unresolved boundary, and ask for a maintainer decision.
