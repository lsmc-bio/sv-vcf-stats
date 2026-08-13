# `vcf-sv-stats` v1 implementation ledger

Date: 2026-08-13

## Control

- Controlling ledger: `docs/plans/20260813T065930Z_sv_vcf_stats_v1_implementation_ledger.md`
- Repository state at Gate 0: private GitHub repository, default branch `main`, implementation branch `codex/initial-implementation`
- Product boundary: public-neutral Python package and command named `vcf-sv-stats`
- Fixture boundary: derived HG002 records only; original source artifacts remain outside the repository and Git object database
- Publication boundary: repository remains private; the authorized upstream contribution is limited to two draft review pull requests; package, container, public visibility, upstream merge, and release tagging remain unauthorized

## Gate 0: inventory freeze

### Repository and access baseline

- Initial checkout: one tracked `README.md`; `git status --short --branch` reported a clean `codex/initial-implementation` branch.
- Repository visibility: private.
- Organization base permission: write.
- Administrative team permission: admin.
- `iamh2o` effective permission: admin and intended repository-wide CODEOWNER.
- Organization branch rules require pull requests and prohibit deletion and non-fast-forward updates on `main`.
- Code security, dependency security updates, secret scanning, non-provider patterns, validity checks, and push protection are enabled.

### Supplied-design and fixture baseline

- Design document SHA-256: `ee14fb01cd25fca8dbf482d6ec48c3585091a830b777d10a92acd2a4cfb4cd62`.
- Source archive SHA-256: `0ac50aac5e481a776f30cd17f4e5703934f889d6ec6a8b3cbbc2ebc7ac0d9c13`.
- VCF paths inspected: 22, representing 21 logical payload roles because one query payload is present in plain and compressed form.
- Identity evidence: one specimen `HG002`, one sample `HG002`, one library, two sequencing inputs, and one sample column per VCF. Every sample column resolves to `HG002`.
- Source access: local read-only files supplied by the user. No remote storage or compute system is required or authorized.
- Additional remote files used: zero. No remote filesystem, object storage, or cluster was inspected.
- Source-derived fixtures must be generated outside the checkout, sanitized, independently validated, and scanned before their first addition to Git.
- Generated corpus: 21 source-derived compressed VCF fixtures, one plain/compressed parity pair, one derived BCF, 1,186 source-derived records, and 180,037 compressed VCF bytes.
- Redistribution review: every fixture has the terminal status `reviewed-public-derived-data`; a public-release re-review remains mandatory.

### Toolchain baseline

- Host: Darwin arm64.
- System Python: 3.9.6, unsupported and therefore not used for implementation verification.
- Environment manager: `uv 0.11.16`; public CPython 3.11, 3.12, and 3.13 runtimes.
- Runtime dependencies: public package indexes only; `cli-core-yo 2.1.1`, `pysam 0.24.0`, and bundled HTSlib 1.23.1.
- Independent validator: bcftools 1.24 with HTSlib 1.24.
- Git: 2.50.1.
- GitHub CLI: 2.86.0, authenticated as `iamh2o`.
- Implementation tests: 101 tests pass on Python 3.11; the 3.11, 3.12, and 3.13 isolated matrices each pass.
- Coverage: 82 percent branch-aware line coverage, above the configured 70 percent floor.

### Source VCF digests

| Source role | SHA-256 |
|---|---|
| `dysgu.native.vcf.gz` | `1746c758d8a30b44abbcb7de67a24a1a4cb64a16c9efd776e5a3bd20ab827e1a` |
| `dysgu.normalized.vcf.gz` | `832b5071212d6d512b22f8bf595a5188cb84a666c0eb2ee3f8dbb26296a0a06e` |
| `jasmine.merged.vcf.gz` | `11d2d2d2be3d9c6e03ecb9ac0d16515d842a97c776eb0a626befe3b0c76448b8` |
| `manta.native.vcf.gz` | `18acfd53eeb4ffca0d30c2c4816de5b48b1d0d4980256599ed30a0522aa70be2` |
| `manta.normalized.vcf.gz` | `4363257a79ae4121ad025a79f897ccd038cc870ac39bcfcb9c8e662fcceaf24d` |
| `octopusv.merged.vcf.gz` | `b05375fe008755a0c533cd263a420e3c2b42110aef67dbcdf552e6fea81b4d97` |
| `sentieon.cnvscope.vcf.gz` | `c81e769963be14152c62e7e9b9f4de5774e0a01a610258198b0fcdb4ff0d3548` |
| `sentieon.longreadsv.native.vcf.gz` | `520d37333d86a1e2d26f0d8dd49df26cd7fe1ee544e0595f17584947c9f110b6` |
| `sentieon.longreadsv.normalized.vcf.gz` | `b67a19adc482d072d468e1026ee9b40e480d631c1278c5e221f91669716beabc` |
| `sniffles2.native.vcf.gz` | `d5ba5057f518bfaf1d907747adebbe203840f98e53b35e668e387e675563f549` |
| `sniffles2.normalized.vcf.gz` | `02bb7fa2af41fbc9b3aa78c310ea113a77060d36a70d9b65f84a3efda98aa065` |
| `survivor.merged.vcf.gz` | `a215fcc82267c257ff3d6d35a6acdf382e51f879e89371f6df09637881536670` |
| `tiddit.native.vcf.gz` | `e84e6099b70690b6fdfe47f34be01e110a8b855769339d7b2e8ffba55bbd8324` |
| `tiddit.normalized.vcf.gz` | `1bfa3c2588868a70b976975acf8c79f7c7b2fcb150f857603209f88b3b22a921` |
| `tiddit.reference-repaired.vcf.gz` | `003c0a8d786c45a36768dd864c00d1678a7a4d2a0540111d6fb7e07fefd076cd` |
| `trussv.merged.vcf.gz` | `838672a7542c8f99afee144875c8a6d826b32553b884e8d14b1d8e8088672ade` |
| `truvari.query.vcf.gz` | `2154caedee92a2acba7eb359daa97643efb5e89660798860f160119f9bdeb4ed` |
| `truvari.query.vcf` | `a7e85c37409c02ac8b94d923e3a14f5232f1ea438c1a59c9bad39fc85b0b0c45` |
| `truvari.fn.vcf.gz` | `acd3002d9a314469a26a06ac4b8e85b36e47a8a1f6e1bd8c67a6d459b72acf1a` |
| `truvari.fp.vcf.gz` | `0080f3c2d9cb39c3e5e323d3961695be742ba309821994acc5a684a307a0d787` |
| `truvari.tp-base.vcf.gz` | `2d813a064191a2ef085f53e89d44185417768f362f651a2436be52977f03d72a` |
| `truvari.tp-comp.vcf.gz` | `8751d3514e5579738dc8d6abc4bdad97a830611b1896a554caddd12085254f29` |

## Approval gates

