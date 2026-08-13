# syntax=docker/dockerfile:1

FROM python:3.11-slim AS build

ARG SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0.dev0
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION}
WORKDIR /build
COPY . /build
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels \
        --requirement requirements.lock.txt \
    && python -m pip wheel --no-cache-dir --no-deps --wheel-dir /wheels .

FROM debian:bookworm-slim

ARG SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0.dev0
ARG SOURCE_COMMIT=unknown
LABEL org.opencontainers.image.title="vcf-sv-stats" \
    org.opencontainers.image.description="Standards-aware structural-variant and copy-number VCF statistics" \
    org.opencontainers.image.version="${SETUPTOOLS_SCM_PRETEND_VERSION}" \
    org.opencontainers.image.revision="${SOURCE_COMMIT}" \
    org.opencontainers.image.licenses="Apache-2.0"
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp/app-home \
    XDG_CONFIG_HOME=/tmp/app-home/config \
    XDG_CACHE_HOME=/tmp/app-home/cache \
    XDG_DATA_HOME=/tmp/app-home/data \
    XDG_STATE_HOME=/tmp/app-home/state
RUN --mount=type=bind,from=build,source=/wheels,target=/wheels,ro \
    apt-get update \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        python3 \
        python3-pip \
    && python3 -m pip install --break-system-packages --no-cache-dir /wheels/*.whl \
    && apt-get purge --yes \
        python3-pip \
        python3-pkg-resources \
        python3-setuptools \
        python3-wheel \
    && apt-get autoremove --yes \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system app \
    && adduser --system --ingroup app --home /nonexistent app \
    && mkdir -p /tmp/app-home \
    && chown app:app /tmp/app-home
USER app
WORKDIR /work
ENTRYPOINT ["vcf-sv-stats"]
CMD ["--help"]
