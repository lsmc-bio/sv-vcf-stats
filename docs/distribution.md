# Distribution qualification

`vcf-sv-stats` is a public 1.0 release. This guide defines how a candidate
proves installability and supply-chain evidence. Release `1.0.1` publishes one
wheel through GitHub Releases without publishing a package, container, or Conda
artifact to a registry.

## GitHub release wheel

The supported public installation artifact is the universal wheel attached to
the `1.0.1` GitHub release:

```bash
python -m pip install --no-cache-dir \
  "https://github.com/lsmc-bio/sv-vcf-stats/releases/download/1.0.1/vcf_sv_stats-1.0.1-py3-none-any.whl"
```

The identical URL is used inside a Conda environment:

```bash
conda create --yes --name vcf-sv-stats python=3.13 pip
conda run --name vcf-sv-stats python -m pip install --no-cache-dir \
  "https://github.com/lsmc-bio/sv-vcf-stats/releases/download/1.0.1/vcf_sv_stats-1.0.1-py3-none-any.whl"
```

This is not a native Conda package or channel. The generated GitHub source-code
snapshots are not the supported pip artifact for this release.

## Supported target contract

The machine-readable matrix in
[`packaging/supported-targets.json`](../packaging/supported-targets.json) covers:

| Operating system | Architecture | Python | Candidate channels |
|---|---|---|---|
| Linux | x86_64, arm64 | 3.11, 3.12, 3.13 | wheel, source archive |
| macOS | arm64, x86_64 | 3.11, 3.12, 3.13 | wheel, source archive |

Each of the 24 cross-product cases must install from a complete local
wheelhouse with package-index access disabled. The source archive is rebuilt
offline, its wheel must be byte-identical to the primary wheel, and both
installed channels must pass `vcf-sv-stats-verify-install` with the same
semantic digest.

## Installed verifier

The verifier is part of the distribution rather than the source test suite:

```bash
vcf-sv-stats-verify-install --output install-verification.json
```

It creates a temporary, neutral two-record callset; derives indexed VCF.gz and
BCF forms; validates, summarizes, and normalizes both; verifies semantic parity;
and exercises the installed `version`, `info`, `validate`, and `stats` CLI
paths. It opens no network connection and removes its temporary files.

The resulting receipt validates against
`urn:vcf-sv-stats:schema:install-verification:1.0.0`. The matrix aggregator
requires exactly 24 receipt names and one tool version and semantic digest.

## Conda recipes

[`packaging/bioconda/meta.yaml`](../packaging/bioconda/meta.yaml) is the candidate
Bioconda recipe. Two public PyPI dependencies that are not available as public
Conda packages have pinned supporting recipes under `packaging/conda/`:

- `cli-core-yo==2.1.1`, MIT licensed;
- `rfc8785==0.1.4`, Apache-2.0 licensed.

All source URLs and SHA-256 values are explicit. CI builds the supporting
packages and main recipe into a temporary local channel, performs an offline
installation, and runs the installed verifier. Nothing uploads to a channel.

## OCI and Apptainer

The candidate OCI layout contains exactly `linux/amd64` and `linux/arm64`
images. Both run as a non-root `app` user in `/work`, use
`vcf-sv-stats` as the fixed entry point, and contain no bundled reference
genome. BuildKit must attach an SPDX SBOM and SLSA provenance statement to each
platform manifest.

CI runs both architectures with networking disabled, a read-only root
filesystem, and an explicit temporary filesystem. The OCI auditor verifies
platforms, runtime configuration, layer paths, blob digests, and per-platform
attestations. A separate Apptainer 1.5.3 smoke converts the exact candidate,
confirms non-root execution, runs the verifier in a contained environment, and
records the SIF digest.

The full OCI archive and every generated evidence file are scanned for
`BRAND-002`. Neutrality scanning is deliberately scoped to product-owned Python
packages, console entry points, image configuration, aggregate evidence, and
repository content. Base operating-system binaries and third-party SBOM file
inventories are governed by their pinned digests and license inventories;
applying short organization-token hashes to arbitrary vendor binary bytes would
produce non-semantic collisions rather than a branding result.

## Candidate evidence

`tools/build_release_evidence.py` binds the exact wheel, normalized source
archive, optional OCI layout and audit, full Git commit, locked runtime
dependencies, native tooling, and reviewed HG002 fixture corpus. It emits:

- CycloneDX 1.6 and SPDX 2.3 SBOMs;
- SHA-256 checksums;
- an in-toto statement with SLSA v1 provenance;
- an exact runtime-license inventory;
- OCI platform attestations and audit receipt when a container is included.

The durable signing path uses Sigstore keyless signing on an exact default-branch
manual qualification. GitHub Actions supplies a short-lived OIDC identity; no
long-lived key or repository signing secret exists. Verification requires both
the exact workflow identity
`$GITHUB_SERVER_URL/$GITHUB_WORKFLOW_REF` and issuer
`https://token.actions.githubusercontent.com`.

Pull-request runs and default manual qualifications build and scan unsigned
candidate evidence. Signing additionally requires the explicit
`publish_sigstore_entry=true` dispatch input and the repository's exact default
branch. This is a separate public-write gate because Sigstore records signing
metadata and the artifact digest in its public transparency log; it does not
publish artifact contents. Release `1.0.1` leaves the input false because no
Sigstore publication was requested.

The OIDC permission exists only on that job-level-gated signing job. Pull
requests and ordinary qualification jobs receive no identity-token permission,
so code under review cannot bypass the public-write gate. The signing job also
declares every distribution qualification as a prerequisite and requires
`success()`, preventing an irreversible transparency entry for a partially
qualified candidate.

The Sigstore bundle necessarily contains the administrative repository and
workflow identity. That identity is the sole hosting exception to product
neutrality and is verified separately from product-owned content.

## Run the gates

```bash
uv run pytest -q tests/test_verify_install.py \
  tests/test_distribution_qualification.py \
  tests/test_conda_recipes.py tests/test_oci_audit.py \
  tests/test_release_evidence.py
uv run vcf-sv-stats-verify-install --output /tmp/install-verification.json
```

The prior cross-platform distribution contract is retained in Git history but
is not part of release `1.0.1`. Do not resume its matrix. The current
`.github/workflows/distribution.yml` manually builds only the universal wheel
that will be attached to the GitHub release.

## Public GitHub wheel release sequence

Create the immutable annotated `1.0.1` tag on the merged release commit and
dispatch the one-wheel workflow on that tag. It builds exactly
`vcf_sv_stats-1.0.1-py3-none-any.whl`; no other distribution format is built.

After the tag-ref run succeeds, download and verify the exact universal wheel,
make the repository public, enable and read back private vulnerability
reporting, and attach only the wheel and its `SHA256SUMS` file to the public
GitHub release. Leave Sigstore publication disabled. Public GitHub visibility
and these two release assets do not authorize any registry upload.