| Gate | Requirement |
|---|---|
| Gate 0 | Inventory, source identities, digests, repository state, and product boundary recorded before runtime implementation. |
| Gate 1 | Neutral specification, API, CLI, schemas, and fixture tooling implemented with focused tests. |
| Gate 2 | Source-derived fixtures pass identity, redistribution, conformance, size, and neutral-content checks before Git staging. |
| Gate 3 | Full test, packaging, artifact, history, and GitHub metadata validation passes. |
| Gate 4 | All ledger rows terminal; branch committed and pushed; private pull request created. |

## Repository and product rows

| ID | Area | Requirement | Status | Category | Gate | Owner | Evidence | Root Cause | Terminal Note |
|---|---|---|---|---|---|---|---|---|---|
| REPO-001 | GitHub | Private repository created with neutral description | SUCCESS | feature_implementation | Gate 0 | orchestrator | GitHub repository inspection on 2026-08-13 |  | Private repository exists. |
| REPO-002 | Access | Organization members inherit write; administrative team and `iamh2o` have admin | SUCCESS | active_product_contract | Gate 0 | orchestrator | GitHub permission endpoints |  | Requested access verified. |
| REPO-003 | Ownership | `iamh2o` is repository-wide CODEOWNER | SUCCESS | feature_implementation | Gate 1 | orchestrator | `.github/CODEOWNERS` assigns `*` to `@iamh2o` |  | Repository-wide ownership rule is explicit. |
| REPO-004 | Security | Code security, dependency updates, secret scanning, and push protection enabled | SUCCESS | legitimate_safety_handling | Gate 0 | orchestrator | GitHub security settings |  | Enabled at repository or organization level. |
| REPO-005 | Security | Private vulnerability reporting enabled or exact platform limitation recorded | SUCCESS | legitimate_safety_handling | Gate 3 | orchestrator | Repository endpoint returns 404 while private; GitHub documents the feature for public repositories | Platform does not expose the feature for this private repository. | Exact limitation recorded; re-evaluate immediately before public visibility. |
| REPO-006 | CI | Public GitHub-hosted CI and dependency review configured | SUCCESS | feature_implementation | Gate 3 | orchestrator | Exact-commit run `31719216204` passed three Python jobs with 101 tests each, packaging, full container-layer audit, HTSlib 1.24 validation, and dependency review |  | Private draft pull-request CI is green. |
| PROD-001 | Neutrality | No organization-specific runtime, identity, path, domain, package, service, or branding dependency | SUCCESS | active_product_contract | Gate 3 | orchestrator | Neutral schemas, adapter URNs, config, local/stdin input gate, public lock files, structural scanner, and zero local findings |  | Hosting organization appears only in repository administration. |
| BRAND-002 | Neutrality | Prohibited company token absent from files, artifacts, history, and GitHub metadata | SUCCESS | contract_test | Gate 3 | orchestrator | Unexcepted hashed-token scan passed after run `31689711866` across checkout, nested artifacts, every reachable Git object, repository metadata, pull-request text, and all completed workflow logs; the CI image layer scan also passed |  | Zero findings across every required surface. |
| FIX-001 | Fixtures | All bundled source-derived fixtures are verified HG002-only | SUCCESS | contract_test | Gate 2 | orchestrator | `tools/verify_test_data.py`; 22 digest-bound source identity inspections; 21 derived fixtures; plain and BCF parity artifacts |  | Exactly one VCF/BCF sample named `HG002`; no other subject token. |
| FIX-002 | Fixtures | Fixture corpus obeys deterministic record and size budgets | SUCCESS | contract_test | Gate 2 | orchestrator | `test_data/manifest.json`: 1,186 records and 180,037 compressed VCF bytes; all fixtures 12 through 100 records |  | Below 2,500 records, 10 MiB, and 128-record closure caps. |
| FIX-003 | Fixtures | Headers, bodies, identifiers, relationships, indexes, and provenance are sanitized and valid | SUCCESS | contract_test | Gate 2 | orchestrator | External deterministic regeneration is byte-identical; fixture verifier and bcftools/HTSlib 1.24 validate all VCF/BCF files and indexes |  | Retained caller quirks remain explicit diagnostics, not silent repairs. |
| FIX-004 | Fixtures | Redistribution review recorded for every source-derived fixture | SUCCESS | legitimate_safety_handling | Gate 2 | orchestrator | `docs/fixture-governance.md`, `test_data/NOTICE.md`, and per-entry manifest status |  | Public-release re-review is an explicit later gate. |
| REL-001 | Publication | Repository remains private; no package, image, tag, visibility change, or upstream merge performed | SUCCESS | active_product_contract | Gate 4 | orchestrator | Private draft pull request `#1`; repository visibility `PRIVATE`; upstream module PR `MultiQC/MultiQC#3626` and fixture PR `MultiQC/test-data#385` remain drafts; no release, tag, package, image, merge, or visibility change |  | Authorized review artifacts exist while the pre-1.0 publication boundary remains preserved. |

## Neutralized acceptance criteria

