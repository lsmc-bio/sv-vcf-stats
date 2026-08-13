# `vcf-sv-stats` private-fork integration and public-release-candidate ledger

Date: 2026-08-13

## Control

- Controlling ledger: `docs/plans/20260813T191624Z_private_fork_release_candidate_ledger.md`
- Prior implementation ledger: `docs/plans/20260813T065930Z_sv_vcf_stats_v1_implementation_ledger.md`
- Product boundary: neutral `vcf-sv-stats` code and documentation; organization names remain administrative hosting details only
- MultiQC boundary: integrate and qualify against the organization-owned MultiQC fork; do not merge into or otherwise modify upstream `MultiQC/MultiQC` or `MultiQC/test-data`
- Publication boundary: keep the repository private; after exact-main qualification, create annotated tag `1.0.0`, qualify the exact tag-derived version, and only then create a private GitHub release. Do not change visibility or upload Python, Conda, or container-registry artifacts

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
| QUAL-001 | Qualification | Merge release-candidate preparation and run full qualification on the exact merged default-branch commit | OPEN | contract_test | Gate 5 | orchestrator | Pending |  |  |
| SCAN-001 | Neutrality | Run final checkout, artifact, Git, GitHub metadata, and completed-workflow scans with zero findings | OPEN | contract_test | Gate 5 | orchestrator | Pending |  |  |
| FINAL-001 | Closure | Terminalize every row and preserve the no-public-visibility and no-registry-publication boundary | OPEN | plan_amendment | Gate 5 | orchestrator | Pending |  |  |
| HANDOFF-001 | Independent review | Commit a self-contained new-thread guide for skeptical design, specification, implementation, evidence, and gap review | IN_PROGRESS | plan_amendment | Gate 6 | orchestrator | `docs/plans/20260813T193359Z_independent_design_completion_review_handoff.md` |  | Awaiting merge. |
| REL-001 | Tool version | Tag the source-qualified private default branch with annotated breaking version `1.0.0` | OPEN | release | Gate 6 | orchestrator | Pending |  | The immutable tag is the input to final release-version qualification, not its substitute. |
| QUAL-002 | Release version | Run the full distribution matrix and final artifact scans on the exact `1.0.0` tag; require every derived package and image version to equal the tag | OPEN | contract_test | Gate 6 | orchestrator | Pending |  | The GitHub release is blocked until this exact-tag gate succeeds. |
| REL-002 | Tool release | Create a formal GitHub release for `1.0.0` while keeping the repository private | OPEN | release | Gate 6 | orchestrator | Pending |  |  |
| REL-003 | MultiQC fork release | Tag the merged fork module with the next available maintained-fork version and create its GitHub release | SUCCESS | release | Gate 6 | orchestrator | An annotated release tag peels to merge `f0377460424de2e4e75c97f1f27ef6261fc97897`; the corresponding formal GitHub release was published on 2026-08-13 |  | The exact administrative version is recorded in the fork release, not in this neutral product repository. |

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

## Final report

All rows terminal: no.

Objective complete: no.

No repository visibility change, registry upload, or upstream MultiQC merge is authorized by this ledger. The tool tag is authorized after its exact merge commit passes source qualification; its GitHub release is authorized only after the tagged `1.0.0` artifacts independently pass the full distribution and scan gates.

## Status updates

- 2026-08-13: CORE-001 succeeded. The implementation PR was marked ready and merged through the protected pull-request path as `9d0eee52ac97372548ee0378e32b8aee0747a665`; no bypass or branch deletion was used.
- 2026-08-13: The user corrected the release boundary: keep the tool repository private, but create the qualified `1.0.0` tag and private GitHub release; also release the maintained-fork MultiQC version. Public visibility and registry publication remain unapproved.
- 2026-08-13: MQC-002 through MQC-006 succeeded. The maintained-fork module merged as `f0377460424de2e4e75c97f1f27ef6261fc97897` after exact-head CodeQL and local Python 3.9/3.14 qualification; both superseded public-upstream drafts were closed without merge.
- 2026-08-13: FIX-001 through VULN-001 reached evidence-backed success. Twenty-three fixture artifacts have a dated disposition, the durable signer is exact-identity keyless OIDC with an opt-in public-log gate, current status docs are reconciled, and the visibility-transition security read-back is mandatory.
- 2026-08-13: REL-003 succeeded. The next annotated maintained-fork tag and formal GitHub release point to the qualified module merge; its administrative version string remains outside this neutral product repository.
- 2026-08-13: Automated release review identified that untagged `setuptools-scm` artifacts carry a development version. QUAL-002 now makes full exact-tag `1.0.0` qualification a hard prerequisite for the private GitHub release.
