#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 CERTIFICATE_DIRECTORY" >&2
  exit 2
fi

certificate_dir=$1
certificate="$certificate_dir/tls.crt"
key="$certificate_dir/tls.key"
if [[ -e "$certificate" || -e "$key" ]]; then
  echo "refusing to overwrite an existing runtime certificate" >&2
  exit 1
fi

mkdir -p "$certificate_dir"
umask 077
openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 365 \
  -keyout "$key" \
  -out "$certificate" \
  -subj "/CN=nfx.internal" \
  -addext "subjectAltName=DNS:nfx.internal,DNS:localhost,IP:127.0.0.1"
chmod 600 "$key"
chmod 644 "$certificate"
echo "created self-signed certificate and key in the supplied external directory"