| ID | Requirement | Status | Category | Gate | Owner | Evidence | Root Cause | Terminal Note |
|---|---|---|---|---|---|---|---|---|
| AC-001 | Valid generic SV VCF 4.5 selects the generic adapter and produces exact scoped statistics | SUCCESS | contract_test | Gate 1 | orchestrator | `test_generic_vcf45_sv_statistics_match_exact_scopes` |  | Exact record, allele, BND, event, and filter scopes pass. |
| AC-002 | Valid generic CNV VCF handles CN, genotype, gain, loss, neutral, and reference segments correctly | SUCCESS | contract_test | Gate 1 | orchestrator | `test_generic_vcf45_canonical_and_cnv_states` and fixture goldens |  | CN and genotype states remain factual; without explicit baseline, gain/loss/neutral inference is correctly unavailable and reference segments are separate. |
| AC-003 | Finalized VCF 4.5 SV, BND, multiallelic, local-allele, phasing, and cardinality constructs follow exact rules | SUCCESS | contract_test | Gate 1 | orchestrator | `tests/test_engine.py` finalized/invalid/version/phasing/local-allele/phase-set matrix; `vcf45.py` ploidy-aware A/R/G/P/LA/LR/LG validation; canonical VCF.gz and BCF tests; independent HTSlib 1.24 run `31719216204` |  | All 10 finalized-version, SV, cardinality, local-allele, phase, reference-block, writer, and independent-validation checkpoints pass. |
| AC-004 | Equivalent VCF.gz and BCF produce semantically identical canonical payloads and valid indexes | SUCCESS | contract_test | Gate 2 | orchestrator | `test_plain_compressed_and_bcf_semantic_parity`; bcftools/HTSlib 1.24 VCF/BCF/index validation |  | Canonical observations and statistics match; CSI is valid. |
| AC-005 | Unknown valid producer succeeds through an explicit generic adapter without inventing a caller | SUCCESS | contract_test | Gate 1 | orchestrator | `test_versioned_detection_and_generic_fallback` and generic 4.5 tests |  | Producer remains `unknown`. |
| AC-006 | Malformed fixture produces deterministic layered diagnostics and never equates parsing with conformance | SUCCESS | contract_test | Gate 1 | orchestrator | `test_malformed_and_relationship_findings`; fixture diagnostic goldens |  | Parser, conformance, semantics, safety, and completeness are distinct states. |
| AC-007 | Ambiguous producer evidence reports ranked alternatives and withholds named selection | SUCCESS | contract_test | Gate 1 | orchestrator | `test_ambiguous_and_untested_detection_are_safe` |  | Generic is selected and ranked candidates retained. |
| AC-008 | Untested producer versions are blocked or explicitly provisional and cannot authorize unproven rewrites | SUCCESS | contract_test | Gate 1 | orchestrator | Adapter tests and `test_unsafe_merged_rewrite_publishes_assessment_only` |  | Untested acceptance is provisional; unproven rewrite fails. |
| AC-009 | Reciprocal BND pair resolves two records and two breakends into one event | SUCCESS | contract_test | Gate 1 | orchestrator | Exact generic SV test; Manta native fixture golden |  | Two records and two breakends resolve to one relationship event. |
| AC-010 | Orphan, single, and ambiguous BNDs are counted without invented events | SUCCESS | contract_test | Gate 1 | orchestrator | Generic single-BND test and Sniffles2/Jasmine fixture goldens |  | Undeclared mates remain explicit unresolved breakends. |
| AC-011 | CNV/genotype matrix handles ploidy, phasing, missingness, CN, quality, baseline, and contradictions | SUCCESS | contract_test | Gate 1 | orchestrator | Generic CNV test and CNVscope fixture golden |  | Ploidy, phase, no-call, reference/alternate, CN, CNQ, and baseline-unavailable states are explicit; no biological contradiction is inferred without baseline context. |
| AC-012 | Manta 1.6.0 fixture detects supported adapter and preserves reciprocal relationships | SUCCESS | contract_test | Gate 2 | orchestrator | Manta native expected summary and adapter registry test |  | Fixture-relative relationship counts are exact. |
| AC-013 | Manta relationship damage is diagnosed; identifier rewrites are graph-preserving or refused | SUCCESS | contract_test | Gate 2 | orchestrator | Manta normalized expected diagnostics and normalization blocker tests |  | Stale mate references are diagnosed; representation-changing ID repair is refused. |
| AC-014 | TIDDIT 3.9.7 duplicate IDs, BND limitations, placeholders, and reference requirements are explicit | SUCCESS | contract_test | Gate 2 | orchestrator | TIDDIT native, normalized, and reference-repaired goldens; adapter descriptor |  | Duplicate IDs and undeclared mate limits remain diagnostics; reference repair requires an explicit reference. |
| AC-015 | dysgu 1.8.0 declarations, translocation convention, anchors, and exclusions are adapter-scoped | SUCCESS | contract_test | Gate 2 | orchestrator | dysgu native/normalized goldens and adapter descriptor |  | Producer fields remain adapter-scoped and declaration deviations explicit. |
| AC-016 | Sniffles2 2.8.0 insertion, deletion, and unpaired breakend states are correct | SUCCESS | contract_test | Gate 2 | orchestrator | Sniffles2 native/normalized goldens |  | Unpaired BNDs remain unresolved observations. |
| AC-017 | Sentieon LongReadSV 202503.03 multiallelic and phase-set deviations follow fixture goldens | SUCCESS | contract_test | Gate 2 | orchestrator | LongReadSV native/normalized goldens |  | Version detection and reserved phase declaration diagnostics are exact for the subset. |
| AC-018 | Sentieon CNVscope 202503.03 segments and filtered candidates do not inflate alternate CNV events | SUCCESS | contract_test | Gate 2 | orchestrator | CNVscope golden and CNV genotype-state implementation |  | Reference segments are distinct and candidate inconsistencies remain diagnostics. |
| AC-019 | Jasmine 1.1.5 retains source support and diagnoses invalid type/ALT combinations | SUCCESS | contract_test | Gate 2 | orchestrator | Jasmine merged golden and adapter descriptor |  | Support remains merger provenance; undeclared relationships are reported. |
| AC-020 | SURVIVOR 1.0.6 keeps bracket/type conventions and support provenance merger-scoped | SUCCESS | contract_test | Gate 2 | orchestrator | SURVIVOR merged golden and adapter descriptor |  | Bracket/type conflicts and support provenance stay merger-scoped. |
| AC-021 | OctopuSV 0.4.1 remains provisional with duplicate and relationship findings | SUCCESS | contract_test | Gate 2 | orchestrator | OctopuSV golden and adapter registry test |  | Provisional, rewrite-disabled status and diagnostics are exact. |
| AC-022 | TrusSV 0.3.1 remains provisional; legal missing IDs are retained and unsafe repair blocked | SUCCESS | contract_test | Gate 2 | orchestrator | TrusSV golden and unsafe rewrite assessment test |  | Missing IDs are preserved; adapter remains provisional and rewrite-disabled. |
| AC-023 | Merged/source comparison reports preserved and missing lineage without proposing unsafe reinsertion | SUCCESS | contract_test | Gate 2 | orchestrator | Closed source-manifest schema and immutable API; `tests/test_sources.py`; `test_data/source_manifests/trussv-manta.source-manifest.json`; fixture-relative comparison golden; JSON/JSONL/TSV reconciliation and canonical-rewrite safety tests |  | All seven checkpoints pass with digest-bound local sources and conservative `preserved`, `not_preserved`, `not_found`, and `ambiguous` outcomes; no reinsertion is proposed. |
| AC-024 | Unsupported Severus and separate Sentieon short-read SV identities are reported truthfully | SUCCESS | contract_test | Gate 1 | orchestrator | `test_registry_statuses_and_rewrite_policy` |  | Both remain distinct unsupported adapters with no substituted fixture. |
| AC-025 | Conservative normalization writes a new independently valid artifact without changing input bytes | SUCCESS | contract_test | Gate 1 | orchestrator | VCF.gz/BCF normalization parity test; input digest assertion; bcftools/HTSlib 1.24 validation |  | New data and index validate; source bytes remain unchanged. |
| AC-026 | Canonical multiallelic splitting remaps all declared cardinalities, genotypes, phase, IDs, and lineage | SUCCESS | contract_test | Gate 1 | orchestrator | `canonicalize.py`; `tests/test_normalize.py` lossless container-independent split, arbitrary-ploidy G/P projection, leading-phase behavior, graph/manifest reconciliation, parity, independent validation, and publication-boundary failure injection |  | All nine split planning, cardinality, local-allele, genotype, phase, graph, lineage, parity, and recovery checkpoints pass or refuse before publication when losslessness cannot be proved. |
| AC-027 | Unsafe merged rewrite fails with complete fixability assessment and no output data file | SUCCESS | contract_test | Gate 1 | orchestrator | `test_unsafe_merged_rewrite_publishes_assessment_only` |  | Assessment is published; data and index are absent. |
| AC-028 | Authorized loss applies only to named, known, applicable loss codes and is fully recorded | NO_LONGER_NEEDED | contract_test | Gate 1 | orchestrator | CLI and library reject every authorization because v1 defines no lossy transform | Conservative-only pre-1.0 implementation has no applicable loss code. | Reopen before introducing the first lossy transform; unknown and blanket authorization already fail. |
| AC-029 | Any output/input alias is rejected before writing and input/index digests remain unchanged | SUCCESS | contract_test | Gate 1 | orchestrator | Alias matrix covers lexical, hard-link, and symlink cases plus source/index digests |  | Preflight rejects all tested aliases. |
| AC-030 | Existing unrelated paths are rejected and force never recursively removes content | SUCCESS | contract_test | Gate 1 | orchestrator | Unowned file and unrelated-directory tests |  | Unrecognized content remains untouched. |
| AC-031 | Failure injection at publication boundaries yields deterministic recovery with no false-complete set | SUCCESS | contract_test | Gate 1 | orchestrator | Four rename boundaries, directory fsync, backup move, and replacement restore tests |  | No false-complete artifact set remains; verified prior set is restored. |
| AC-032 | Transformation manifest reconciles source mappings, identities, digests, and cardinalities | SUCCESS | contract_test | Gate 1 | orchestrator | Normalization digest-graph test and exact schema validation |  | Source/output/index/reference/schema/adapter identities and record mappings reconcile. |
| AC-033 | Statistics goldens define scope, denominator, unit, comparability, missingness, inference, and bins | SUCCESS | contract_test | Gate 1 | orchestrator | 21 fixture goldens, metric-contract assertions, exact generic SV/CNV tests |  | Fixture-relative values and versioned bin policy are deterministic. |
| AC-034 | Generic multi-analysis-unit context preserves distinct IDs and maps VCF samples only explicitly | SUCCESS | contract_test | Gate 1 | orchestrator | `test_multiple_analysis_units_remain_distinct` and sample-mapping conflict test |  | Generic IDs and explicit mappings remain separate. |
| AC-035 | Missing identity context permits callset statistics with unresolved status and no inference | SUCCESS | contract_test | Gate 1 | orchestrator | Inspection/statistics deterministic test and filename non-inference test |  | Callset statistics remain available with unresolved analysis context. |
| AC-036 | Repeated runs and thread variation preserve canonical payloads and normalized semantic content | SUCCESS | contract_test | Gate 3 | orchestrator | Repeated stats, 1/max-thread payload, normalized-byte tests, and benchmark repetitions |  | Deterministic payloads and normalized bytes match. |
| AC-037 | Every JSON artifact validates against its exact embedded schema and version policy | SUCCESS | contract_test | Gate 1 | orchestrator | Embedded 2020-12 schemas, artifact tests, unknown schema/major rejection, MultiQC consumer tests |  | Emitted v1 artifacts validate before publication. |
| AC-038 | Discrepancies output is exhaustive, deterministic, non-mutating, and published before fail-on exit | SUCCESS | contract_test | Gate 1 | orchestrator | JSON/JSONL/TSV count reconciliation, input digest check, CLI fail-on test |  | Report publication precedes policy exit. |
| AC-039 | Native MultiQC contract discovers only schema-valid, digest-bound summaries, separates identities, and rejects duplicates | SUCCESS | contract_test | Gate 3 | orchestrator | Draft module PR `MultiQC/MultiQC#3626` and companion data PR `MultiQC/test-data#385`; 12 focused tests, two strict generic module tests against the companion branch, 1,000-report case, 11 sections, `prek`, Ruff, and passing upstream lint/integration/Python 3.9 typing checks; baseline run `31105750315` reproduces the Python 3.14 typing failure outside this module |  | All nine native-module checkpoints pass. The two whole-project red statuses are explicitly external: test-data merge ordering and the reproduced pre-existing typing failure; neither draft was merged or shipped. |
| AC-040 | Performance matrix demonstrates bounded memory, relative scaling, determinism, and interruption safety | SUCCESS | contract_test | Gate 3 | orchestrator | `docs/benchmarks/20260813_streaming_qualification.md` plus digest-bound streaming, thread, recovery, and input-manifest receipts on commit `d8222f4cd10241de42ec006716234ad6781e4851` |  | All 11 checkpoints pass: 2M/1M wall 2.035x, temporary bytes 2.001x, 10M/1M RSS 0.995x, baseline 2.33x-6.12x, invariant thread payloads, and no output after SIGINT, SIGTERM, file limit, or SIGKILL. |
| AC-041 | Wheel, source archive, Conda package, OCI image, and Apptainer candidate install offline, run non-root where applicable, and contain no reference | SUCCESS | contract_test | Gate 3 | orchestrator | Exact-commit distribution run `31719216231`: 24 offline wheel/source install receipts across Linux/macOS, x86_64/arm64, Python 3.11-3.13; local-channel Conda install; multi-architecture OCI audit/SBOM/provenance; Apptainer 1.5.3 smoke; candidate scans |  | All 12 qualification checkpoints pass without uploading a package/image or creating a tag; publication still requires explicit approval. |
| AC-042 | Documentation explains record/event scope, VCF sample/analysis unit, adapters, references, losses, privacy, and recovery | SUCCESS | feature_implementation | Gate 3 | orchestrator | Showcase README; documentation map; architecture, command, output, operator, testing, fixture, and MultiQC guides; executable documentation-contract tests |  | README fixture output, relative links, examples, 20 command paths, 13 adapters, corpus totals, and dependency claims are bound to executable evidence; known pre-1.0 gaps remain explicit. |

