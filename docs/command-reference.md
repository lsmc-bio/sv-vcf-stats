# Command reference

The executable is `vcf-sv-stats`, implemented through the public
`cli-core-yo==2.1.1` framework. Global options precede the command:

```text
vcf-sv-stats [--json] [--dry-run] [--no-color] [--debug]
             [--config PATH] COMMAND [ARGS]...
```

Use `vcf-sv-stats COMMAND --help` for the exact option surface. This page
documents policy and data behavior.

## Global options

| Option | Contract |
|---|---|
| `--json` | Emit machine-readable command output and structured errors. |
| `--dry-run` | Plan supported mutating commands without publishing state. Rejected for commands whose policy does not support it. |
| `--no-color` | Disable ANSI styling. JSON output is never styled. |
| `--debug` | Enable framework debug diagnostics. |
| `--config PATH` | Use one explicit strict-YAML configuration for the invocation. |

## Command catalog

<!-- command-catalog:start -->
| Command path | Reads full input? | Persistent writes | Purpose |
|---|---:|---:|---|
| `inspect` | unless `--max-records` | no | Inventory container, header, samples, adapter evidence, and early diagnostics. |
| `validate` | yes | optional diagnostics report | Report independent conformance, semantic, safety, and completeness states. |
| `discrepancies` | yes | required report | Publish exhaustive JSON, JSONL, or TSV diagnostics with policy exit. |
| `stats` | yes | optional summary | Calculate deterministic descriptive metrics and metric contracts. |
| `normalize` | yes | data + index + sidecars | Publish conservative normalized output transactionally. |
| `run` | yes | report directory | Publish summary, diagnostics, provenance, and optional normalized output as one directory. |
| `adapters list` | no | no | List the complete adapter registry, optionally filtered by status. |
| `adapters show` | no | no | Show one exact adapter URN. |
| `adapters detect` | header + first record | no | Rank producer evidence and report ambiguity. |
| `schema show` | no | no | List or emit an embedded JSON Schema. |
| `diagnostics explain` | no | no | Explain one stable diagnostic code. |
| `reference fetch` | no VCF input | explicit cache | Plan, retrieve, or offline-verify the pinned public reference profile. |
| `config path` | no | no | Show the framework configuration path. |
| `config init` | no | config file | Create configuration from the packaged template. |
| `config show` | no | no | Show effective configuration without secrets. |
| `config validate` | no | no | Validate strict YAML configuration. |
| `config edit` | no | config file | Open configuration through the framework editor contract. |
| `config reset` | no | config file | Reset configuration to the packaged template. |
| `version` | no | no | Show the package version. |
| `info` | no | no | Show tool, Python, dependency, HTSlib, and schema versions. |
<!-- command-catalog:end -->

## Common input options

| Option | Meaning |
|---|---|
| `INPUT` | Local VCF, VCF.gz, BCF, or `-` for standard input. |
| `--adapter URN` | Require an explicit adapter rather than automatic selection. |
| `--accept-untested-producer-version` | Permit provisional interpretation; never authorizes an unproven rewrite. |
| `--identity-context PATH` | Load explicit JSON or TSV analysis-unit mappings. |
| `--reference PATH` | Provide an explicit local FASTA for reference-aware checks. |
| `--mode MODE` | `compatible`, `standard`, `strict`, or `pedantic`. |
| `--threads N` | Set deterministic worker count within the logical CPU limit. |
| `--temp-dir DIR` | Use an explicit existing directory for temporary state. |
| `--regions REGION` | Restrict reporting to one or more regions. |
| `--regions-scan` | Permit full scanning when region access lacks an index. |

Regional output is always partial. Normalization does not permit region
selection.

## Exit behavior

