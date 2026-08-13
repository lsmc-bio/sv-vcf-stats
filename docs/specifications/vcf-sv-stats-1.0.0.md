# `vcf-sv-stats` 1.0 normative contract

Status: pre-1.0 implementation target. Requirements use MUST, SHOULD, and MAY in
their ordinary standards sense.

## Purpose and boundary

`vcf-sv-stats` inspects, validates, summarizes, and conservatively rewrites
structural-variant and copy-number VCF or BCF callsets. Statistics are
descriptive. They do not establish truth concordance, accuracy, clinical
validity, or pathogenicity.

The product is portable and public-neutral. Runtime behavior cannot depend on a
particular institution, private service, hosted storage system, compute
environment, credential, customer identifier, or filesystem layout. Input is a
local regular file or standard input. The sole network-capable feature is an
explicit, confirmed retrieval of a pinned public reference profile.

## Stable names

- Distribution, package, and executable: `vcf-sv-stats`, `vcf_sv_stats`, and
  `vcf-sv-stats`.
- Schemas: `urn:vcf-sv-stats:schema:<artifact>:<version>`.
- Adapters: `urn:vcf-sv-stats:adapter:<producer>:1`.
- Custom VCF fields: `VCFSVSTATS1_*`.
- Environment variables: `VCF_SV_STATS_*`.
- Canonical observation model: `vcf-sv-stats.canonical-observation/1.0.0`.

## Domain grains

A source record is one VCF row. An allele is one ALT value. A breakend is one
oriented junction endpoint. An event is resolved only by explicit event
evidence, reciprocal compatible mates, or an adapter rule backed by a fixture.
A reciprocal BND pair is two records, two breakends, and one event. Orphan and
single breakends remain breakends and never become invented events.

A VCF sample column is a genotype column, not an analysis identity. Optional
context uses `analysis_unit_id`, `display_id`, `algorithm_id`, explicit VCF
sample mappings, and typed external identifiers. Filenames and directories do
not resolve identity. Without a sidecar, callset statistics remain available and
the analysis unit is `unresolved`.

## Processing phases

Operations follow this order: locality and size gate, container and header
validation, adapter detection, streaming parse, canonical observations,
disk-backed relationship resolution, semantic validation, statistics, optional
rewrite, independent validation and indexing, then transactional publication.
Fatal failure ends later phases without discarding diagnostics already produced.

Inspection may stop early only with explicit `max_records`; it then reports
`complete=false`. Validation, statistics, normalization, and report bundles scan
the full selected input. A regional result is always partial and lists its
regions. Regional access requires an index unless full scanning is explicitly
accepted. Normalization forbids regional selection.

## Validation states and diagnostics

Parser acceptance, VCF conformance, SV/CNV semantic consistency, operation
safety, and statistics completeness are separate states. A parser-readable file
can remain nonconformant or unsafe to rewrite.

Every diagnostic has a stable code, severity, category, message, optional record
location and field, specification reference, fixability, adapter evidence, and
operation-blocking flags. Severity alone does not decide whether statistics or
normalization may proceed. Reports omit raw alleles, genotypes, private paths,
and command lines.

## Adapter model

The generic adapter is always available and never infers a producer from a
filename. Evidence-ranked detection with low or ambiguous confidence selects
generic and reports alternatives. A versioned named adapter is selected only
when its evidence and tested version agree. Explicit acceptance of an untested
version is provisional and cannot authorize an unproven rewrite.

Supported adapters are Manta 1.6.0, TIDDIT 3.9.7, dysgu 1.8.0, Sniffles2 2.8.0,
Sentieon LongReadSV 202503.03, Sentieon CNVscope 202503.03, Jasmine 1.1.5, and
SURVIVOR 1.0.6. OctopuSV 0.4.1 and TrusSV 0.3.1 are provisional and
rewrite-disabled. Severus and the distinct Sentieon short-read SV dialect are
unsupported until native, licensed, versioned fixtures pass the adapter gate.

Merger support fields are provenance, not biological replication or accuracy.
Support counts, vectors, caller order, source identifiers, and relationship
completeness must be checked before use. Missing source topology never
authorizes mate, event, genotype, or allele invention.

## Canonical observations

The immutable public observation records source record and allele ordinals,
source coordinates and ID, original declared type, normalized type,
representation, length, filter state, and explicit mate/event references.
Symbolic, sequence-resolved, bracket breakend, and single-breakend alleles remain
distinct representations. Unknown constructs remain `UNKNOWN`; mixed small
variants remain `NON_SV` and are excluded from SV/CNV event metrics.