## Quantitative completion audit

Audit date: 2026-08-13.

### Scope and scoring method

This audit compares the supplied design document identified by the Gate 0
SHA-256, the neutral normative contract, every original ledger row, current
source and tests, and exact-commit CI evidence. Requirements deliberately
removed by the approved neutral-product boundary are not counted as gaps.
Private empirical totals that were deliberately replaced with fixture-relative
expectations are likewise scored against the approved fixture contract.

The score measures acceptance completion, not estimated engineering effort:

1. The baseline denominator is the 55 original rows: 13 repository/product
   rows and AC-001 through AC-042. Every row has equal weight in the total.
2. A `SUCCESS` row receives 100% only where its cited evidence satisfies the
   approved neutralized row. AC-028 also receives 100% because the specified
   lossy feature was deliberately removed and its fail-closed disposition is
   complete.
3. Each formerly partial feature was decomposed into explicit acceptance
   checkpoints. Its percentage is satisfied checkpoints divided by total
   checkpoints. Displayed percentages are rounded; roll-ups use the exact
   fractions.
4. The completion-work rows below do not change the denominator. They turn the
   six gaps into executable work and prevent the percentage from improving by
   merely adding planning rows.
5. Terminality and completion remain separate measures. All 55 baseline rows
   are terminal and all 55 satisfy their approved disposition.

