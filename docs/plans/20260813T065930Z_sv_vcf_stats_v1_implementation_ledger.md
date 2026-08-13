# `vcf-sv-stats` v1 implementation ledger

Date: 2026-08-13

## Control

- Controlling ledger: `docs/plans/20260813T065930Z_sv_vcf_stats_v1_implementation_ledger.md`
- Repository state at Gate 0: private GitHub repository, default branch `main`, implementation branch `codex/initial-implementation`
- Product boundary: public-neutral Python package and command named `vcf-sv-stats`
- Fixture boundary: derived HG002 records only; original source artifacts remain outside the repository and Git object database
- Publication boundary: repository remains private; package, container, public visibility, and upstream contributions are not authorized in this implementation

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
- Implementation tests: 55 tests pass on Python 3.11; the 3.11, 3.12, and 3.13 isolated matrices each pass.
- Coverage: 79 percent branch-aware line coverage, above the configured 70 percent floor.

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
| REPO-006 | CI | Public GitHub-hosted CI and dependency review configured | IN_PROGRESS | feature_implementation | Gate 3 | orchestrator | `.github/workflows/ci.yml` defines three Python jobs, packaging, container audit, HTSlib 1.24 validation, and dependency review | Workflow cannot execute until the branch is pushed. | Awaiting private draft pull-request CI. |
| PROD-001 | Neutrality | No organization-specific runtime, identity, path, domain, package, service, or branding dependency | SUCCESS | active_product_contract | Gate 3 | orchestrator | Neutral schemas, adapter URNs, config, local/stdin input gate, public lock files, structural scanner, and zero local findings |  | Hosting organization appears only in repository administration. |
| BRAND-002 | Neutrality | Prohibited company token absent from files, artifacts, history, and GitHub metadata | IN_PROGRESS | contract_test | Gate 3 | orchestrator | Hashed-token scans pass for checkout, nested artifacts, current reachable Git objects, repository metadata, and the locally tested image; workflow logs do not yet exist | Branch has not yet produced GitHub workflow logs. | Awaiting post-CI metadata and log scan. |
| FIX-001 | Fixtures | All bundled source-derived fixtures are verified HG002-only | SUCCESS | contract_test | Gate 2 | orchestrator | `tools/verify_test_data.py`; 22 digest-bound source identity inspections; 21 derived fixtures; plain and BCF parity artifacts |  | Exactly one VCF/BCF sample named `HG002`; no other subject token. |
| FIX-002 | Fixtures | Fixture corpus obeys deterministic record and size budgets | SUCCESS | contract_test | Gate 2 | orchestrator | `test_data/manifest.json`: 1,186 records and 180,037 compressed VCF bytes; all fixtures 12 through 100 records |  | Below 2,500 records, 10 MiB, and 128-record closure caps. |
| FIX-003 | Fixtures | Headers, bodies, identifiers, relationships, indexes, and provenance are sanitized and valid | SUCCESS | contract_test | Gate 2 | orchestrator | External deterministic regeneration is byte-identical; fixture verifier and bcftools/HTSlib 1.24 validate all VCF/BCF files and indexes |  | Retained caller quirks remain explicit diagnostics, not silent repairs. |
| FIX-004 | Fixtures | Redistribution review recorded for every source-derived fixture | SUCCESS | legitimate_safety_handling | Gate 2 | orchestrator | `docs/fixture-governance.md`, `test_data/NOTICE.md`, and per-entry manifest status |  | Public-release re-review is an explicit later gate. |
| REL-001 | Publication | Repository remains private; no package, image, tag, or upstream publication performed | IN_PROGRESS | active_product_contract | Gate 4 | orchestrator | Current GitHub visibility is private; no tags or releases; artifacts only in temporary local directories | Final branch and pull-request state not yet available. | Awaiting private draft pull request and final publication audit. |

## Neutralized acceptance criteria