Source VCF coordinates remain one-based. Length is nonnegative and its basis is
reported. BND, translocation, and undefined lengths remain missing rather than
zero. Missing values never become numeric zero.

Copy-number and genotype reporting preserves no-call, partial missingness,
ploidy, phasing, reference, heterozygous, homozygous-alt, and other states.
Copy-number values are separate from their biological interpretation; a value of
two does not universally prove neutrality.

## Statistics

Required scopes are source records, alleles, breakends, events, genotypes, exact
VCF sample columns, explicit analysis units, and callset. Each stable metric
defines its scope, denominator, unit, inclusion rule, missing/invalid counts,
derivation status, and comparability group.

`vss-bins/1` length bins are `[0,50)`, `[50,100)`, `[100,500)`,
`[500,1000)`, `[1000,5000)`, `[5000,10000)`, `[10000,50000)`,
`[50000,100000)`, `[100000,1000000)`, `[1000000,10000000)`, and
`[10000000,+inf)`. Histograms include exact `n`, minimum, maximum, missing,
invalid, and not-applicable counts. QUAL and copy number use separately labeled
distributions. Non-finite JSON numbers are prohibited.

## Rewriting and publication

Normalized output is a new BGZF VCF plus TBI/CSI, or BCF plus CSI. The input is
opened read-only and cannot alias any output through an ordinary path, symlink,
hard link, or resolved identity. Existing unrelated paths are rejected. Force
replacement applies only to a complete prior artifact set whose receipt proves
ownership; it never recursively removes content.

`conservative` permits only unambiguous, semantics-preserving operations with
unchanged record cardinality. Representation-changing `caller-lossless` and
`canonical` behavior requires adapter proof and complete lineage. Loss is denied
unless a stable, known, applicable loss code is individually authorized. There
is no blanket authorization, and authorization can never invent evidence.

The VCF header binds the canonical normalization request digest. The transform
manifest binds input, output, index, mappings, and transformation counts. The
receipt binds request, manifest, and artifact digests. Sidecars and index are
published before the data commit marker. A failure removes the new partial set
and restores a verified prior set when replacing it. A complete `run` directory
is staged and renamed as one filesystem operation.

## Machine artifacts

JSON uses UTF-8, finite values, deterministic key semantics, JSON Schema
2020-12, and RFC 8785 canonical hashing. The summary content signature is
`vcf-sv-stats:summary:1`. Schema major versions define compatibility; unknown
majors are rejected. Library calls return immutable models or structured
exceptions and never terminate the host process.

## CLI

One immutable `CliSpec` and explicit `CommandPolicy` registry define:

- `inspect`, `validate`, `discrepancies`, `normalize`, `stats`, and `run`;
- `adapters list`, `adapters show`, and `adapters detect`;
- `schema show`, `diagnostics explain`, `reference fetch`, `version`, and `info`.

Root JSON, color, dry-run, configuration, and runtime behavior come from the
public `cli-core-yo` framework. Strict YAML rejects duplicate and unknown keys.
Output data never goes to standard output. Dry-run is accepted only for
mutating commands.

## Reference profile

Reference-free inspection, declaration checks, event logic, and most statistics
remain available. Reference-aware checks require an explicit local FASTA or the
pinned `GRCh38.p14` public profile. Retrieval prints source, expected size, and
terms before confirmation, supports offline verification, uses an exclusive
cache lock, verifies content, creates an index, and records a digest manifest.
No reference is bundled in a wheel, source archive, container, or test fixture.

## MultiQC boundary

The producer emits `*.vcf-sv-stats.json`. Discovery requires both this suffix
and the content signature. A consumer validates the supported schema major and
payload digest, reads only summaries, keeps the report ID distinct from all
authoritative identity fields, deduplicates byte-equivalent report payloads,
and rejects conflicting duplicates. Core code does not import MultiQC.

## Privacy, fixtures, and release gates

Coordinates, alleles, genotypes, identifiers, and paths can be sensitive.
Diagnostics and receipts use digests, ordinals, field names, and short display
names. There is no telemetry.

Source-derived test fixtures are deterministic, heavily subsampled, sanitized
HG002 records. Headers are rebuilt from an allowlist, the sole sample is named
`HG002`, source identifiers and relationship references are neutralized, and
raw sources never enter Git. The manifest binds source and fixture digests,
counts, behavior classes, sanitization version, identity evidence, and
redistribution review.

The repository remains private and versions remain pre-1.0 while required
acceptance rows are incomplete. Public visibility, package or container
publication, an upstream module contribution, and the annotated `1.0.0` tag
each require explicit later approval.
