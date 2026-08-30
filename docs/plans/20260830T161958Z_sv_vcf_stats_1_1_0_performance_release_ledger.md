# sv-vcf-stats 1.1.0 performance and release ledger

Created: 2026-08-30T16:19:58Z

Controlling request: the user-supplied sv-vcf-stats 1.1.0 performance and release plan captured by this ledger.

Ledger path: docs/plans/20260830T161958Z_sv_vcf_stats_1_1_0_performance_release_ledger.md

Objective: make the existing thread option control HTSlib/BGZF input decompression, remove unnecessary per-record SQLite and rendering work, preserve all semantic and distribution contracts, merge through normal CI, publish annotated 1.1.0 with exactly one universal wheel plus SHA256SUMS, and merge a documentation-only receipt closeout.

## Scope and non-goals

- Preserve statistics, diagnostics, JSON schemas, CLI shapes, default threads=1, and serial Python semantic/cross-record analysis.
- No process sharding, per-contig workers, new dependencies, schema changes, compatibility aliases, output-strategy fields, dependency upgrades, broad refactors, DayOA/DYEC changes, production reruns, PyPI, Conda, container, Apptainer, or Sigstore publication.
- Local validation is intentionally focused. Existing automatic PR CI may run unchanged.
- Any material expansion requires explicit user approval and a plan-amendment row before implementation.

## Multi-agent ownership

All branches start at origin/main commit da08f6808d6d4404451ce3244c98a5442cc57132. Only the lead edits this ledger or performs GitHub mutations.

| Owner | Model | Effort | Branch/worktree | Disjoint write scope |
|---|---|---:|---|---|
| Lead/integrator | gpt-5.6-sol | medium | codex/sv-vcf-stats-1-1-0-fast-stats at /Users/jmajor/projects/lsmc/.codex-worktrees/sv-vcf-stats-1-1-0-fast-stats | This ledger, integration-only conflict resolution, PR/release/closeout receipts |
| IO performance agent | gpt-5.6-sol | high | codex/sv-vcf-stats-1-1-0-io at /Users/jmajor/projects/lsmc/.codex-worktrees/sv-vcf-stats-1-1-0-io | src/vcf_sv_stats/io.py, engine.py, canonical.py, the minimum normalization.py thread propagation, and focused IO/render tests only |
| Event-store agent | gpt-5.6-terra | medium | codex/sv-vcf-stats-1-1-0-event-store at /Users/jmajor/projects/lsmc/.codex-worktrees/sv-vcf-stats-1-1-0-event-store | src/vcf_sv_stats/events.py and focused relationship/EventStore tests only |
| Evidence/release agent | gpt-5.6-luna | low | codex/sv-vcf-stats-1-1-0-evidence at /Users/jmajor/projects/lsmc/.codex-worktrees/sv-vcf-stats-1-1-0-evidence | tests/test_distribution_qualification.py, performance/threading and release documentation, bounded benchmark evidence only |

## Gate 0 baseline

- Fetch: git fetch --prune --tags origin completed 2026-08-30T16:10Z.
- Repository: https://github.com/lsmc-bio/sv-vcf-stats.git; default branch main.
- Current origin/main: da08f6808d6d4404451ce3244c98a5442cc57132, Merge pull request #14 from lsmc-bio/codex/public-release-candidate.
- Latest annotated tag and GitHub Release: 1.0.1; tag object peels to fa3bc9228223d167d428d935ea85a25454b0dbd5; release published 2026-08-14T00:00:18Z.
- origin/main is two documentation/merge commits beyond 1.0.1. git diff --stat 1.0.1..origin/main reports only 13 additions and 12 deletions in the prior release ledger; no source, test, dependency, or workflow drift.
- Tag 1.1.0 is absent locally and remotely after the fetch. GitHub Release 1.1.0 is absent.
- The operator checkout /Users/jmajor/projects/lsmc/sv-vcf-stats is clean but remains on stale codex/initial-implementation at 099c1b1dd2e1e6f6e7ba86a972fb82ab80cf03a6; it is explicitly excluded from implementation.
- The fresh lead and three agent worktrees are clean and start at exact origin/main.
- Thread path: cli.py validates the effective thread count and stores it in OperationRequest; engine._analyze does not pass request.threads to scan_variant; canonical.scan_variant calls io.open_variant(path); io.open_variant opens pysam.VariantFile(path, "r") without threads. The semantic scan is serial.
- Per-record work: canonical.scan_variant calls str(record) for every record and _raw_filter_state renders the record again; EventStore.add inserts one records row for every scanned record and indexes are created in EventStore.__init__ before ingestion.
- Existing production qualification evidence: docs/benchmarks/20260813_thread_matrix.json records CPU/wall ratios 1.007-1.017 at threads 1 and 10, and mean wall times 0.936 s versus 0.897 s. This is near-single-core behavior and proves only output invariance, not semantic multithreading.
- Release contract: origin/main .github/workflows/distribution.yml is a manual tag-only build of exactly one vcf_sv_stats-<tag>-py3-none-any.whl artifact. GitHub Release 1.0.1 contains exactly vcf_sv_stats-1.0.1-py3-none-any.whl and SHA256SUMS.
- Baseline limits: no production HG002, DayOA, cross-platform, or old ten-million-record campaign will be run.

