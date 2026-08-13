# Independent design and completion review handoff

Date: 2026-08-13

## Mission for the next thread

Perform a skeptical, repository-grounded review of `vcf-sv-stats`. Determine
whether the implementation actually fulfills its design intention, normative
specification, acceptance plan, and release claims. Find correctness problems,
missing behavior, weak tests, misleading documentation, and evidence gaps, then
implement and verify every safe in-scope repair needed to make the tool complete.

Do not inherit a percentage or `SUCCESS` row as truth. Recalculate completion
from executable evidence. Distinguish all rows being terminal from the objective
being genuinely complete.

## Non-negotiable boundaries

- Keep the tool portable and public-neutral. Product code, documentation,
  schemas, outputs, fixtures, package metadata, and runtime behavior must not
  depend on a particular organization, private service, storage system, compute
  cluster, credential, customer identity, or filesystem layout.
- Keep the repository private. A private GitHub tag or release does not
  authorize public visibility, PyPI, Conda, container-registry publication, or
  an external upstream pull request.
- Treat the maintained MultiQC fork as the current integration target. Do not
  write to the public upstream MultiQC repositories. A later thread may prepare
  a new upstream proposal only after separate approval.
- Preserve the separation between descriptive callset statistics and truth-set
  concordance. Preserve report ID, optional analysis-unit context, and VCF
  sample columns as distinct identities.
- Do not add guessed defaults, silent fallbacks, compatibility shims, or
  filename-derived identity.
- Do not retrieve genomic inputs from private infrastructure or object storage.
  If an additional file is genuinely necessary, justify it first. Pause and ask
  for guidance before retrieving more than five additional files.
- Never place raw or intermediate source VCFs in the repository or Git history.
- Refer to the prohibited branding requirement only as `BRAND-002`; do not spell
  or echo a matching token in files, commit messages, tags, issues, or logs.

## Read before judging

Read these sources completely and in this order:

1. `README.md` and `docs/README.md`;
2. `docs/specifications/vcf-sv-stats-1.0.0.md`;
3. the newest controlling ledger under `docs/plans/`, followed by
   `docs/plans/20260813T065930Z_sv_vcf_stats_v1_implementation_ledger.md`;
4. `docs/architecture.md`, `docs/output-contract.md`, and
   `docs/command-reference.md`;
5. `docs/fixture-governance.md`, `test_data/manifest.json`, and
   `test_data/NOTICE.md`;
6. `docs/testing.md`, `docs/distribution.md`, `SECURITY.md`, and
   `docs/multiqc-integration.md`;
7. `pyproject.toml`, dependency locks, schemas, adapter registry, workflows,
   implementation modules, and tests.

Also inspect current GitHub state directly: default-branch commit, open and
merged pull requests, rules, visibility, tags, releases, workflow runs,
security settings, and attached release evidence. Treat the checked-out source
and live repository as authoritative over this handoff if they differ.

## Required review questions

### Product and interface

- Does the CLI actually use the public `cli-core-yo==2.1.1` contract throughout,
  with one immutable command specification and explicit command policies?
- Do every CLI command and every `vcf_sv_stats.api.v1` function agree on input,
  output, error, exit, streaming, and side-effect semantics?
- Are VCF 4.5 cardinalities, arbitrary ploidy, local alleles, phasing, BNDs,
  mate/event closure, duplicate IDs, symbolic alleles, CN, and multiallelic
  normalization lossless under every claimed safe path?
- Can any unsupported, provisional, ambiguous, or unknown adapter accidentally
  authorize a rewrite?
- Are source-versus-merged comparisons explicit about `preserved`,
  `not_preserved`, `not_found`, and `ambiguous`, without inventing evidence?

### Data integrity and transactions

- Can path aliases, symlinks, hard links, interruption, index failure, receipt
  failure, or force replacement leave a partial or falsely complete output?
- Does the one-way request, manifest, receipt digest graph bind every artifact
  exactly once without circularity or an unbound mutable field?
- Are deterministic JSON, strict YAML, finite-number handling, schema versioning,
  and library exception boundaries tested with malformed and adversarial inputs?

### Statistics and scale

- Does every public metric name its grain, denominator, unit, inclusion rule,
  missing/invalid state, derivation status, and comparability group?
- Are records, alleles, breakends, events, calls, VCF samples, analysis units,
  and callsets kept distinct in code as well as prose?
- Reproduce the 100K through 10M qualification claims. Check peak RSS,
  temporary-space growth, determinism, thread invariance, interruption recovery,
  and baseline fairness rather than accepting stored receipts alone.

### Fixtures and redistribution

- Independently verify all 21 source-derived compressed VCF fixtures, the BCF
  parity artifact, and the plain VCF parity artifact against the manifest.
- Confirm every VCF and BCF has exactly one sample named `HG002`, every manifest
  entry declares `HG002`, and no other supported subject-token pattern occurs.
- Confirm source and fixture hashes, record counts, indexes, relationship
  closure, behavior coverage, compressed-size limit, neutral headers, neutral
  record IDs, and the dated per-artifact redistribution disposition.
- Check that expected JSON and JSONL files are computed from fixtures rather than
  hand-authored to match implementation bugs.

### Security, neutrality, and supply chain

- Threat-model local input parsing, decompression, temporary storage,
  normalization replacement, reference retrieval, configuration, diagnostics,
  release evidence, and CI identity boundaries.
- Run both hashed token policies across tracked paths, decompressed content,
  Git history, built wheels and source archives, SBOMs, OCI layers, indexes,
  release notes, repository metadata, and completed workflow logs.
- Verify Sigstore provenance only accepts the exact GitHub Actions workflow and
  OIDC issuer. Confirm no persistent private signing key or signing secret exists.
- Rebuild wheel and source archive, test offline installation on all declared
  targets, validate SBOMs and provenance, audit the multi-architecture OCI
  layout, and execute the Apptainer smoke contract.

### MultiQC consumer

- Verify the fork module discovers only `*.vcf-sv-stats.json`, validates schema,
  content signature, and canonical digest, rejects conflicts, preserves identity
  boundaries, and renders zero-valued and malformed edge cases visibly.
- Run its focused tests, generic module harness, strict CLI report generation,
  Ruff, mypy on Python 3.9 and 3.14, code checks, and fork CI.
- Confirm the fork release consumes the in-repository neutral HG002 summary and
  has no dependency on the superseded public upstream drafts.

## Evidence and execution contract

Create a new datetime-named controlling ledger in `docs/plans/` before making
changes. Gate 0 must record the exact commits, tags, releases, workflow run IDs,
toolchain versions, dirty state, fixture manifest digest, and live repository
settings. Give every defect or gap its own row with status, evidence, blocker,
root cause, and terminal disposition.

Run the repository-prescribed test matrix plus tests designed to falsify each
claim. Review the diff interactively before merge. Use ordinary pull requests,
wait for exact-head checks, resolve every actionable review thread, and never
bypass branch rules. A later private tag or release must point to a clean,
fully qualified default-branch commit.

At handoff, report:

- feature acceptance percentage and scoring method;
- total ledger percentage and scoring method;
- fully accepted rows over total rows;
- every remaining item below 100 percent, in dependency order;
- whether all rows are terminal;
- whether the objective is actually complete;
- exact commits, tags, releases, CI runs, and artifacts supporting the answer.

Do not declare 100 percent because tests pass. Declare it only when the design,
specification, implementation, fixtures, documentation, distribution evidence,
and maintained MultiQC consumer agree under independent negative testing.
