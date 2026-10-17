#!/bin/sh
# Runs from the nginx image's /docker-entrypoint.d before nginx starts.
# Uses certs mounted at /etc/nginx/certs; generates a self-signed pair if none exist.
set -eu

CERT_DIR=/etc/nginx/certs
mkdir -p "$CERT_DIR"

if [ -f "$CERT_DIR/cert.pem" ] && [ -f "$CERT_DIR/key.pem" ]; then
  echo "$0: using existing certificate in $CERT_DIR"
  exit 0
fi

# Add the display host's name/IP via TLS_SAN, e.g. "DNS:weekboard.local,IP:192.168.1.50"
SAN="DNS:localhost,IP:127.0.0.1${TLS_SAN:+,$TLS_SAN}"
echo "$0: generating self-signed certificate for $SAN"
openssl req -x509 -newkey rsa:2048 -nodes -days 825 \
  -keyout "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" \
  -subj "/CN=Week Board" -addext "subjectAltName=$SAN" 2>/dev/null
chmod 600 "$CERT_DIR/key.pem"
