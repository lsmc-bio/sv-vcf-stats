# 1.1.0 TEST-002 / BENCH-001 qualification

This is the reproducible bounded protocol; it contains no candidate
measurement or pass claim yet.

## TEST-002 input

Use one host and one fresh temporary directory. Generate one indexed,
reference-block-heavy gVCF with one million records and 24 contigs:

```bash
root=$(mktemp -d /tmp/vcf-sv-stats-1.1.0.XXXXXX)
uv run python tools/generate_benchmark_vcf.py --output "$root/one-million.g.vcf.gz" \
  --manifest "$root/input.json" --class-id reference-block-heavy-24-contig \
  --records 1000000 --samples 1 --contigs 24 --seed 17
uv run python -c 'import pysam, sys; pysam.tabix_index(sys.argv[1], preset="vcf", force=False)' \
  "$root/one-million.g.vcf.gz"
```

Keep this input and index unchanged for both versions. Apply an operator-owned
bounded storage limit to `$root` before generation.

## BENCH-001 measurements

On the same host and input, run each version twice at threads 1 and 8:

```bash
uv run python tools/benchmark_streaming.py --input "$root/one-million.g.vcf.gz" \
  --output "$root/1.0.1.json" --repetitions 2 --threads 1 --threads 8 \
  --source-commit <40-char-1.0.1-commit>
uv run python tools/benchmark_streaming.py --input "$root/one-million.g.vcf.gz" \
  --output "$root/1.1.0.json" --repetitions 2 --threads 1 --threads 8 \
  --source-commit <40-char-integrated-1.1.0-commit>
```

Use median elapsed time. Candidate threads=1 must be at least 20% faster than
released 1.0.1 threads=1; candidate threads=8 must be no more than 10% slower
than candidate threads=1. Require semantic parity after normalizing producer
version and dependent payload digest. Do not commit receipts until candidate
measurements and parity checks exist.
