# sv-vcf-stats 1.1.0 performance and release ledger

Created: 2026-08-30T16:19:58Z

Controlling request: the user-supplied sv-vcf-stats 1.1.0 performance and release plan captured by this ledger.

Ledger path: docs/plans/20260830T161958Z_sv_vcf_stats_1_1_0_performance_release_ledger.md

Objective: make the existing thread option control HTSlib/BGZF input decompression, remove unnecessary per-record SQLite and rendering work, preserve all semantic and distribution contracts, merge through normal CI, publish annotated 1.1.0 with exactly one universal wheel plus SHA256SUMS, and merge a documentation-only receipt closeout.

## Scope and non-goals

- Preserve statistics, diagnostics, JSON schemas, CLI shapes, default threads=1, and serial Python semantic/cross-record analysis.
- No process sharding, per-contig workers, new dependencies, schema changes, compatibility aliases, output-strategy fields, dependency upgrades, broad refactors, external-pipeline changes, production reruns, PyPI, Conda, container, Apptainer, or Sigstore publication.
- Local validation is intentionally focused. Existing automatic PR CI may run unchanged.
- Any material expansion requires explicit user approval and a plan-amendment row before implementation.
- Approved amendment: add a repository-local, public-safe AGENTS.md and refresh README.md with restrained open-source styling inspired by the user-supplied rgbw_colorspace_converter reference. These documentation changes must not name any organization, disclose local operating instructions, copy reference prose or assets, or change runtime/release behavior.

## Multi-agent ownership

All branches start at origin/main commit da08f6808d6d4404451ce3244c98a5442cc57132. Only the lead edits this ledger or performs GitHub mutations.

| Owner | Model | Effort | Branch/worktree | Disjoint write scope |
|---|---|---:|---|---|
| Lead/integrator | gpt-5.6-sol | medium | codex/sv-vcf-stats-1-1-0-fast-stats | This ledger, integration-only conflict resolution, PR/release/closeout receipts |
| IO performance agent | gpt-5.6-sol | high | codex/sv-vcf-stats-1-1-0-io | src/vcf_sv_stats/io.py, engine.py, canonical.py, the minimum normalization.py thread propagation, and focused IO/render tests only |
| Event-store agent | gpt-5.6-terra | medium | codex/sv-vcf-stats-1-1-0-event-store | src/vcf_sv_stats/events.py and focused relationship/EventStore tests only |
| Evidence/release agent | gpt-5.6-luna | low | codex/sv-vcf-stats-1-1-0-evidence | tests/test_distribution_qualification.py, performance/threading and release documentation, bounded benchmark evidence only |

## Gate 0 baseline

- Fetch: git fetch --prune --tags origin completed 2026-08-30T16:10Z.
- Repository: public GitHub origin; default branch main.
- Current origin/main: da08f6808d6d4404451ce3244c98a5442cc57132, merge commit for PR #14.
- Latest annotated tag and GitHub Release: 1.0.1; tag object peels to fa3bc9228223d167d428d935ea85a25454b0dbd5; release published 2026-08-14T00:00:18Z.
- origin/main is two documentation/merge commits beyond 1.0.1. git diff --stat 1.0.1..origin/main reports only 13 additions and 12 deletions in the prior release ledger; no source, test, dependency, or workflow drift.
- Tag 1.1.0 is absent locally and remotely after the fetch. GitHub Release 1.1.0 is absent.
- A pre-existing checkout remains on stale codex/initial-implementation at 099c1b1dd2e1e6f6e7ba86a972fb82ab80cf03a6 and is explicitly excluded from implementation.
- The fresh lead and three agent worktrees are clean and start at exact origin/main.
- Thread path: cli.py validates the effective thread count and stores it in OperationRequest; engine._analyze does not pass request.threads to scan_variant; canonical.scan_variant calls io.open_variant(path); io.open_variant opens pysam.VariantFile(path, "r") without threads. The semantic scan is serial.
- Per-record work: canonical.scan_variant calls str(record) for every record and _raw_filter_state renders the record again; EventStore.add inserts one records row for every scanned record and indexes are created in EventStore.__init__ before ingestion.
- Existing production qualification evidence: docs/benchmarks/20260813_thread_matrix.json records CPU/wall ratios 1.007-1.017 at threads 1 and 10, and mean wall times 0.936 s versus 0.897 s. This is near-single-core behavior and proves only output invariance, not semantic multithreading.
- Release contract: origin/main .github/workflows/distribution.yml is a manual tag-only build of exactly one vcf_sv_stats-<tag>-py3-none-any.whl artifact. GitHub Release 1.0.1 contains exactly vcf_sv_stats-1.0.1-py3-none-any.whl and SHA256SUMS.
- Baseline limits: no production HG002, external-pipeline, cross-platform, or old ten-million-record campaign will be run.