## Control ledger

Statuses: OPEN, IN_PROGRESS, ATTEMPTING_BUGFIX, SUCCESS, DUPLICATE, NO_LONGER_NEEDED, FAIL, BLOCKED. Final acceptance requires no working status.

| ID | Area | Requirement | Status | Category | Approval gate | Owner | Evidence | Root cause | Terminal note |
|---|---|---|---|---|---|---|---|---|---|
| BASE-001 | Baseline | Re-fetch and record origin/main, latest tag/release, dirty files, and absence of 1.1.0 | SUCCESS | contract_test | Gate 0 | Lead | Fetch and exact refs/assets recorded above |  | Baseline is current and 1.1.0 is unused. |
| BASE-002 | Baseline | Use a fresh release worktree from origin/main and exclude the stale operator branch | SUCCESS | legitimate_safety_handling | Gate 0 | Lead | Four clean branches/worktrees at da08f6808d6d4404451ce3244c98a5442cc57132 |  | Fresh isolated worktrees created; stale checkout untouched. |
| BASE-003 | Baseline | Record no-op thread path, serial scan, all-record SQLite writes, duplicate rendering, and near-single-core evidence | SUCCESS | contract_test | Gate 0 | Lead | Source paths and 20260813 thread receipt summarized above |  | Current bottlenecks and semantic boundary are attributable. |
| BASE-004 | Baseline | Confirm one universal wheel plus SHA256SUMS release contract | SUCCESS | active_product_contract | Gate 0 | Lead | origin/main distribution workflow; GitHub Release 1.0.1 asset inventory |  | Existing distribution contract remains exactly two release assets. |
| PERF-001 | IO | Propagate OperationRequest.threads to pysam.VariantFile(..., threads=N), default 1, reject less than 1 | IN_PROGRESS | feature_implementation | Gate 1 | IO performance agent | Agent dispatched in isolated IO worktree |  |  |
| PERF-002 | Event store | Persist a row only for record ID, event ID, mate ID, or BND while retaining all diagnostics | SUCCESS | feature_implementation | Gate 1 | Event-store agent | Integrated commit fdf092f; tests/test_event_relationships.py plus existing malformed/relationship test -> 4 passed |  | Sparse insertion preserves duplicate, event, mate, orphan, reciprocal BND, and empty-graph results. |
| PERF-003 | Event store | Create EventStore indexes only after ingestion immediately before summarization | SUCCESS | feature_implementation | Gate 1 | Event-store agent | EventStore init has no indexes; summarize creates four IF NOT EXISTS indexes; focused lifecycle assertion passed |  | Index maintenance is deferred until immediately before summary queries. |
| PERF-004 | IO | Render each VCF record once and reuse raw FILTER/INFO fields | IN_PROGRESS | feature_implementation | Gate 1 | IO performance agent | Agent dispatched in isolated IO worktree |  |  |
| COMPAT-001 | Compatibility | Preserve serial semantics, schemas, dependencies, CLI shape, diagnostics, and output strategy | OPEN | active_product_contract | Gate 1 | Lead | Integrated diff and parity checks pending |  |  |
| TEST-001 | Validation | Candidate outputs at threads 1, 2, and 8 are identical subject to available CPUs | OPEN | contract_test | Gate 2 | Lead | Pending focused thread-parity run |  |  |
| TEST-002 | Validation | Candidate matches released 1.0.1 after producer-version and dependent payload-digest normalization | IN_PROGRESS | contract_test | Gate 2 | Evidence/release agent | Agent dispatched to prepare and run released-wheel parity evidence |  |  |
| TEST-003 | Validation | Cover reciprocal cross-contig BNDs, orphan mates, duplicate IDs, explicit events, and reference-block-heavy gVCFs | SUCCESS | contract_test | Gate 2 | Event-store agent | tests/test_event_relationships.py and test_malformed_and_relationship_findings -> 4 passed in integrated worktree |  | Cross-contig reciprocal pair, orphan, duplicate, explicit event, BND without mate, and 1,000 reference blocks are covered. |
| TEST-004 | Validation | Run targeted pytest, Ruff touched files, mypy package, and no broad local suite | OPEN | contract_test | Gate 2 | Lead | Pending integrated focused checks |  |  |
| TEST-005 | Distribution | Replace only three stale broad-matrix assertions with one-wheel workflow assertions | IN_PROGRESS | contract_test | Gate 2 | Evidence/release agent | Agent dispatched for test-only workflow-contract patch |  |  |
| BENCH-001 | Benchmark | Run bounded indexed one-million-record 24-contig gVCF benchmark with two warm repetitions; enforce speed, thread, digest, and temp bounds | IN_PROGRESS | contract_test | Gate 2 | Evidence/release agent | Agent dispatched to prepare the bounded benchmark and later run it against the integrated candidate |  |  |
| PR-001 | Integration | Integrate disjoint patches into the clean release branch | OPEN | feature_implementation | Gate 3 | Lead | Pending agent commits |  |  |
| PR-002 | Integration | Limit integrated changes to approved performance/threading, focused tests, and release documentation | OPEN | active_product_contract | Gate 3 | Lead | Pending final diff audit |  |  |
| PR-003 | Integration | Push branch and open a ready PR to main | OPEN | active_product_contract | Gate 3 | Lead | Pending PR URL |  |  |
| PR-004 | Integration | Resolve only attributable failures and merge normally after existing CI passes | OPEN | active_product_contract | Gate 3 | Lead | Pending check and merge receipts |  |  |
| REL-001 | Release | Verify clean merged main contains exactly approved changes | OPEN | active_product_contract | Gate 4 | Lead | Pending merged commit audit |  |  |
| REL-002 | Release | Create/push annotated non-v 1.1.0 tag and verify object plus peeled commit | OPEN | active_product_contract | Gate 4 | Lead | Pending tag receipt |  |  |
| REL-003 | Release | Dispatch existing manual distribution workflow at tag 1.1.0 | OPEN | active_product_contract | Gate 4 | Lead | Pending workflow run receipt |  |  |
| REL-004 | Release | Require exact universal wheel, generate SHA256SUMS, and verify fresh anonymous installation | OPEN | contract_test | Gate 4 | Lead | Pending asset/install receipts |  |  |
| REL-005 | Release | Publish GitHub Release vcf-sv-stats 1.1.0 with only wheel and checksum | OPEN | active_product_contract | Gate 4 | Lead | Pending release URL and asset inventory |  |  |
| CLOSE-001 | Closeout | Merge one tiny documentation-only PR with post-release receipts and terminal ledger states | OPEN | historical_docs_only | Gate 4 | Lead | Pending closeout PR and merged commit |  |  |

