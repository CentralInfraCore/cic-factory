# Use a slim, modern Python image
FROM python:3.11-slim

# Set a working directory
WORKDIR /app

# Install system dependencies that might be needed for cryptographic libraries,
# pip-tools, and the Go toolchain.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    git \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install pip-tools globally in the container for the setup service to use
RUN pip install --no-cache-dir pip-tools

# ---- Go toolchain (mk/golang.mk, go/ reference implementation) ----
# TinyGo was removed with the WASM machinery: this repo compiles no guest
# module. Rust is intentionally NOT installed here — CIC-Relay runs cargo in
# a separately pinned rust-builder container (docker-compose.yml
# x-rust-version anchor), and docs/rust-gate-extraction.md keeps that shape.
ARG GO_VERSION=1.25.0
ENV PATH="/usr/local/go/bin:/root/go/bin:${PATH}"

RUN ARCH="$(dpkg --print-architecture)" && \
    curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${ARCH}.tar.gz" -o /tmp/go.tgz && \
    tar -C /usr/local -xzf /tmp/go.tgz && \
    rm /tmp/go.tgz

# ---- Go quality tools (mk/golang.mk: golang.lint / golang.vuln) ----
# GOBIN=/usr/local/bin: the builder runs as the host UID (docker-compose
# `user:`), which has no access to /root — installing to GOPATH/bin (under
# /root) would be unreadable at runtime.
RUN GOBIN=/usr/local/bin go install honnef.co/go/tools/cmd/staticcheck@v0.6.1 && \
    GOBIN=/usr/local/bin go install golang.org/x/vuln/cmd/govulncheck@v1.1.4
