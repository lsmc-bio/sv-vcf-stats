# `vcf-sv-stats` integration, qualification, and GitHub release ledger

Date: 2026-08-13

## Control

- Controlling ledger: `docs/plans/20260813T191624Z_private_fork_release_candidate_ledger.md`
- Prior implementation ledger: `docs/plans/20260813T065930Z_sv_vcf_stats_v1_implementation_ledger.md`
- Product boundary: neutral `vcf-sv-stats` code and documentation; organization names remain administrative hosting details only
- MultiQC boundary: integrate and qualify against the organization-owned MultiQC fork; do not merge into or otherwise modify upstream `MultiQC/MultiQC` or `MultiQC/test-data`
- Historical publication boundary: keep the repository private through the `1.0.0` candidate release and do not upload registry artifacts.
- Controlling 2026-08-13 amendment: preserve all completed work, continue on `codex/public-release-candidate`, release annotated `1.0.1`, make the repository public, and upload only the universal wheel plus its checksum to GitHub Releases. Pip in an ordinary environment and pip inside Conda must use the identical anonymous release URL. PyPI, Bioconda, native Conda channels, container registries, Sigstore publication, and public-upstream MultiQC work remain unauthorized.
- Controlling ASAP correction: do not run or resume the broad distribution matrix and do not start another test suite. Run `31755170704` was cancelled at the user's direction. `.github/workflows/distribution.yml` is limited to a manual build of exactly one tag-derived universal wheel. Move directly through PR merge, annotated tag, public GitHub release, and pip installation from the public URL.

## Gate 0: inventory freeze

### Repository baseline

- Core tool checkout: clean `codex/initial-implementation` at `099c1b1dd2e1e6f6e7ba86a972fb82ab80cf03a6`; private draft PR `#1` is mergeable and every core and distribution check is green.
- Core default branch before merge: `main` at `1376a6cf891e1363f3de6addcb282a06e3566109`; the implementation branch is 12 commits and 208 files ahead.
- Release-candidate worktree: isolated `codex/public-release-candidate`, rebased onto merged core commit `9d0eee52ac97372548ee0378e32b8aee0747a665`.
- MultiQC fork: public organization-owned fork with default branch `main` at `fa7fba4029bc76b3500b94ab698d347c2aacf66b`.
- Existing MultiQC checkout: contains unrelated untracked `.coverage` and `.playwright-cli/`; it will not be used for writes. New work uses isolated worktrees.
- Public upstream module and companion-data PRs are open drafts. They are superseded by the corrected fork-only direction and will be closed without merge after equivalent fork branches are safely recorded.

### Baseline evidence

- Core PR exact-head checks: Python 3.11 through 3.13, HTSlib 1.24, dependency review, package/artifact audit, container audit, 24 offline install receipts, Conda, OCI, SBOM/provenance, and Apptainer are green.
- MultiQC module source branch: `fa6007e91b1a914fee60546d67d8f53a3fd9789b`, seven changed files, 1,057 inserted lines, 12 focused tests, 11 report sections.
- Companion fixture source branch: `803a64424db0be82ffdce2ed99ba4ab8b1ee4528`, one 14,778-byte neutral HG002 summary.
- Known fork typing defect: `multiqc/utils/util_functions.py` dereferences the optional result of `get_ipython()`; Python 3.14 mypy reproduces this outside the new module.
- Tool fixture baseline: 21 source-derived compressed HG002 VCF fixtures, one derived BCF, one derived plain VCF, 1,186 source-derived records, and prior per-entry `reviewed-public-derived-data` dispositions.
- Signing baseline: qualification uses an ephemeral local Cosign key. No durable release identity is configured.
- Vulnerability-reporting baseline: the tool repository is private; the public-only reporting surface is therefore unavailable until visibility changes.

### Assumptions and limits

