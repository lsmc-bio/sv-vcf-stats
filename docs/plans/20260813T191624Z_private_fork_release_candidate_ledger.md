# `vcf-sv-stats` private-fork integration and public-release-candidate ledger

Date: 2026-08-13

## Control

- Controlling ledger: `docs/plans/20260813T191624Z_private_fork_release_candidate_ledger.md`
- Prior implementation ledger: `docs/plans/20260813T065930Z_sv_vcf_stats_v1_implementation_ledger.md`
- Product boundary: neutral `vcf-sv-stats` code and documentation; organization names remain administrative hosting details only
- MultiQC boundary: integrate and qualify against the organization-owned MultiQC fork; do not merge into or otherwise modify upstream `MultiQC/MultiQC` or `MultiQC/test-data`
- Publication boundary: prepare a public release candidate, but do not change repository visibility, create a version tag or release, or upload Python, Conda, or container artifacts

## Gate 0: inventory freeze

### Repository baseline

- Core tool checkout: clean `codex/initial-implementation` at `099c1b1dd2e1e6f6e7ba86a972fb82ab80cf03a6`; private draft PR `#1` is mergeable and every core and distribution check is green.
- Core default branch before merge: `main` at `1376a6cf891e1363f3de6addcb282a06e3566109`; the implementation branch is 12 commits and 208 files ahead.
- Release-candidate worktree: isolated `codex/public-release-candidate` worktree created from the pre-merge default branch so the completed implementation checkout remains clean.
- MultiQC fork: public organization-owned fork with default branch `main` at `fa7fba4029bc76b3500b94ab698d347c2aacf66b`.
- Existing MultiQC checkout: contains unrelated untracked `.coverage` and `.playwright-cli/`; it will not be used for writes. New work uses isolated worktrees.
- Public upstream module and companion-data PRs are open drafts. They are superseded by the corrected fork-only direction and will be closed without merge after equivalent fork branches are safely recorded.

### Baseline evidence

- Core PR exact-head checks: Python 3.11 through 3.13, HTSlib 1.24, dependency review, package/artifact audit, container audit, 24 offline install receipts, Conda, OCI, SBOM/provenance, and Apptainer are green.
- MultiQC module source branch: `fa6007e91b1a914fee60546d67d8f53a3fd9789b`, seven changed files, 1,057 inserted lines, 12 focused tests, 11 report sections.
- Companion fixture source branch: `803a64424db0be82ffdce2ed99ba4ab8b1ee4528`, one 14,778-byte neutral HG002 summary.
- Known fork typing defect: `multiqc/utils/util_functions.py` dereferences the optional result of `get_ipython()`; Python 3.14 mypy reproduces this outside the new module.
- Tool fixture baseline: 21 source-derived HG002 VCF fixtures, one derived BCF, 1,186 records, and prior per-entry `reviewed-public-derived-data` dispositions.
- Signing baseline: qualification uses an ephemeral local Cosign key. No durable release identity is configured.
- Vulnerability-reporting baseline: the tool repository is private; the public-only reporting surface is therefore unavailable until visibility changes.

### Assumptions and limits

- The organization-owned MultiQC fork is publicly visible. “Internal fork” means the maintained integration target, not confidential hosting.
- The user authorizes core and fork PR readiness and merge. No upstream merge, public tool visibility, version tag, registry upload, or release announcement is authorized.
- The durable signing identity will be the GitHub Actions OIDC identity bound to the exact repository, workflow file, and default-branch ref. No long-lived signing secret will be created.
- Redistribution re-review may use public primary-source licensing and provenance documents. No additional genomic file will be fetched from remote storage or compute.

## Promotion ledger