### Roll-up

| Scope | Rows | Rows at 100% | Completion points | Completion |
|---|---:|---:|---:|---:|
| Repository, access, security, fixtures, and current private-release boundary | 13 | 13 | 1,300 / 1,300 | 100.0% |
| Feature acceptance AC-001 through AC-042 | 42 | 42 | 4,200 / 4,200 | 100.0% |
| **Total baseline plan** | **55** | **55** | **5,500 / 5,500** | **100.0%** |
| Baseline terminal dispositions | 55 | 55 terminal | 55 / 55 | 100.0% terminal and complete |

The target of 5,500 / 5,500 points is met. AC-003, AC-023, AC-026, AC-039,
AC-040, and AC-041 each reached their fixed checkpoint denominator without
expanding or weakening another baseline row.

### Feature-family completion

| Feature family | Baseline rows | Completion |
|---|---|---:|
| Generic standards, validation, BND, CNV, and genotype behavior | AC-001 through AC-011 | 100.0% |
| Caller and merger adapters, fixtures, and source comparison | AC-012 through AC-024 | 100.0% |
| Normalization, loss policy, alias safety, transactions, and manifests | AC-025 through AC-032 | 100.0% |
| Statistics, analysis context, determinism, schemas, and discrepancies | AC-033 through AC-038 | 100.0% |
| Native aggregate-report module | AC-039 | 100.0% |
| Performance and interruption qualification | AC-040 | 100.0% |
| Offline and multi-platform distribution qualification | AC-041 | 100.0% |
| Documentation | AC-042 | 100.0% |

### All-row scorecard

The main ledger tables remain authoritative for requirements and evidence; this
scorecard makes the completion arithmetic explicit for every baseline row.

| ID | Terminal status | Satisfied checkpoints | Completion |
|---|---|---:|---:|
| REPO-001 | SUCCESS | 1 / 1 | 100% |
| REPO-002 | SUCCESS | 1 / 1 | 100% |
| REPO-003 | SUCCESS | 1 / 1 | 100% |
| REPO-004 | SUCCESS | 1 / 1 | 100% |
| REPO-005 | SUCCESS | 1 / 1 | 100% |
| REPO-006 | SUCCESS | 1 / 1 | 100% |
| PROD-001 | SUCCESS | 1 / 1 | 100% |
| BRAND-002 | SUCCESS | 1 / 1 | 100% |
| FIX-001 | SUCCESS | 1 / 1 | 100% |
| FIX-002 | SUCCESS | 1 / 1 | 100% |
| FIX-003 | SUCCESS | 1 / 1 | 100% |
| FIX-004 | SUCCESS | 1 / 1 | 100% |
| REL-001 | SUCCESS | 1 / 1 | 100% |
| AC-001 | SUCCESS | 1 / 1 | 100% |
| AC-002 | SUCCESS | 1 / 1 | 100% |
| AC-003 | SUCCESS | 10 / 10 | 100% |
| AC-004 | SUCCESS | 1 / 1 | 100% |
| AC-005 | SUCCESS | 1 / 1 | 100% |
| AC-006 | SUCCESS | 1 / 1 | 100% |
| AC-007 | SUCCESS | 1 / 1 | 100% |
| AC-008 | SUCCESS | 1 / 1 | 100% |
| AC-009 | SUCCESS | 1 / 1 | 100% |
| AC-010 | SUCCESS | 1 / 1 | 100% |
| AC-011 | SUCCESS | 1 / 1 | 100% |
| AC-012 | SUCCESS | 1 / 1 | 100% |
| AC-013 | SUCCESS | 1 / 1 | 100% |
| AC-014 | SUCCESS | 1 / 1 | 100% |
| AC-015 | SUCCESS | 1 / 1 | 100% |
| AC-016 | SUCCESS | 1 / 1 | 100% |
| AC-017 | SUCCESS | 1 / 1 | 100% |
| AC-018 | SUCCESS | 1 / 1 | 100% |
| AC-019 | SUCCESS | 1 / 1 | 100% |
| AC-020 | SUCCESS | 1 / 1 | 100% |
| AC-021 | SUCCESS | 1 / 1 | 100% |
| AC-022 | SUCCESS | 1 / 1 | 100% |
| AC-023 | SUCCESS | 7 / 7 | 100% |
| AC-024 | SUCCESS | 1 / 1 | 100% |
| AC-025 | SUCCESS | 1 / 1 | 100% |
| AC-026 | SUCCESS | 9 / 9 | 100% |
| AC-027 | SUCCESS | 1 / 1 | 100% |
| AC-028 | NO_LONGER_NEEDED | 1 / 1 | 100% |
| AC-029 | SUCCESS | 1 / 1 | 100% |
| AC-030 | SUCCESS | 1 / 1 | 100% |
| AC-031 | SUCCESS | 1 / 1 | 100% |
| AC-032 | SUCCESS | 1 / 1 | 100% |
| AC-033 | SUCCESS | 1 / 1 | 100% |
| AC-034 | SUCCESS | 1 / 1 | 100% |
| AC-035 | SUCCESS | 1 / 1 | 100% |
| AC-036 | SUCCESS | 1 / 1 | 100% |
| AC-037 | SUCCESS | 1 / 1 | 100% |
| AC-038 | SUCCESS | 1 / 1 | 100% |
| AC-039 | SUCCESS | 9 / 9 | 100% |
| AC-040 | SUCCESS | 11 / 11 | 100% |
| AC-041 | SUCCESS | 12 / 12 | 100% |
| AC-042 | SUCCESS | 1 / 1 | 100% |

### Formerly partial-row closure basis

| ID | Completed checkpoint set | Terminal evidence |
|---|---|---|
| AC-003 | Declared-version and draft gating; exact finalized SV fields; A/R/G/P/LA/LR/LG; local alleles; PSL/PSO/PSQ and PS conflicts; FORMAT LEN; reference blocks; complete synthetic matrix; VCF.gz/BCF writer validation | Finalized and invalid matrices in `tests/test_engine.py`, canonical tests, and HTSlib 1.24 validation |
| AC-023 | Closed source manifest; local digest/index/alias safety; ordered source validation; conservative comparator; four explicit outcomes; API/CLI/discrepancy integration; goldens and rewrite gate | `tests/test_sources.py`, embedded schema, source manifest, and fixture-relative comparison golden |
| AC-026 | Immutable split plan; deterministic IDs; A/R/G/P/LA/LR/LG and local-allele remapping; GT and phase preservation/refusal; graph closure; lineage; parity and recovery | `canonicalize.py` and focused canonical, arbitrary-ploidy, parity, HTSlib, graph, manifest, and failure-injection tests |
| AC-039 | Native discovery/parser/module; all sections; context matrix; 1,000-report behavior; strict checks; documentation; compatibility and maintenance commitment; draft upstream review | Draft PRs `MultiQC/MultiQC#3626` and `MultiQC/test-data#385`, focused and strict integration tests, and documented coupled-PR/baseline check disposition |
| AC-040 | Neutral generators; complete receipts; representative and large matrix; scaling/RSS/baseline limits; thread invariance; signal/resource/crash behavior; report | `docs/benchmarks/20260813_streaming_qualification.md` and three digest-bound qualification receipts |
| AC-041 | Network-free verifier; 24 install receipts; Conda; OCI and Apptainer; SPDX/CycloneDX; checksums; Sigstore/SLSA evidence; inventories; release guide; exact-candidate scans | Exact-commit distribution run `31719216231` and `docs/distribution.md`; no publication action |