- The organization-owned MultiQC fork is publicly visible. “Internal fork” means the maintained integration target, not confidential hosting.
- The user authorizes core and fork PR readiness and merge, annotated tool tag `1.0.0`, a private tool GitHub release, and the next maintained-fork MultiQC tag and GitHub release. No public tool visibility, registry upload, or public upstream merge is authorized.
- The durable signing identity will be the GitHub Actions OIDC identity bound to the exact repository, workflow file, and default-branch ref. No long-lived signing secret will be created.
- Redistribution re-review may use public primary-source licensing and provenance documents. No additional genomic file will be fetched from remote storage or compute.

### 2026-08-13 GitHub-wheel tranche baseline

- At `2026-08-13T23:34:18Z`, clean branch `codex/public-release-candidate` fast-forwarded without rewrite from `e1e03451518d48c6a1e6796881af1ae4700ca7e9` to `origin/main` commit `de34fe8d462b335d3c5d567ad7b4e44427b8ed09`; the remote branch remained eight commits behind until this tranche is pushed.
- Annotated tag `1.0.0` peels to `de34fe8d462b335d3c5d567ad7b4e44427b8ed09`. The existing GitHub release is `https://github.com/lsmc-bio/sv-vcf-stats/releases/tag/1.0.0`, published at `2026-08-13T21:40:01Z`, with no uploaded assets.
- PR `#11` merged the release-candidate branch as `456b1e42e1887e6bb49b19dcd1baa7dd7140845d`; PR `#12` merged source-archive evidence hardening as current `main` commit `de34fe8d462b335d3c5d567ad7b4e44427b8ed09`.
- Exact-main CI run `31745397629`, CodeQL run `31745397529`, and manually dispatched distribution run `31745544787` succeeded. Run `31745544787` used branch `main`, not tag `1.0.0`, so it is source qualification but not final tag-version evidence.
- Repository `lsmc-bio/sv-vcf-stats` is private with default branch `main`; active ruleset `core` has ID `4066222`. Code security, Dependabot security updates, secret scanning, non-provider patterns, validity checks, and push protection are enabled; open secret-scanning alerts total zero.
- Private vulnerability reporting returns `404` while the repository is private. Its `true` read-back is mandatory after visibility changes and before the public release.
- Fixture manifest SHA-256 is `d06b0027678020eb132ca91b20156dd34b380eeaf5fc7184219a10434de40cca`. No fixture, runtime, schema, adapter, statistics, or MultiQC change is authorized by this tranche.
- PR `#13` initially started legacy broad-distribution run `31755170704`. The user rejected that scope; the run was cancelled and is not release evidence. It must not be resumed or redispatched.

## Promotion ledger

