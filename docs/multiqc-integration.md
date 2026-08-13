# MultiQC producer integration

The producer contract is a small JSON file named `*.vcf-sv-stats.json` with
content signature `vcf-sv-stats:summary:1`. Consumers do not read VCF, BCF,
indexes, transformation manifests, or command logs.

`vcf_sv_stats.multiqc.ingest_summaries` is the executable producer-side
reference contract. It validates filenames, schema major, exact 1.0 schema,
content signature, and canonical payload digest. Each `reports[]` entry becomes
one report record. Its stable `report_id` is used only as the MultiQC
compatibility key; explicit analysis-unit, display, algorithm, sample mapping,
and external-identifier fields remain authoritative and unchanged.

An identical report payload repeated under the same ID is deduplicated with its
additional path recorded. Different payloads under the same ID are rejected and
neither conflicting record is ingested. Unknown schema majors are rejected.

The proposed native module should show resolved events, interpretable alleles,
validation errors, orphan-breakend percentage, unknown-type percentage, filter
states, length bins, copy-number availability, producer, adapter status, and
identity resolution. Tooltips must state scope and denominator. Caller support
is provenance and must never be labeled accuracy.

The native module belongs in the upstream project under that project's license,
review, typing, snapshot, and strict-mode requirements. Creating that upstream
contribution is a separate publication action and is not part of the current
private implementation.