## Control ledger

Statuses: OPEN, IN_PROGRESS, ATTEMPTING_BUGFIX, SUCCESS, DUPLICATE, NO_LONGER_NEEDED, FAIL, BLOCKED. Final acceptance requires no working status.

| ID | Area | Requirement | Status | Category | Approval gate | Owner | Evidence | Root cause | Terminal note |
|---|---|---|---|---|---|---|---|---|---|
| BASE-001 | Baseline | Re-fetch and record origin/main, latest tag/release, dirty files, and absence of 1.1.0 | SUCCESS | contract_test | Gate 0 | Lead | Fetch and exact refs/assets recorded above |  | Baseline is current and 1.1.0 is unused. |
| BASE-002 | Baseline | Use a fresh release worktree from origin/main and exclude the stale operator branch | SUCCESS | legitimate_safety_handling | Gate 0 | Lead | Four clean branches/worktrees at da08f6808d6d4404451ce3244c98a5442cc57132 |  | Fresh isolated worktrees created; stale checkout untouched. |
| BASE-003 | Baseline | Record no-op thread path, serial scan, all-record SQLite writes, duplicate rendering, and near-single-core evidence | SUCCESS | contract_test | Gate 0 | Lead | Source paths and 20260813 thread receipt summarized above |  | Current bottlenecks and semantic boundary are attributable. |
| BASE-004 | Baseline | Confirm one universal wheel plus SHA256SUMS release contract | SUCCESS | active_product_contract | Gate 0 | Lead | origin/main distribution workflow; GitHub Release 1.0.1 asset inventory |  | Existing distribution contract remains exactly two release assets. |
| AMEND-001 | Scope | Record explicit approval for public-safe AGENTS.md and low-key styled README.md refresh | SUCCESS | active_product_contract | Gate 3 | Lead | User instruction received while PR #17 CI was running |  | The documentation-only expansion is approved and bounded by the public-repository constraints above. |
| DOCS-001 | Documentation | Add repository-local open-source AGENTS.md with no organization-specific or local-only content | SUCCESS | active_product_contract | Gate 3 | Lead | AGENTS.md uses repository-relative setup, contracts, safety, focused proof, Git, and release guidance; forbidden and structural-neutrality scanners report zero findings |  | Guidance is suitable for a public checkout and contains no workstation layout or local operating runbook. |
| DOCS-002 | Documentation | Refresh README.md with restrained reference-inspired features without naming an organization | SUCCESS | active_product_contract | Gate 3 | Lead | README uses one five-color accent SVG, compact badges/navigation, accurate 1.1.0 threading/benchmark/install content, and corrected documentation links; 15 documentation/distribution tests, Ruff, SVG XML validation, both scanners, and diff check passed |  | The palette came from the user-specified public source; no source prose, imagery, name, or branding was copied. |
| PERF-001 | IO | Propagate OperationRequest.threads to pysam.VariantFile(..., threads=N), default 1, reject less than 1 | SUCCESS | feature_implementation | Gate 1 | IO performance agent | Integrated commit c726201; focused propagation/default/API+CLI rejection, VCF 4.5, BCF, and normalization checks in 22-test combined run |  | All owned input readers receive the requested count; output writing and Python semantics stay serial. |
| PERF-002 | Event store | Persist a row only for record ID, event ID, mate ID, or BND while retaining all diagnostics | SUCCESS | feature_implementation | Gate 1 | Event-store agent | Integrated commit fdf092f; tests/test_event_relationships.py plus existing malformed/relationship test -> 4 passed |  | Sparse insertion preserves duplicate, event, mate, orphan, reciprocal BND, and empty-graph results. |
| PERF-003 | Event store | Create EventStore indexes only after ingestion immediately before summarization | SUCCESS | feature_implementation | Gate 1 | Event-store agent | EventStore init has no indexes; summarize creates four IF NOT EXISTS indexes; focused lifecycle assertion passed |  | Index maintenance is deferred until immediately before summary queries. |
| PERF-004 | IO | Render each VCF record once and reuse raw FILTER/INFO fields | SUCCESS | feature_implementation | Gate 1 | IO performance agent | tests/test_io_performance.py render counter equals four records; canonical scan reuses one split record text |  | Raw FILTER and INFO fields are reused without output changes. |
| COMPAT-001 | Compatibility | Preserve serial semantics, schemas, dependencies, CLI shape, diagnostics, and output strategy | SUCCESS | active_product_contract | Gate 1 | Lead | Integrated diff has no schema, dependency, workflow, CLI-shape, or output-strategy changes; the Python scan and relationship resolution remain serial; thread 1/2/8 and normalized 1.0.1 parity checks passed |  | The approved implementation changes input decompression and removes redundant work without semantic or distribution drift. |
| TEST-001 | Validation | Candidate outputs at threads 1, 2, and 8 are identical subject to available CPUs | SUCCESS | contract_test | Gate 2 | Lead | Exact installed 1.1.0 candidate scanned the one-million-record gVCF at threads 1, 2, and 8; full JSON objects compare equal |  | Ten logical CPUs were available; all three outputs are identical. |
| TEST-002 | Validation | Candidate matches released 1.0.1 after producer-version and dependent payload-digest normalization | SUCCESS | contract_test | Gate 2 | Evidence/release agent | Fresh released 1.0.1 and exact candidate summaries match after common producer.version and removal of payload_sha256; normalized semantic SHA256 2c758bd603c64f6600bb47e05e9fc95fe2aa8a66ec68fce8c63e9480e2825ed2 |  | No semantic output drift exists beyond the approved producer version and dependent digest. |
| TEST-003 | Validation | Cover reciprocal cross-contig BNDs, orphan mates, duplicate IDs, explicit events, and reference-block-heavy gVCFs | SUCCESS | contract_test | Gate 2 | Event-store agent | tests/test_event_relationships.py and test_malformed_and_relationship_findings -> 4 passed in integrated worktree |  | Cross-contig reciprocal pair, orphan, duplicate, explicit event, BND without mate, and 1,000 reference blocks are covered. |
| TEST-004 | Validation | Run targeted pytest, Ruff touched files, mypy package, and no broad local suite | SUCCESS | contract_test | Gate 2 | Lead | Final integrated targeted pytest -> 32 passed in 3.15s; both raw benchmark receipts validated against streaming-benchmark schema; Ruff touched files passed; mypy 25 source files passed; git diff --check passed; no broad suite run |  | Focused local validation is green. |
| TEST-005 | Distribution | Replace only three stale broad-matrix assertions with one-wheel workflow assertions | SUCCESS | contract_test | Gate 2 | Evidence/release agent | tests/test_distribution_qualification.py retains the supported-target receipt test and replaces exactly three stale workflow tests; focused combined run -> 5 passed |  | One-wheel, exact-tag, and no-extra-format/signing contracts match origin/main workflow. |
| BENCH-001 | Benchmark | Run bounded indexed one-million-record 24-contig gVCF benchmark with two warm repetitions; enforce speed, thread, digest, and temp bounds | SUCCESS | contract_test | Gate 2 | Evidence/release agent | Schema-valid receipts docs/benchmarks/20260830T1628Z_bench-001_1.0.1.json and 20260830T1630Z_bench-001_1.1.0.json; medians 6,123,152,250 ns (1.0.1 t1), 4,590,473,958.5 ns (candidate t1), 4,591,697,875 ns (candidate t8); normalized semantic SHA256 2c758bd603c64f6600bb47e05e9fc95fe2aa8a66ec68fce8c63e9480e2825ed2 |  | Candidate t1 improved 25.030870%; t8 regressed only 0.026662% from candidate t1; peak temp was 31,633,408 bytes released and 32,768 bytes candidate, with zero final temp bytes. |
| PR-001 | Integration | Integrate disjoint patches into the clean release branch | SUCCESS | feature_implementation | Gate 3 | Lead | EventStore fdf092f, IO c726201, and evidence dfecd83/34382d3/46a64f4/f2f8130/1081536 cherry-picked without conflict |  | All disjoint agent slices are on the clean release branch. |
| PR-002 | Integration | Limit integrated changes to approved performance/threading, focused tests, and release documentation | SUCCESS | active_product_contract | Gate 3 | Lead | Final origin/main diff has 22 files: the approved 17-file performance/release slice plus AGENTS.md, README.md, docs/README.md, one decorative SVG, and one documentation-contract test from the explicit amendment; no workflow, dependency, schema, or external-pipeline changes |  | Final integrated scope matches the original plan plus AMEND-001 exactly. |
| PR-003 | Integration | Push branch and open a ready PR to main | SUCCESS | active_product_contract | Gate 3 | Lead | Ready PR #17 targets main from codex/sv-vcf-stats-1-1-0-fast-stats |  | Branch pushed normally and PR opened without bypass settings. |
| PR-004 | Integration | Resolve only attributable failures and merge normally after existing CI passes | SUCCESS | active_product_contract | Gate 3 | Lead | Exact final head 60f8671 passed all 10 PR checks across CI run 33323416344 and CodeQL run 33323414921; PR #17 was CLEAN/MERGEABLE and merged normally at 2026-08-30T16:48:45Z as b713b65f123c44e10f474c68fdf79d4aa1f78b78 | The new public ledger retained repository-local organization and workstation evidence that is not appropriate in a neutral public artifact. | The attributable content was removed without scanner/workflow weakening; no administrator bypass or force operation was used. |
| REL-001 | Release | Verify clean merged main contains exactly approved changes | SUCCESS | active_product_contract | Gate 4 | Lead | Fresh origin/main was exact b713b65f123c44e10f474c68fdf79d4aa1f78b78; its tree 08ef45d2685db3d8c2aad2f42b768e849bec92fb exactly matched final PR head and the baseline-to-main audit contained only the approved 22 files |  | Merged main is clean, attributable, and contains the original scope plus AMEND-001 only. |
| REL-002 | Release | Create/push annotated non-v 1.1.0 tag and verify object plus peeled commit | SUCCESS | active_product_contract | Gate 4 | Lead | Remote annotated tag object 620742fb525043b314532400851bb4d275edd764 peels to b713b65f123c44e10f474c68fdf79d4aa1f78b78; git cat-file -t returned tag |  | Non-v annotated tag 1.1.0 is published on the exact merged commit. |
| REL-003 | Release | Dispatch existing manual distribution workflow at tag 1.1.0 | SUCCESS | active_product_contract | Gate 4 | Lead | Manual GitHub release wheel run 33323533021 completed SUCCESS for head branch 1.1.0 and head SHA b713b65f123c44e10f474c68fdf79d4aa1f78b78 |  | Existing workflow built and uploaded the single github-release-wheel artifact. |
| REL-004 | Release | Require exact universal wheel, generate SHA256SUMS, and verify fresh anonymous installation | SUCCESS | contract_test | Gate 4 | Lead | Exact wheel vcf_sv_stats-1.1.0-py3-none-any.whl SHA256 5c85893705cad15ce3310799578ba89fc3e78b4259c3770f5de3a20f30da08f8; SHA256SUMS SHA256 b3cdc079d20f9a813de158ed700df8ff0f7ae880fb5343d954484347d95fe2de; anonymous public-URL Python 3.11 install reported 1.1.0 and verifier passed with semantic SHA256 cd822fdd9b129586333528e678ce6054640d197cd7fa2f0ca6f7c439238d30df |  | Anonymous bytes matched the staged workflow artifact; install receipt d3ff840ee98240ade9609a20d0b34b2b89f7f0fa742c6691c610d82d46a9f2f1 passed without GitHub credentials. |
| REL-005 | Release | Publish GitHub Release vcf-sv-stats 1.1.0 with only wheel and checksum | SUCCESS | active_product_contract | Gate 4 | Lead | GitHub Release vcf-sv-stats 1.1.0 published 2026-08-30T16:50:34Z at tag 1.1.0; uploaded asset inventory is exactly SHA256SUMS (102 bytes) and vcf_sv_stats-1.1.0-py3-none-any.whl (89,060 bytes) |  | Release is public, neither draft nor prerelease, and has no additional uploaded assets. |
| CLOSE-001 | Closeout | Merge one tiny documentation-only PR with post-release receipts and terminal ledger states | IN_PROGRESS | historical_docs_only | Gate 4 | Lead | Fresh codex/sv-vcf-stats-1-1-0-closeout branch starts at merged main b713b65 and changes only this ledger |  | Closeout PR URL, final-head CI, and normal merge remain pending. |