| ID | Area | Requirement | Status | Category | Gate | Owner | Evidence | Root Cause | Terminal Note |
|---|---|---|---|---|---|---|---|---|---|
| CORE-001 | Core | Mark the fully green implementation PR ready and merge it without bypassing rules | OPEN | feature_implementation | Gate 1 | orchestrator | Pending |  |  |
| MQC-001 | MultiQC fixture | Add the neutral HG002 summary as an in-repository fork integration fixture and merge it first | OPEN | feature_implementation | Gate 2 | orchestrator | Pending |  |  |
| MQC-002 | MultiQC module | Rebase the neutral module onto current fork `main`, register it, and bind integration tests to the merged fixture | OPEN | feature_implementation | Gate 2 | orchestrator | Pending |  |  |
| MQC-003 | MultiQC typing | Fix the Python 3.14 optional-shell typing defect with a regression test | OPEN | feature_implementation | Gate 2 | orchestrator | Pending |  |  |
| MQC-004 | MultiQC quality | Pass focused tests, strict module execution, Ruff, mypy, code checks, and fork CI | OPEN | contract_test | Gate 2 | orchestrator | Pending |  |  |
| MQC-005 | MultiQC merge | Review the fork diff, resolve every blocker, and merge the fork module PR | OPEN | contract_test | Gate 2 | orchestrator | Pending |  |  |
| MQC-006 | Upstream boundary | Close both premature public upstream drafts with a fork-first supersession note and no merge | OPEN | plan_amendment | Gate 2 | orchestrator | Pending |  |  |
| FIX-001 | Redistribution | Reconcile the manifest to all 21 source-derived fixtures and one derived BCF | OPEN | contract_test | Gate 3 | orchestrator | Pending |  |  |
| FIX-002 | Redistribution | Re-review HG002, reference, caller-output, notice, and source-provenance bases using primary evidence | OPEN | legitimate_safety_handling | Gate 3 | orchestrator | Pending |  |  |
| FIX-003 | Redistribution | Record a terminal per-fixture public-release-candidate disposition without weakening the later publication gate | OPEN | legitimate_safety_handling | Gate 3 | orchestrator | Pending |  |  |
| SIGN-001 | Signing | Replace the ephemeral qualification key with a documented GitHub Actions OIDC Sigstore identity | OPEN | feature_implementation | Gate 4 | orchestrator | Pending |  |  |
| SIGN-002 | Signing | Verify the signed provenance against exact issuer and workflow identity constraints | OPEN | contract_test | Gate 4 | orchestrator | Pending |  |  |
| DOC-001 | Documentation | Replace “private, pre-1.0” product-status language with accurate public-release-candidate language | OPEN | feature_implementation | Gate 4 | orchestrator | Pending |  |  |
| VULN-001 | Security | Reconfirm the current private-repository limitation and make enablement/read-back a mandatory visibility-transition gate | OPEN | legitimate_safety_handling | Gate 4 | orchestrator | Pending |  |  |
| QUAL-001 | Qualification | Merge release-candidate preparation and run full qualification on the exact merged default-branch commit | OPEN | contract_test | Gate 5 | orchestrator | Pending |  |  |
| SCAN-001 | Neutrality | Run final checkout, artifact, Git, GitHub metadata, and completed-workflow scans with zero findings | OPEN | contract_test | Gate 5 | orchestrator | Pending |  |  |
| FINAL-001 | Closure | Terminalize every row and preserve the no-publication boundary | OPEN | plan_amendment | Gate 5 | orchestrator | Pending |  |  |

## Gates

| Gate | Requirement |
|---|---|
| Gate 0 | Exact repository, branch, dirty-state, PR, fixture, signing, and publication baselines recorded before writes. |
| Gate 1 | Core implementation merged through the protected pull-request path with exact-head green checks. |
| Gate 2 | Fixture-first fork integration and module PR merged with complete fork-local tests; public upstream drafts closed unmerged. |
| Gate 3 | Every bundled fixture has a fresh evidence-backed redistribution disposition. |
| Gate 4 | Durable keyless identity, release-candidate documentation, and visibility-transition security gate are implemented and tested. |
| Gate 5 | Exact merged default-branch qualification and all final scans pass; no publication action occurs. |

## Final report

All rows terminal: no.

Objective complete: no.

No repository visibility change, version tag, release, registry upload, or upstream MultiQC merge is authorized by this ledger.