## Benchmark acceptance contract

- Input: generated, indexed, one-million-record, 24-contig, reference-block-heavy gVCF.
- Same host and exact input for installed released 1.0.1 and candidate 1.1.0.
- Two warm repetitions per configuration.
- Candidate threads=1 median wall time must improve by at least 20 percent versus 1.0.1.
- Candidate threads=8 median wall time must not regress more than 10 percent versus candidate threads=1.
- Normalize only producer version and its dependent payload digest for semantic comparison.
- Record bounded temporary storage. Do not run the old 10M matrix or any production input.

## Execution journal

- 2026-08-30T16:10Z: fetched origin and tags; confirmed lsmc-bio/sv-vcf-stats, exact main, latest 1.0.1 release, and absent 1.1.0.
- 2026-08-30T16:14Z: confirmed current operator checkout is stale; read origin/main directly and found the intended one-wheel release workflow.
- 2026-08-30T16:18Z: created lead and three agent worktrees from exact origin/main with disjoint branches and write scopes.
- 2026-08-30T16:19Z: Gate 0 terminal with four SUCCESS rows; no implementation started before this ledger.
- 2026-08-30T16:22Z: dispatched the three requested isolated workstreams with exact model/effort assignments and disjoint write ownership.
- 2026-08-30T16:28Z: integrated EventStore commit fdf092f; focused relationship tests passed 4/4 and Ruff passed on touched files.

## Final report

All rows terminal: no

Objective complete: no

Status counts: SUCCESS 7; OPEN 13; IN_PROGRESS 5; ATTEMPTING_BUGFIX 0; DUPLICATE 0; NO_LONGER_NEEDED 0; FAIL 0; BLOCKED 0.

Residual risks: benchmark thresholds, PR CI, release workflow, anonymous install, and post-release closeout remain unproven.
