# 1.1.0 TEST-002 / BENCH-001 qualification

The bounded qualification passed on 2026-08-30. Raw schema-valid receipts are
[`1.0.1`](20260830T1628Z_bench-001_1.0.1.json) and
[`1.1.0`](20260830T1630Z_bench-001_1.1.0.json).

## TEST-002 input

Use one host and one fresh temporary directory. Generate one indexed,
reference-block-heavy gVCF with one million records and 24 contigs:

```bash
root=$(mktemp -d /tmp/vcf-sv-stats-1.1.0.XXXXXX)
uv run python tools/generate_gvcf_benchmark.py --output "$root/one-million.g.vcf.gz"
```

Keep this input and index unchanged for both versions. The harness measured
recursive temporary usage; the observed peak and zero final usage below
establish the bounded-storage result.

Input SHA-256: `7627ac55651c0136a29aaca1d39047b17c163462273a1f1b742a63c3b73090d`
(5,209,076 bytes). Tabix index SHA-256:
`deee7b28dd1137210f114aaaa4d5c726bc0d56e7b0b8ea6380b3cbd6839a66a0` (18,851
bytes).

## BENCH-001 measurements

On the same host and input, first perform one unrecorded cache warm-up for each
configuration. The harness labels the first measured row “cold” because it is
the first process, despite the explicit unrecorded warm-up. Then record exactly
two repetitions for released 1.0.1 at
threads=1, and for the candidate at threads=1 and threads=8:

```bash
uv run python tools/benchmark_streaming.py --input "$root/one-million.g.vcf.gz" \
  --output "$root/1.0.1.json" --repetitions 2 --threads 1 \
  --source-commit <40-char-1.0.1-commit>
uv run python tools/benchmark_streaming.py --input "$root/one-million.g.vcf.gz" \
  --output "$root/1.1.0.json" --repetitions 2 --threads 1 --threads 8 \
  --source-commit <40-char-integrated-1.1.0-commit>
```

Use median elapsed time. Candidate threads=1 was 25.030870% faster than
released 1.0.1 threads=1; candidate threads=8 was 0.026662% slower than
candidate threads=1. Medians were 6,123,152,250 ns, 4,590,473,958.5 ns, and
4,591,697,875 ns respectively. Full candidate outputs were identical.
Semantic parity holds after setting `producer.version` to a common value,
removing the dependent top-level `payload_sha256`, and comparing normalized
SHA-256 `2c758bd603c64f6600bb47e05e9fc95fe2aa8a66ec68fce8c63e9480e2825ed2`.

Host: Apple M5, Darwin 25.5.0, 10 logical CPUs, Python 3.11.15, pysam 0.24.0,
HTSlib 1.23.1. Peak temporary bytes: 31,633,408 (1.0.1), 32,768 (1.1.0);
final temporary bytes: zero.