| ID | Area | Requirement | Status | Category | Gate | Owner | Evidence | Root Cause | Terminal Note |
|---|---|---|---|---|---|---|---|---|---|
| CORE-001 | Core | Mark the fully green implementation PR ready and merge it without bypassing rules | SUCCESS | feature_implementation | Gate 1 | orchestrator | PR `#1` merged normally at `9d0eee52ac97372548ee0378e32b8aee0747a665` after all 23 exact-head checks passed |  | The implementation is on `main`; the source branch remains available and no tag or publication action occurred. |
| MQC-001 | MultiQC fixture | Add the neutral HG002 summary as an in-repository fork integration fixture and merge it first | SUCCESS | feature_implementation | Gate 2 | orchestrator | Fork PR `#10` merged normally as `ec775bea00819340ef940ecd2da39d0ea0f29478`; source and destination SHA-256 were identical and both scanner policies passed |  | The in-repository fixture is on fork `main`; no public upstream data merge occurred. |
| MQC-002 | MultiQC module | Rebase the neutral module onto current fork `main`, register it, and bind integration tests to the merged fixture | SUCCESS | feature_implementation | Gate 2 | orchestrator | Fork PR `#11` merged normally as `f0377460424de2e4e75c97f1f27ef6261fc97897`; the consumer and in-repository fixture tests pass |  | Native consumer integration is on maintained-fork `main`. |
| MQC-003 | MultiQC typing | Fix the Python 3.14 optional-shell typing defect with a regression test | SUCCESS | feature_implementation | Gate 2 | orchestrator | Python 3.9 and 3.14 `mypy multiqc` and `mypy tests` pass; optional-shell and existing fork-test annotations are covered |  | The exact merged tree has no mypy error in either supported qualification interpreter. |
| MQC-004 | MultiQC quality | Pass focused tests, strict module execution, Ruff, mypy, code checks, and fork CI | SUCCESS | contract_test | Gate 2 | orchestrator | Module and generic harness tests pass on Python 3.9 and 3.14; strict CLI report generation, changed-file hooks, code checks, both mypy scopes, and exact-head CodeQL run `31737204419` pass |  | Four automated review findings were fixed with regressions and every thread was resolved. |
| MQC-005 | MultiQC merge | Review the fork diff, resolve every blocker, and merge the fork module PR | SUCCESS | contract_test | Gate 2 | orchestrator | Fork PR `#11`; head `344105e7165e4291b1e0dd9faae1f6c7e6be823b`; merge `f0377460424de2e4e75c97f1f27ef6261fc97897` |  | Merged normally with no branch-rule bypass. |
| MQC-006 | Upstream boundary | Close both premature public upstream drafts with a fork-first supersession note and no merge | SUCCESS | plan_amendment | Gate 2 | orchestrator | Both public-upstream drafts were given a supersession note and closed on 2026-08-13 |  | Neither public-upstream draft was merged. |
| FIX-001 | Redistribution | Reconcile the manifest to all 21 source-derived fixtures and both parity artifacts | SUCCESS | contract_test | Gate 3 | orchestrator | `tools/verify_test_data.py` reports 21 fixtures and 1,186 source-derived records; the manifest also covers derived BCF and plain VCF parity artifacts |  | All 23 artifacts carry a checked disposition. |
| FIX-002 | Redistribution | Re-review HG002, reference, caller-output, notice, and source-provenance bases using primary evidence | SUCCESS | legitimate_safety_handling | Gate 3 | orchestrator | `docs/fixture-governance.md` records the dated primary-source basis, scope, exclusions, invalidation conditions, and artifact table |  | No additional genomic file was retrieved. |
| FIX-003 | Redistribution | Record a terminal per-fixture public-release-candidate disposition without weakening the later publication gate | SUCCESS | legitimate_safety_handling | Gate 3 | orchestrator | Every primary and derived manifest entry carries `reviewed-public-release-candidate-2026-08-13`; `test_data/redistribution-review.json` binds that status to the RFC 8785 digest of every other manifest field |  | The builder defaults to pending; explicit pending verification checks integrity only, while release evidence always requires an exact review match. |
| SIGN-001 | Signing | Replace the ephemeral qualification key with a documented GitHub Actions OIDC Sigstore identity | SUCCESS | feature_implementation | Gate 4 | orchestrator | Only the job-level-gated manual default-branch signing job requests `id-token: write`; it creates no key or signing secret and binds the workflow identity to the exact default-branch ref |  | Pull-request and ordinary qualification jobs cannot mint an OIDC token. |
| SIGN-002 | Signing | Validate exact issuer and workflow identity constraints without publishing private-candidate signing metadata | SUCCESS | contract_test | Gate 4 | orchestrator | Workflow and tests require every distribution job to succeed, the exact workflow identity, and `https://token.actions.githubusercontent.com`; the opt-in dispatch input defaults false |  | No transparency-log entry is created for a partial qualification or without separate approval of that public metadata write. |
| DOC-001 | Documentation | Replace “private, pre-1.0” product-status language with accurate public-release-candidate language | SUCCESS | feature_implementation | Gate 4 | orchestrator | Current documentation tests reject stale status language; README, distribution, operator, benchmark, specification, security, and release docs are updated |  | Historical ledgers remain immutable evidence. |
| VULN-001 | Security | Reconfirm the current private-repository limitation and make enablement/read-back a mandatory visibility-transition gate | SUCCESS | legitimate_safety_handling | Gate 4 | orchestrator | Authenticated endpoint returned `404` while private on 2026-08-13; `SECURITY.md` requires enablement plus `true` read-back immediately after an approved visibility change |  | The repository remains private, so the public-only feature is not falsely claimed. |
| QUAL-001 | Qualification | Merge release-candidate preparation and run full qualification on the exact merged default-branch commit | SUCCESS | contract_test | Gate 5 | orchestrator | PR `#11` merged as `456b1e42e1887e6bb49b19dcd1baa7dd7140845d`; follow-up PR `#12` produced exact `main` `de34fe8d462b335d3c5d567ad7b4e44427b8ed09`; CI `31745397629`, CodeQL `31745397529`, and distribution `31745544787` succeeded on that commit |  | Exact-main source qualification is complete; the manual distribution run is not misrepresented as tag-ref evidence. |
| SCAN-001 | Neutrality | Run final checkout, artifact, Git, GitHub metadata, and completed-workflow scans with zero findings | OPEN | contract_test | Gate 5 | orchestrator | Pending |  |  |
| FINAL-001 | Closure | Terminalize every row and preserve the no-public-visibility and no-registry-publication boundary | NO_LONGER_NEEDED | plan_amendment | Gate 5 | orchestrator | The user's controlling GitHub-wheel amendment explicitly authorizes public repository visibility while retaining every registry prohibition |  | The historical private-visibility requirement is superseded; the no-registry boundary remains active. |
| HANDOFF-001 | Independent review | Commit a self-contained new-thread guide for skeptical design, specification, implementation, evidence, and gap review | SUCCESS | plan_amendment | Gate 6 | orchestrator | The handoff is present on `main` through merged PR `#11` at merge commit `456b1e42e1887e6bb49b19dcd1baa7dd7140845d` |  | The original review checklist is preserved and deferred by the controlling tranche amendment. |
| REL-001 | Tool version | Tag the source-qualified private default branch with annotated breaking version `1.0.0` | SUCCESS | release | Gate 6 | orchestrator | `git cat-file -t 1.0.0` returns `tag`; the tag peels to `de34fe8d462b335d3c5d567ad7b4e44427b8ed09` |  | The immutable historical candidate tag remains unchanged. |
| QUAL-002 | Release version | Run the full distribution matrix and final artifact scans on the exact `1.0.0` tag; require every derived package and image version to equal the tag | NO_LONGER_NEEDED | contract_test | Gate 6 | orchestrator | Live Actions history shows run `31745544787` used `main`; the narrowed tranche requires fresh exact-tag qualification for `1.0.1` under URL-QUAL-001 |  | Do not move or retrofit `1.0.0`; the exact-tag requirement transfers to the next patch release. |
| REL-002 | Tool release | Create a formal GitHub release for `1.0.0` while keeping the repository private | SUCCESS | release | Gate 6 | orchestrator | `https://github.com/lsmc-bio/sv-vcf-stats/releases/tag/1.0.0`, published `2026-08-13T21:40:01Z`, with zero uploaded assets |  | Historical release preserved unchanged; it will become visible with the repository. |
| REL-003 | MultiQC fork release | Tag the merged fork module with the next available maintained-fork version and create its GitHub release | SUCCESS | release | Gate 6 | orchestrator | An annotated release tag peels to merge `f0377460424de2e4e75c97f1f27ef6261fc97897`; the corresponding formal GitHub release was published on 2026-08-13 |  | The exact administrative version is recorded in the fork release, not in this neutral product repository. |
| URL-AMEND-001 | Scope | Narrow the active handoff without deleting the independent review backlog or completed evidence | SUCCESS | plan_amendment | Gate 7 | orchestrator | Controlling amendment in `docs/plans/20260813T193359Z_independent_design_completion_review_handoff.md`; user explicitly selected the same release-wheel URL for ordinary and Conda pip installation |  | Broader design review remains deferred, not accepted or discarded. |
| URL-BRANCH-001 | Git | Continue on and fast-forward the existing release-candidate branch without rewriting history | SUCCESS | plan_amendment | Gate 7 | orchestrator | `git merge --ff-only origin/main` advanced `e1e0345` to `de34fe8`; clean status before edits |  | Existing branch and all merged work are preserved. |
| URL-DOC-001 | Documentation | Document the exact GitHub wheel URL and identical pip-inside-Conda path; add public repository package metadata | SUCCESS | feature_implementation | Gate 7 | orchestrator | README, distribution/security docs, specification status, documentation map, `pyproject.toml`, `docs/releases/1.0.1.md`, and exact-URL regression in `tests/test_documentation.py`; local `1.0.1` wheel metadata and install verified |  | No runtime API, CLI, schema, statistics, fixture, adapter, or MultiQC behavior changed. |
| URL-SCAN-001 | Neutrality | Permit only the exact administrative GitHub repository coordinate in source/history scans while continuing to reject the owner token elsewhere | SUCCESS | contract_test | Gate 7 | orchestrator | `tools/scan_tokens.py --source-github-repository`; regressions in `tests/test_token_scanner.py`; source, history, wheel, and source-archive scans returned zero findings |  | Exact repository and GitHub-generated merge coordinates are administrative; product names, schemas, outputs, unrelated prose, and random Git object IDs receive no exception. |
| URL-PR-001 | GitHub | Commit, push, review, and merge the amended branch through the normal protected PR path | OPEN | release | Gate 7 | orchestrator | Pending |  |  |
| URL-TAG-001 | Version | Create and push immutable annotated tag `1.0.1` on the exact clean merge commit | OPEN | release | Gate 8 | orchestrator | Pending |  |  |
| URL-QUAL-001 | Wheel build | Build exactly one `py3-none-any` wheel from tag ref `1.0.1` with the narrowed manual workflow | OPEN | release | Gate 8 | orchestrator | Legacy broad run `31755170704` was cancelled; it is not evidence and must not be resumed |  | No test matrix, sdist, Conda package, OCI, Apptainer, SBOM, provenance, signing, or registry publication. |
| URL-VIS-001 | Visibility | Make the repository public, enable private vulnerability reporting, and read back security/rules settings | OPEN | legitimate_safety_handling | Gate 8 | orchestrator | Pending |  |  |
| URL-REL-001 | Release | Publish GitHub release `1.0.1` with only the exact-tag wheel and `SHA256SUMS` | OPEN | release | Gate 8 | orchestrator | Pending |  |  |
| URL-PIP-001 | Public install | Install the anonymous wheel URL into a clean ordinary Python 3.13 environment and run version plus installed verifier | OPEN | contract_test | Gate 8 | orchestrator | Pending |  |  |
| URL-CONDA-PIP-001 | Public install | Install the identical anonymous wheel URL with pip inside a clean Conda Python 3.13 environment and run version plus installed verifier | OPEN | contract_test | Gate 8 | orchestrator | Pending |  |  |
| URL-CLOSE-001 | Closure | Record release URL, SHAs, one-wheel build run, checksum, visibility, and both public pip-install receipts in a merged closeout | OPEN | plan_amendment | Gate 8 | orchestrator | Pending |  |  |