## Completion work ledger

These rows record the executed path from the measured 92.3% baseline to 100%.
They remain ordered by dependency. Every `SUCCESS` row cites terminal
acceptance evidence; code presence or effort spent did not earn partial credit.

Shared row fields are explicit: the owner is `orchestrator`; the category is
`feature_implementation` except COMP-039-01, which is
`legitimate_safety_handling`, and COMP-FINAL-02, which is `contract_test`.
COMP-039-01's former external-write blocker was removed by the user's explicit
direction to take all six features to 100%. That authorization covered draft
review contributions only; upstream merge and release publication remain out
of scope. No working status remains.

### Wave 1: finalized standards and source evidence

| ID | Parent | Work item | Status | Gate | Terminal acceptance evidence |
|---|---|---|---|---|---|
| COMP-003-01 | AC-003 | Add a neutral synthetic finalized/draft VCF version matrix covering every named 4.4/4.5 SV construct | SUCCESS | Gate 1 | `tests/test_engine.py` covers all ten AC-003 checkpoint groups with exact positive and negative findings. |
| COMP-003-02 | AC-003 | Implement declared-version dispatch and reject unsupported finalized or draft claims | SUCCESS | Gate 1 | `test_draft_and_future_vcf_versions_do_not_pass_as_finalized` proves supported 4.5 and fail-closed draft/future behavior. |
| COMP-003-03 | AC-003 | Implement exact symbolic ALT, deprecated `SVTYPE`/`END`, positive allele-specific `SVLEN`, `SVCLAIM`, and `EVENTTYPE` rules | SUCCESS | Gate 1 | Finalized valid/invalid matrix tests prove each rule and deterministic compatibility diagnostic. |
| COMP-003-04 | AC-003 | Replace basic cardinality checks with a ploidy-aware Number A/R/G/P/LA/LR/LG engine | SUCCESS | Gate 1 | Engine and canonical property tests cover haploid, diploid, polyploid, multiallelic, missing, and malformed values. |
| COMP-003-05 | AC-003 | Validate local alleles, PSL/PSO/PSQ, PS conflicts, FORMAT LEN, and `<*>`/`<NON_REF>` reference blocks | SUCCESS | Gate 1 | Local-allele, prefix-phasing, disk-backed phase-set, symbolic-length, and reference-block tests pass. |
| COMP-003-06 | AC-003 | Complete target-4.5 writer validation and close the full synthetic matrix | SUCCESS | Gate 1 | Canonical VCF.gz/BCF outputs pass embedded strict checks, parity tests, and independent HTSlib 1.24 validation; AC-003 is 10/10. |
| COMP-023-01 | AC-023 | Add closed source-manifest schema, immutable API model, and embedded schema identity | SUCCESS | Gate 1 | Embedded `source-manifest-1.0.0` schema and tests accept only ordered, unique, digest-bound local sources. |
| COMP-023-02 | AC-023 | Add discrepancies/normalize/run CLI and API inputs with locality, digest, index, and alias safety | SUCCESS | Gate 1 | `tests/test_sources.py` rejects missing, changed, remote, duplicate/order/adapter, symlink, hard-link, and output-alias cases. |
| COMP-023-03 | AC-023 | Implement conservative source-to-merged allele, endpoint, ID, mate, and support-order comparison | SUCCESS | Gate 2 | `sources.py` emits deterministic source keys and never infers a missing counterpart or topology. |
| COMP-023-04 | AC-023 | Emit explicit `preserved`, `not_preserved`, `not_found`, and `ambiguous` outcomes in structured discrepancies | SUCCESS | Gate 2 | JSON, JSONL, TSV, and API counts reconcile; the fixture golden contains explicit conservative outcomes and no safe-reinsertion proposal. |
| COMP-023-05 | AC-023 | Bind comparison to merged normalization safety and fixture-relative goldens | SUCCESS | Gate 2 | Supported comparison golden passes and missing comparison dimensions block canonical rewrite with exact fixability; AC-023 is 7/7. |

### Wave 2: canonical multiallelic normalization

| ID | Parent | Work item | Status | Gate | Terminal acceptance evidence |
|---|---|---|---|---|---|
| COMP-026-01 | AC-026 | Implement a two-pass immutable split plan with deterministic source keys and collision-checked IDs | SUCCESS | Gate 1 | Repeated plans are byte-identical; deterministic IDs are collision checked and alias preflight remains mandatory. |
| COMP-026-02 | AC-026 | Remap INFO/FORMAT Number A and R values and their declarations | SUCCESS | Gate 1 | Canonical split tests reconcile every A/R value and missing state to one selected source allele. |
| COMP-026-03 | AC-026 | Remap Number G and P values for arbitrary supported ploidy | SUCCESS | Gate 1 | `test_canonical_g_and_p_projection_supports_arbitrary_ploidy` covers haploid, diploid, polyploid, and invalid cardinality. |
| COMP-026-04 | AC-026 | Remap LAA plus Number LA/LR/LG fields, GT indexes, separators, and PSL/PSO/PSQ state | SUCCESS | Gate 1 | Lossless local-allele and phase tests pass; unrepresentable BCF leading-phase state refuses before publication. |
| COMP-026-05 | AC-026 | Rewrite every ID, mate/event reference, event count, and transformation-manifest lineage entry coherently | SUCCESS | Gate 1 | Graph closure, unique IDs, mappings, cardinality totals, and resolved-event totals reconcile in the transformation manifest. |
| COMP-026-06 | AC-026 | Run VCF/BCF parity, independent HTSlib, round-trip, failure-injection, and deterministic golden tests | SUCCESS | Gate 3 | Output, index, manifest, and receipt artifacts pass parity, HTSlib 1.24, determinism, and failure-injection checks; AC-026 is 9/9. |

### Wave 3: native reporting, performance, and distributions