| ID | Requirement | Status | Category | Gate | Owner | Evidence | Root Cause | Terminal Note |
|---|---|---|---|---|---|---|---|---|
| AC-001 | Valid generic SV VCF 4.5 selects the generic adapter and produces exact scoped statistics | SUCCESS | contract_test | Gate 1 | orchestrator | `test_generic_vcf45_sv_statistics_match_exact_scopes` |  | Exact record, allele, BND, event, and filter scopes pass. |
| AC-002 | Valid generic CNV VCF handles CN, genotype, gain, loss, neutral, and reference segments correctly | SUCCESS | contract_test | Gate 1 | orchestrator | `test_generic_vcf45_canonical_and_cnv_states` and fixture goldens |  | CN and genotype states remain factual; without explicit baseline, gain/loss/neutral inference is correctly unavailable and reference segments are separate. |
| AC-003 | Finalized VCF 4.5 SV, BND, multiallelic, local-allele, phasing, and cardinality constructs follow exact rules | FAIL | contract_test | Gate 1 | orchestrator | Generic 4.5 and cardinality tests cover symbolic, sequence, single-BND, CNV, phasing, and basic A/R cardinality | Full Number P/LA/LR/LG, local-allele fields, PSL/PSO/PSQ, and draft-versus-final version gating are not implemented. | No partial conformance claim; implement the complete 4.5 synthetic matrix and lossless remapper before v1. |
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
| AC-023 | Merged/source comparison reports preserved and missing lineage without proposing unsafe reinsertion | FAIL | contract_test | Gate 2 | orchestrator | Fixture support-vector inventory and merger goldens inspected | A digest-bound source-manifest comparison API and record-lineage comparator are not implemented. | Implement explicit local source manifests and conservative `preserved`, `not_preserved`, `not_found`, and `ambiguous` comparisons; never infer reinsertion. |
| AC-024 | Unsupported Severus and separate Sentieon short-read SV identities are reported truthfully | SUCCESS | contract_test | Gate 1 | orchestrator | `test_registry_statuses_and_rewrite_policy` |  | Both remain distinct unsupported adapters with no substituted fixture. |
| AC-025 | Conservative normalization writes a new independently valid artifact without changing input bytes | SUCCESS | contract_test | Gate 1 | orchestrator | VCF.gz/BCF normalization parity test; input digest assertion; bcftools/HTSlib 1.24 validation |  | New data and index validate; source bytes remain unchanged. |
| AC-026 | Canonical multiallelic splitting remaps all declared cardinalities, genotypes, phase, IDs, and lineage | FAIL | contract_test | Gate 1 | orchestrator | `test_unimplemented_canonical_profile_fails_instead_of_copying` | Complete A/R/G/P/LA/LR/LG and local-allele remapping is not implemented. | Canonical requests now fail with a schema-valid safety assessment and no output; implement only with full property and lineage tests. |
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
| AC-039 | Native MultiQC contract discovers only signed summaries, separates identities, and rejects duplicates | BLOCKED | contract_test | Gate 3 | orchestrator | Producer-side `ingest_summaries` contract and duplicate/conflict/schema tests pass | A native upstream module is an external publication action requiring later explicit approval. | Producer boundary is ready; no upstream branch or pull request was created. |
| AC-040 | Performance matrix demonstrates bounded memory, relative scaling, determinism, and interruption safety | FAIL | contract_test | Gate 3 | orchestrator | `tools/benchmark_streaming.py`; three deterministic runs each on 100-record and 98-record fixtures | The required million/ten-million-record, relative-scaling, RSS, baseline, signal, and crash matrix was not run. | Harness and smoke baseline are committed; qualify on generated neutral large inputs before v1. |
| AC-041 | Wheel, source archive, and container build offline, run non-root where applicable, and contain no reference | BLOCKED | contract_test | Gate 3 | orchestrator | Reproducible wheel/sdist builds and scans pass; local image ran read-only and non-root, fixture stats passed, all-layer hashed-token scan passed, and no reference was found | Distribution-channel recipes, release attestations, multi-architecture proof, and final offline install verification are release activities requiring later explicit approval. | No package or image was published; finish release-target verification only after approval. |
| AC-042 | Documentation explains record/event scope, VCF sample/analysis unit, adapters, references, losses, privacy, and recovery | SUCCESS | feature_implementation | Gate 3 | orchestrator | README, neutral normative specification, operator guide, fixture governance, and MultiQC integration guide |  | Known pre-1.0 gaps are stated without claiming v1 completion. |

## Status updates

- 2026-08-13: Gate 0 inventory recorded before runtime source creation.
- 2026-08-13: Gate 1 implemented immutable API models, `cli-core-yo 2.1.1` command registry, generic and versioned adapters, strict config, streaming/disk-backed analysis, schemas, conservative normalization, transactional publication, references, and MultiQC producer ingestion.
- 2026-08-13: Gate 2 generated outside the checkout from the supplied local corpus; byte-identical regeneration, HG002-only verification, redistribution status, size limits, hashed-token scans, and bcftools/HTSlib 1.24 validation passed before staging.
- 2026-08-13: AC-003 entered `ATTEMPTING_BUGFIX`: added focused VCF 4.5 generic SV/CNV, single-breakend, multiallelic, phasing, and cardinality coverage. Disposition is `FAIL` because the complete finalized local-allele and Number P/LA/LR/LG matrix remains unimplemented.
- 2026-08-13: AC-023 entered `ATTEMPTING_BUGFIX`: inventoried merger support fields and source identities and preserved fixture-relative diagnostics. Disposition is `FAIL` because no digest-bound source-manifest comparator exists.
- 2026-08-13: AC-026 entered `ATTEMPTING_BUGFIX`: exercised the canonical profile, removed silent copy behavior, and added complete fail-closed assessment tests. Disposition is `FAIL` until lossless remapping and lineage exist.
- 2026-08-13: AC-040 entered `ATTEMPTING_BUGFIX`: added a path-safe benchmark harness and deterministic repeated fixture runs. Disposition is `FAIL` because the required large-input and interruption matrix remains unexecuted.
- 2026-08-13: Gate 3 local verification passed: 55 tests, Python 3.11 through 3.13, strict type/lint checks, 79 percent coverage, deterministic package builds, SBOM, fixture verifier, and checkout/artifact/Git/GitHub scans. Workflow-log evidence awaits the private draft pull request.

## Final report

All rows terminal: no. Three repository rows await Gate 4 CI and publication-state evidence.

Objective complete: no.

Current status counts: 45 `SUCCESS`, 4 `FAIL`, 1 `NO_LONGER_NEEDED`, 2 `BLOCKED`, and 3 `IN_PROGRESS`.