| Condition | Exit | Artifact behavior |
|---|---:|---|
| Successful command | `0` | Requested complete artifact is available. |
| CLI usage error | `2` | No operation starts. |
| Structured domain/input/output failure | `1` | No false-complete output is left behind. |
| `validate` finds an invalid callset | `1` | Optional diagnostics are published first. |
| `discrepancies --fail-on error` finds errors | `1` | Complete discrepancy report is published first. |
| `discrepancies --fail-on warning` finds warnings or errors | `1` | Complete discrepancy report is published first. |

Library calls do not use these process exits; they return immutable result
models or raise structured exceptions.

## Output routing

- Human command acknowledgements go to standard output.
- `--json` makes command output machine-readable.
- Data artifacts never stream to standard output.
- Errors do not contaminate successful JSON payloads.
- Diagnostics reports require an explicit output path.
- `stats` prints JSON when `--output` is absent and writes atomically when it is
  present.

## Adapter matrix

<!-- adapter-matrix:start -->
| Adapter URN | Producer | Version | Status | Rewrite enabled |
|---|---|---:|---|---:|
| `urn:vcf-sv-stats:adapter:generic:1` | unknown | — | supported | yes |
| `urn:vcf-sv-stats:adapter:manta:1` | Manta | 1.6.0 | supported | yes |
| `urn:vcf-sv-stats:adapter:tiddit:1` | TIDDIT | 3.9.7 | supported | yes |
| `urn:vcf-sv-stats:adapter:dysgu:1` | dysgu | 1.8.0 | supported | yes |
| `urn:vcf-sv-stats:adapter:sniffles2:1` | Sniffles2 | 2.8.0 | supported | yes |
| `urn:vcf-sv-stats:adapter:sentieon-longreadsv:1` | Sentieon LongReadSV | 202503.03 | supported | yes |
| `urn:vcf-sv-stats:adapter:sentieon-cnvscope:1` | Sentieon CNVscope | 202503.03 | supported | yes |
| `urn:vcf-sv-stats:adapter:jasmine:1` | Jasmine | 1.1.5 | supported | yes |
| `urn:vcf-sv-stats:adapter:survivor:1` | SURVIVOR | 1.0.6 | supported | yes |
| `urn:vcf-sv-stats:adapter:octopusv:1` | OctopuSV | 0.4.1 | provisional | no |
| `urn:vcf-sv-stats:adapter:trussv:1` | TrusSV | 0.3.1 | provisional | no |
| `urn:vcf-sv-stats:adapter:severus:1` | Severus | — | unsupported | no |
| `urn:vcf-sv-stats:adapter:sentieon-shortread-sv:1` | Sentieon short-read SV | — | unsupported | no |
<!-- adapter-matrix:end -->

“Rewrite enabled” means the adapter permits conservative rewriting when no
blocking diagnostics exist. It also permits canonical rewriting for finalized
VCF 4.5 inputs when field and relationship proofs are complete; merger
adapters require a safe digest-bound source comparison. It never implies
`caller-lossless` or lossy rewriting.

## Configuration

Configuration is strict YAML: duplicate keys, unknown keys, unsupported schema
versions, and invalid enum values fail. See [examples/config.yaml](examples/config.yaml).

Supported environment variables are deliberately small:

| Variable | Target |
|---|---|
| `VCF_SV_STATS_CONFIG` | Explicit configuration file |
| `VCF_SV_STATS_THREADS` | `io.threads` |
| `VCF_SV_STATS_TMPDIR` | `io.temp_dir` |
| `VCF_SV_STATS_CACHE_DIR` | `reference.cache_dir` |

No filename, service, or directory discovery is performed when a required
value is missing.

## Reference retrieval

```bash
vcf-sv-stats --dry-run reference fetch \
  --assembly GRCh38.p14 \
  --distribution ncbi-refseq
```

A real retrieval requires interactive confirmation or `--yes`. `--offline`
verifies an already cached artifact and never opens the network. The command
checks expected size and digest, creates the FASTA index, and records a manifest.
No reference is bundled with the software.
