# Streaming, scaling, and recovery qualification

Date: 2026-08-13

Outcome: pass. The complete release-candidate qualification matrix demonstrates
deterministic results, bounded resident memory, approximately linear temporary
space, a bounded cost over a fair minimal reader, thread-count invariance, and
atomic failure behavior. This is a qualification result, not a throughput
service-level promise.

The full matrix, thread matrix, and recovery matrix bind to source commit
`d8222f4cd10241de42ec006716234ad6781e4851`.

## Reproducible inputs

`tools/generate_benchmark_vcf.py` generated all inputs with
`neutral-sv-benchmark/1`, seed 17. They are synthetic and not source-derived.
Only the compact manifests and receipts are tracked; the generated VCFs are not
part of the distribution.

| Class | Records | Samples | Contigs | Compressed bytes |
| --- | ---: | ---: | ---: | ---: |
| representative | 100,000 | 1 | 24 | 1,087,790 |
| multi-sample | 100,000 | 4 | 24 | 1,188,133 |
| long-contig | 100,000 | 1 | 2 | 1,291,648 |
| high-sample | 10,000 | 100 | 24 | 183,856 |
| one-million | 1,000,000 | 1 | 24 | 10,898,608 |
| two-million | 2,000,000 | 1 | 24 | 21,798,375 |
| ten-million | 10,000,000 | 1 | 24 | 108,832,726 |

Exact input names, dimensions, and SHA-256 values are in
[`20260813_synthetic_input_manifests.json`](20260813_synthetic_input_manifests.json).

## Measurement method

Each measurement ran in a fresh process. Wall time used a monotonic clock;
user and system CPU time came from process resource usage; peak RSS included
native libraries. A 10 ms monitor measured the recursive temporary-directory
peak. The first process is labeled cold and later processes warm, but the
operating-system cache was not evicted. The baseline is `pysam==0.24.0` reading
every record, alternate allele, sample call, GT allele, CN, and CNQ value. It
does not compute statistics.

Host: Apple M5 arm64, 10 logical CPUs, 32 GiB RAM, APFS, macOS 25.5.0,
CPython 3.11.15, pysam 0.24.0, bundled HTSlib 1.23.1.

## Matrix results

Times and throughput are the mean of two full statistics passes. RSS and
temporary space are the maximum of the two. Baseline factor is full-tool mean
wall time divided by the fair minimal-reader wall time.

| Class | Mean seconds | Records/s | Peak RSS MiB | Peak temp MiB | Baseline factor | Deterministic |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| representative | 0.895 | 111,767 | 60.55 | 6.27 | 5.91x | yes |
| multi-sample | 1.361 | 73,502 | 60.72 | 6.27 | 3.85x | yes |
| long-contig | 0.900 | 111,096 | 60.17 | 6.27 | 5.90x | yes |
| high-sample | 1.563 | 6,448 | 58.16 | 0.05 | 2.33x | yes |
| one-million | 8.904 | 112,315 | 61.12 | 63.07 | 5.65x | yes |
| two-million | 18.118 | 110,390 | 60.97 | 126.17 | 5.61x | yes |
| ten-million | 95.930 | 104,301 | 60.84 | 641.53 | 6.12x | yes |

| Acceptance check | Limit | Observed | Result |
| --- | ---: | ---: | --- |
| 2M / 1M mean wall-time ratio | <= 2.5 | 2.035 | pass |
| 2M / 1M peak temporary-byte ratio | <= 2.2 | 2.001 | pass |
| 10M / 1M peak-RSS ratio | <= 2.0 | 0.995 | pass |
| Full statistics / minimal-reader wall factor | <= 20x | 2.33x-6.12x | pass |

The 10M result used 0.28 MiB less peak RSS than the 1M result. Temporary space
grows with the disk-backed relationship state rather than being hidden in
resident memory.

The separate thread matrix ran the representative input twice at one thread
and twice at ten threads. All four payloads had SHA-256
`717547db4f7205d245a6ff0429c1df3aa4382bedd88cf53f13c2f2e93f493d94`.
Mean wall times were 0.936 s and 0.897 s, respectively. This proves thread-count
invariance; it does not claim that this workload benefits from more threads.

## Interruption and resource behavior

`tools/qualify_recovery.py` exercised a one-million-record input under SIGINT,
SIGTERM, a 512-byte file-size limit, and SIGKILL. All four processes exited
nonzero. No final summary and no hidden publication-stage file remained in the
output directory. The resource-limited process failed during disk-backed work,
so the observation covers a mid-pipeline resource failure rather than only a
final JSON write.

## Evidence

- [`20260813_streaming_matrix.json`](20260813_streaming_matrix.json) is the
  exact-schema, digest-bound full matrix receipt.
- [`20260813_thread_matrix.json`](20260813_thread_matrix.json) is the
  thread-count receipt.
- [`20260813_recovery_matrix.json`](20260813_recovery_matrix.json) is the
  signal, resource, and crash receipt.

The raw inputs can be regenerated from their manifests. Requalification is
required when the streaming algorithm, dependency versions, benchmark policy,
or supported runtime matrix changes materially.