## Benchmark acceptance contract

- Input: generated, indexed, one-million-record, 24-contig, reference-block-heavy gVCF.
- Same host and exact input for installed released 1.0.1 and candidate 1.1.0.
- Two warm repetitions per configuration.
- Candidate threads=1 median wall time must improve by at least 20 percent versus 1.0.1.
- Candidate threads=8 median wall time must not regress more than 10 percent versus candidate threads=1.
- Normalize only producer version and its dependent payload digest for semantic comparison.
- Record bounded temporary storage. Do not run the old 10M matrix or any production input.

## Execution journal

- 2026-08-30T16:10Z: fetched origin and tags; confirmed the exact public source repository and main commit, latest 1.0.1 release, and absent 1.1.0.
- 2026-08-30T16:14Z: confirmed current operator checkout is stale; read origin/main directly and found the intended one-wheel release workflow.
- 2026-08-30T16:18Z: created lead and three agent worktrees from exact origin/main with disjoint branches and write scopes.
- 2026-08-30T16:19Z: Gate 0 terminal with four SUCCESS rows; no implementation started before this ledger.
- 2026-08-30T16:22Z: dispatched the three requested isolated workstreams with exact model/effort assignments and disjoint write ownership.
- 2026-08-30T16:28Z: integrated EventStore commit fdf092f; focused relationship tests passed 4/4 and Ruff passed on touched files.
- 2026-08-30T16:31Z: BENCH-001 entered ATTEMPTING_BUGFIX after the first focused generator test exposed an incorrect parsed-ID assertion; the generated raw row still uses ID dot.
- 2026-08-30T16:34Z: integrated the evidence commits; BENCH-001 bugfix passed, TEST-005 is terminal SUCCESS, and the corrected generator remains ready for candidate measurement.
- 2026-08-30T16:38Z: integrated IO commit c726201; combined targeted pytest passed 22 tests, Ruff passed all touched files, mypy passed 25 package files, and no broad local suite ran.
- 2026-08-30T16:43Z: TEST-001 and TEST-002 passed on the exact one-million-record input using fresh 1.0.1 and 1.1.0 wheel environments; thread 1/2/8 outputs are equal and normalized cross-version semantics match.
- 2026-08-30T16:44Z: integrated the two final evidence commits; BENCH-001 passed with a 25.030870 percent threads=1 improvement, 0.026662 percent threads=8 regression, semantic parity, and bounded temporary storage.
- 2026-08-30T16:45Z: final combined focused validation passed 32 tests, two receipt schema validations, Ruff, mypy across 25 package files, and git diff --check; COMPAT-001 and PR-002 are terminal SUCCESS.
- 2026-08-30T16:46Z: pushed the clean release branch and opened ready PR #17 to main; the existing unchanged PR CI now controls PR-004.
- 2026-08-30T16:48Z: user explicitly expanded scope to a public-safe repository AGENTS.md and a low-key reference-inspired README refresh; AMEND-001 records the authorization before either file is edited.
- 2026-08-30T16:49Z: PR #17 CI exposed one attributable root cause in two jobs: the structural neutrality scanner rejected local/internal evidence in the new ledger. PR-004 entered ATTEMPTING_BUGFIX; no scanner or workflow weakening is permitted.
- 2026-08-30T16:55Z: added the public AGENTS.md and restrained README styling amendment, updated current 1.1.0 installation/documentation assertions, removed local-only ledger evidence, and passed 15 focused tests, both token scanners, Ruff, SVG XML validation, and git diff --check. DOCS-001/002 are SUCCESS; PR-004 returned to IN_PROGRESS pending fresh CI.
- 2026-08-30T16:56Z: exact final PR head passed all 10 checks and PR #17 merged normally as b713b65; merged-main tree and 22-file scope audits passed.
- 2026-08-30T16:57Z: pushed annotated tag object 620742f for 1.1.0, verified its peeled merge commit, and completed manual tag workflow run 33323533021 successfully.
- 2026-08-30T16:58Z: required the exact one-wheel artifact, generated and verified SHA256SUMS, published the two-asset GitHub Release, and passed a credential-free public URL install plus embedded verifier.
- 2026-08-30T16:59Z: created the fresh documentation-only closeout branch from merged main; CLOSE-001 is the sole remaining working row.

## Final report

All rows terminal: no

Objective complete: no

Status counts: SUCCESS 27; OPEN 0; IN_PROGRESS 1; ATTEMPTING_BUGFIX 0; DUPLICATE 0; NO_LONGER_NEEDED 0; FAIL 0; BLOCKED 0.

Residual risks: only the documentation-only closeout PR CI and normal merge remain unproven.