## Gates

| Gate | Requirement |
|---|---|
| Gate 0 | Exact repository, branch, dirty-state, PR, fixture, signing, and publication baselines recorded before writes. |
| Gate 1 | Core implementation merged through the protected pull-request path with exact-head green checks. |
| Gate 2 | Fixture-first fork integration and module PR merged with complete fork-local tests; public upstream drafts closed unmerged. |
| Gate 3 | Every bundled fixture has a fresh evidence-backed redistribution disposition. |
| Gate 4 | Durable keyless identity, release-candidate documentation, and visibility-transition security gate are implemented and tested. |
| Gate 5 | Exact merged default-branch source qualification and source-state scans pass before the private tag; no visibility change or registry publication occurs. |
| Gate 6 | The independent-review handoff is merged; the annotated tool tag receives full version-matching distribution qualification before its private GitHub release; maintained-fork tag and release evidence is terminal. Repository visibility and registries remain unchanged. |
| Gate 7 | Preserve and amend the existing handoff/ledger, pass local qualification, and merge the existing release-candidate branch normally. |
| Gate 8 | Build one universal wheel from annotated `1.0.1`, publish only that GitHub wheel/checksum, prove the same anonymous URL in ordinary and Conda pip environments, and merge the closeout evidence. Do not resume the broad distribution matrix or run another test suite. |