| ID | Parent | Work item | Status | Gate | Terminal acceptance evidence |
|---|---|---|---|---|---|
| COMP-039-01 | AC-039 | Obtain explicit approval to modify the external upstream repository and open a pull request | SUCCESS | Gate 3 | The 2026-08-13 user request explicitly directs all six incomplete features to 100%, quotes the upstream-write blocker, and therefore authorizes the AC-039 contribution scope. No merge or release publication is authorized. |
| COMP-039-02 | AC-039 | Refresh the current official module API, license, version, and test requirements | SUCCESS | Gate 3 after COMP-039-01 | Current upstream main, module conventions, license, strict test workflows, and Python 3.9/3.14 matrix were reviewed; the consumer imports no producer runtime. |
| COMP-039-03 | AC-039 | Implement native discovery, schema/digest validation, identity mapping, and duplicate handling | SUCCESS | Gate 3 after COMP-039-01 | Module tests match the producer reference for accepted, duplicate, conflicting, malformed, and unknown-major inputs. |
| COMP-039-04 | AC-039 | Implement the required overview, type, length, filter, breakend, CN/genotype, support, validation, and normalization sections | SUCCESS | Gate 3 after COMP-039-01 | The native module renders 11 typed sections while preserving grains, denominators, missingness, producer facets, and non-accuracy wording. |
| COMP-039-05 | AC-039 | Add minimized goldens for every required callset/context state and a 1,000-report aggregate case | SUCCESS | Gate 3 after COMP-039-01 | Unknown, CNV, merged, multi-unit, unresolved, invalid, normalized, optional-context, module-render, and deterministic 1,000-report tests pass. |
| COMP-039-06 | AC-039 | Pass current strict/lint/type/unit/snapshot checks and prepare docs, compatibility policy, maintainer commitment, and approved draft PR | SUCCESS | Gate 3 after COMP-039-01 | Twelve focused tests, two generic strict tests against companion data, `prek`, Ruff, upstream lint/integration/Python 3.9 typing, docs, policy, commitment, and both draft PRs pass the module scope. Whole-project red statuses are documented companion-merge ordering and an unrelated Python 3.14 typing failure reproduced by baseline run `31105750315`. |
| COMP-040-01 | AC-040 | Add deterministic neutral generators for representative, multi-sample, long-contig, high-sample, 1M, 2M, and 10M inputs | SUCCESS | Gate 3 | Seed/version-bound synthetic generators and manifests cover all seven classes without source-derived records. |
| COMP-040-02 | AC-040 | Expand the benchmark receipt to hardware, filesystem, cache state, tool/native versions, compression, CPU, temporary peak, and input/output dimensions | SUCCESS | Gate 3 | Exact schema receipts contain the full environment and measurement contract; tests reject incomplete or path-sensitive receipts. |
| COMP-040-03 | AC-040 | Run the complete synthetic and fixture-relative representative matrix | SUCCESS | Gate 3 | Seven input classes have repeated fresh-process measurements and deterministic payload checks; fixture CI smoke remains green. |
| COMP-040-04 | AC-040 | Prove the 1M-to-2M wall-time and temporary-byte scaling thresholds | SUCCESS | Gate 3 | Observed wall ratio 2.035 <= 2.5 and temporary-byte ratio 2.001 <= 2.2. |
| COMP-040-05 | AC-040 | Prove the 10M-to-1M peak-RSS threshold | SUCCESS | Gate 3 | Observed peak-RSS ratio 0.995 <= 2.0; 10M median runtime is 95.930 seconds at 60.84 MiB peak RSS. |
| COMP-040-06 | AC-040 | Compare representative classes with a pinned minimal pysam scan and verify thread-count determinism | SUCCESS | Gate 3 | Full/minimal-reader factor is 2.33x-6.12x <= 20x and all supported thread counts emit the same payload digest. |
| COMP-040-07 | AC-040 | Exercise SIGINT, SIGTERM, resource-limit, and crash recovery and publish a checked-in benchmark report | SUCCESS | Gate 3 | SIGINT, SIGTERM, 512-byte file limit, and SIGKILL leave no final/transient output; checked-in report closes AC-040 at 11/11. |
| COMP-041-01 | AC-041 | Add a network-free `verify-install` procedure with embedded generic VCF/BCF semantic parity | SUCCESS | Gate 3 | Installed verifier creates private neutral VCF.gz/BCF inputs, validates/normalizes both, and proves semantic parity with no network. |
| COMP-041-02 | AC-041 | Run offline wheel/source installation across every claimed Python, OS, and architecture target | SUCCESS | Gate 3 | Run `31719216231` aggregates exactly 24 receipts for Linux/macOS, x86_64/arm64, Python 3.11-3.13, and both install channels. |
| COMP-041-03 | AC-041 | Add a behavior-neutral Bioconda recipe and local recipe tests | SUCCESS | Gate 3 | Public-source recipes build in a temporary local channel; the main Conda package installs offline and passes the verifier. |
| COMP-041-04 | AC-041 | Build digest-bound multi-architecture OCI images and run Docker plus Apptainer read-only/non-root smokes | SUCCESS | Gate 3 | Linux amd64/arm64 images and Apptainer 1.5.3 pass non-root, no-network/read-only smokes with no bundled reference or writable application directory. |
| COMP-041-05 | AC-041 | Complete SPDX and CycloneDX inventories for Python, native libraries, container, dependencies, and fixtures | SUCCESS | Gate 3 | SPDX/CycloneDX inventories reconcile to locks, images, notices, fixture manifest, and redistribution review. |
| COMP-041-06 | AC-041 | Produce checksums, Sigstore-compatible attestations, and SLSA-style provenance for exact candidate artifacts | SUCCESS | Gate 3 | Candidate evidence binds commit, workflow, wheel, source archive, OCI index, per-platform SBOM/provenance, and checksums; ephemeral Cosign verification passes. |
| COMP-041-07 | AC-041 | Run final offline artifact/install/neutrality verification and document release commands and approvals | SUCCESS | Gate 3 | Candidate and product-owned image scans have zero findings; distribution guide records commands and approvals; AC-041 is 12/12 with no publication/tag. |

### Final closure

| ID | Parent | Work item | Status | Gate | Terminal acceptance evidence |
|---|---|---|---|---|---|
| COMP-FINAL-01 | Six partial ACs | Reconcile each completed work row to its parent checkpoint count and terminal evidence | SUCCESS | Gate 4 | AC-003, AC-023, AC-026, AC-039, AC-040, and AC-041 show exact evidence and fixed-denominator scores of 10/10, 7/7, 9/9, 9/9, 11/11, and 12/12. |
| COMP-FINAL-02 | Full plan | Run all supported Python, HTSlib, fixture, schema, docs, package, container, recovery, performance, and content/history/metadata checks | SUCCESS | Gate 4 | Exact-commit CI `31719216204`, distribution run `31719216231`, checked-in benchmark/recovery receipts, local 101-test suite, HTSlib 1.24, fixture verifier, and zero-finding scanners pass. |
| COMP-FINAL-03 | Full plan | Recompute the fixed 55-row denominator and close the objective | SUCCESS | Gate 4 | 5,500 / 5,500 completion points equals 100.0%; all 40 completion rows are `SUCCESS`; visibility, publication, upstream merge, and `1.0.0` still await explicit approval. |