## Final report

All rows terminal: no.

Objective complete: no.

Current GitHub-wheel tranche complete: no.

Deferred independent design-review objective complete: no; preserved for a later thread.

Public repository visibility and the `1.0.1` GitHub wheel/checksum are authorized by the controlling amendment. No registry upload, Sigstore publication, or upstream MultiQC work is authorized.

## Status updates

- 2026-08-13: CORE-001 succeeded. The implementation PR was marked ready and merged through the protected pull-request path as `9d0eee52ac97372548ee0378e32b8aee0747a665`; no bypass or branch deletion was used.
- 2026-08-13: The user corrected the release boundary: keep the tool repository private, but create the qualified `1.0.0` tag and private GitHub release; also release the maintained-fork MultiQC version. Public visibility and registry publication remain unapproved.
- 2026-08-13: MQC-002 through MQC-006 succeeded. The maintained-fork module merged as `f0377460424de2e4e75c97f1f27ef6261fc97897` after exact-head CodeQL and local Python 3.9/3.14 qualification; both superseded public-upstream drafts were closed without merge.
- 2026-08-13: FIX-001 through VULN-001 reached evidence-backed success. Twenty-three fixture artifacts have a dated disposition, the durable signer is exact-identity keyless OIDC with an opt-in public-log gate, current status docs are reconciled, and the visibility-transition security read-back is mandatory.
- 2026-08-13: REL-003 succeeded. The next annotated maintained-fork tag and formal GitHub release point to the qualified module merge; its administrative version string remains outside this neutral product repository.
- 2026-08-13: Automated release review identified that untagged `setuptools-scm` artifacts carry a development version. QUAL-002 now makes full exact-tag `1.0.0` qualification a hard prerequisite for the private GitHub release.
- 2026-08-13: Live reconciliation found that `1.0.0` is annotated and its private GitHub release exists, but distribution run `31745544787` used `main`, not the tag ref. QUAL-002 is therefore `NO_LONGER_NEEDED` rather than falsely successful; URL-QUAL-001 carries the exact-tag proof forward to immutable patch release `1.0.1`.
- 2026-08-13: The user narrowed the active tranche to one public GitHub release wheel URL used by pip both normally and inside Conda, while preserving all prior work and deferring the skeptical full-design review. No native Conda or registry publication is included.
- 2026-08-13: The user explicitly stopped the legacy broad distribution matrix. Run `31755170704` was cancelled, the workflow was reduced to a manual one-wheel build, and the ledger forbids resuming that matrix or starting another test suite in this tranche.
- 2026-08-13: Gate 7 local qualification passed: Ruff and strict mypy are green; 119 tests pass; branch coverage is 82 percent; 21 fixtures and 1,186 records verify; focused release tests pass; source, history, wheel, and source-archive scans report zero findings. A locally built `1.0.1` wheel reports the exact version, carries the three GitHub project URLs, installs under Python 3.13, and passes `vcf-sv-stats-verify-install`.