## Status updates

- 2026-08-13: Gate 0 inventory recorded before runtime source creation.
- 2026-08-13: Gate 1 implemented immutable API models, `cli-core-yo 2.1.1` command registry, generic and versioned adapters, strict config, streaming/disk-backed analysis, schemas, conservative normalization, transactional publication, references, and MultiQC producer ingestion.
- 2026-08-13: Gate 2 generated outside the checkout from the supplied local corpus; byte-identical regeneration, HG002-only verification, redistribution status, size limits, hashed-token scans, and bcftools/HTSlib 1.24 validation passed before staging.
- 2026-08-13: AC-003 entered `ATTEMPTING_BUGFIX`: added focused VCF 4.5 generic SV/CNV, single-breakend, multiallelic, phasing, and cardinality coverage. Disposition is `FAIL` because the complete finalized local-allele and Number P/LA/LR/LG matrix remains unimplemented.
- 2026-08-13: AC-023 entered `ATTEMPTING_BUGFIX`: inventoried merger support fields and source identities and preserved fixture-relative diagnostics. Disposition is `FAIL` because no digest-bound source-manifest comparator exists.
- 2026-08-13: AC-026 entered `ATTEMPTING_BUGFIX`: exercised the canonical profile, removed silent copy behavior, and added complete fail-closed assessment tests. Disposition is `FAIL` until lossless remapping and lineage exist.
- 2026-08-13: AC-040 entered `ATTEMPTING_BUGFIX`: added a path-safe benchmark harness and deterministic repeated fixture runs. Disposition is `FAIL` because the required large-input and interruption matrix remains unexecuted.
- 2026-08-13: Gate 3 local verification passed: 56 tests, Python 3.11 through 3.13, strict type/lint checks, 79 percent coverage, deterministic package builds, SBOM, fixture verifier, and checkout/artifact/Git/GitHub scans.
- 2026-08-13: The first dependency-review run found a vulnerable test-only dependency. The lock was raised to patched `pytest 9.1.1`; all local checks and the complete seven-job run `31687747018` then passed.
- 2026-08-13: Gate 4 passed. Post-CI scans found zero matches across product files, artifacts, Git history, GitHub metadata, pull-request text, and completed workflow logs. The private draft pull request is open and no publication action occurred.
- 2026-08-13: Documentation was upgraded into a public-ready product surface without changing the private pre-1.0 publication boundary. Seven executable documentation tests bind the HG002 README showcase, examples, links, command catalog, adapter matrix, fixture totals, and dependency claims to current behavior. The archive scanner was hardened to inspect decoded members instead of random compressed bytes, raising the suite to 64 tests. Fresh-checkout typing, deterministic wheel/source/SBOM builds, both content scans, fixture verification, bcftools/HTSlib 1.24, and all three Python versions pass locally; seven-job run `31689711866` passed on exact commit `87bfd58ad35ab9d01baa13b975d6bb1be962111d`.
- 2026-08-13: Quantitative plan amendment reviewed the supplied design, neutral normative contract, 55-row baseline, source, tests, and exact-commit CI evidence. The fixed-denominator result is 89.9% for AC-001 through AC-042 and 92.3% for the complete baseline plan. Historical terminality remains 100%, but six features are below acceptance. Forty completion-work rows now define the dependency order, evidence, and approval gates needed to reach 100% without changing the denominator or silently weakening a criterion.
- 2026-08-13: Execution resumed from clean commit `fc7ed587131898ac33dbc5b56173efaee6c32dfd`; the exact-commit seven-job run `31694921225` and 64-test local baseline pass. The user explicitly requested all six partial features reach 100%, satisfying COMP-039-01's upstream contribution approval while leaving merge, package/image publication, visibility, and release tagging outside scope. COMP-003-01 is now active.
- 2026-08-13: AC-003, AC-023, and AC-026 closed on commit `d8222f4cd10241de42ec006716234ad6781e4851`: the finalized VCF 4.5 matrix, digest-bound conservative source comparison, and canonical multiallelic planner/remapper pass focused, property, parity, graph, independent-validator, and recovery tests.
- 2026-08-13: AC-039 closed with the authorized draft module review in `MultiQC/MultiQC#3626` and companion fixture review in `MultiQC/test-data#385`. Twelve focused tests, two generic strict tests against the companion branch, 11 sections, the 1,000-report case, `prek`, Ruff, and module-scope upstream checks pass. The two whole-project red statuses are explicitly the coupled PR merge order and a Python 3.14 typing error outside the module reproduced by baseline run `31105750315`; no merge or release occurred.
- 2026-08-13: AC-040 closed on the checked-in exact receipts: 2M/1M wall 2.035x, temporary bytes 2.001x, 10M/1M RSS 0.995x, full/minimal-reader 2.33x-6.12x, thread payload identity, and zero output after SIGINT, SIGTERM, a file-size limit, or SIGKILL.
- 2026-08-13: AC-041 qualification produced 24 offline wheel/source receipts across all supported OS/architecture/Python combinations, a verified local-channel Conda install, non-root/read-only Apptainer evidence, and a digest-bound multi-architecture OCI candidate with per-platform SBOM/provenance and zero-finding product scans. Exact-commit distribution run `31719216231` and core run `31719216204` are the final implementation CI receipts.
- 2026-08-13: A branch-coverage rerun exposed and closed a fast-host race in the recovery qualification test: the test input now matches the one-million-record checked-in qualification class, and the harness performs a final liveness check immediately before signal delivery. The complete branch-aware run passes 101 tests at 82 percent coverage.
- 2026-08-13: Final local acceptance passes 101 tests, 82 percent branch-aware coverage, Ruff, mypy, fixture verification for 21 HG002-only fixtures and 1,186 records, HTSlib 1.24 validation, and zero-finding checkout/Git/GitHub scans. The fixed denominator is 5,500 / 5,500 and every completion row is terminal `SUCCESS`.

## Final report

All 55 baseline rows terminal: yes.

All 40 completion-work rows terminal: yes; all 40 are `SUCCESS`.

Objective complete: yes for the approved private pre-1.0 implementation and
qualification scope.

Baseline status counts: 54 `SUCCESS` and 1 `NO_LONGER_NEEDED`; every approved
disposition is fully accepted. No `OPEN`, `IN_PROGRESS`, `ATTEMPTING_BUGFIX`,
`FAIL`, or `BLOCKED` row remains.

Quantitative completion: 100.0% of feature acceptance and 100.0% of the fixed
55-row total plan, or 5,500 / 5,500 points.

Not performed: repository visibility change, branch merge, package/image/Conda
publication, upstream PR merge, release announcement, or `1.0.0` tag. Each
remains a separate explicit-approval action.
