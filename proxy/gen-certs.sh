#!/bin/sh
# Generate a local root CA + a leaf certificate for this host, plus the
# Traefik dashboard basic-auth users file. Idempotent: skips if certs exist.
#
# Usage:
#   sh proxy/gen-certs.sh
#   DASH_USER=admin DASH_PASS=secret sh proxy/gen-certs.sh
#
# Then import proxy/certs/rootCA.crt into your browser/OS trust store.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="$HERE/certs"
mkdir -p "$DIR"

DASH_USER="${DASH_USER:-admin}"
DASH_PASS="${DASH_PASS:-weather}"

# SANs: build from CERT_DNS / CERT_IPS env, with sensible defaults.
CERT_DNS="${CERT_DNS:-localhost,weather.local,traefik.local,pi4.local}"
CERT_IPS="${CERT_IPS:-127.0.0.1,192.168.1.238,172.17.0.1}"

if [ -f "$DIR/weather.crt" ] && [ -f "$DIR/weather.key" ] && [ -f "$DIR/rootCA.crt" ]; then
  echo "[certs] existing certificates found in $DIR (delete them to regenerate)."
else
  echo "[certs] generating root CA..."
  openssl genrsa -out "$DIR/rootCA.key" 4096
  openssl req -x509 -new -nodes -key "$DIR/rootCA.key" -sha256 -days 3650 \
    -subj "/C=SE/O=Weather Local/CN=weather-local-ca" -out "$DIR/rootCA.crt"

  echo "[certs] generating leaf certificate..."
  openssl genrsa -out "$DIR/weather.key" 2048

  # Build extensions file.
  {
    echo "[req]"
    echo "distinguished_name = dn"
    echo "prompt = no"
    echo "[dn]"
    echo "CN = weather.local"
    echo "[v3_req]"
    echo "subjectAltName = @alt"
    echo "keyUsage = critical, digitalSignature, keyEncipherment"
    echo "extendedKeyUsage = serverAuth"
    echo "[alt]"
    i=1
    for d in $(printf '%s' "$CERT_DNS" | tr ',' ' '); do
      echo "DNS.$i = $d"
      i=$((i + 1))
    done
    i=1
    for ip in $(printf '%s' "$CERT_IPS" | tr ',' ' '); do
      echo "IP.$i = $ip"
      i=$((i + 1))
    done
  } > "$DIR/san.cnf"

  openssl req -new -key "$DIR/weather.key" -out "$DIR/weather.csr" -config "$DIR/san.cnf"
  openssl x509 -req -in "$DIR/weather.csr" -CA "$DIR/rootCA.crt" -CAkey "$DIR/rootCA.key" \
    -CAcreateserial -out "$DIR/weather.crt" -days 825 -sha256 \
    -extfile "$DIR/san.cnf" -extensions v3_req

  rm -f "$DIR/weather.csr" "$DIR/san.cnf"
  chmod 600 "$DIR/rootCA.key" "$DIR/weather.key"
  echo "[certs] done."
fi

# Dashboard basic-auth users file (Apache MD5, supported by Traefik).
echo "[auth] writing dashboard users file (user: $DASH_USER)"
HASH="$(openssl passwd -apr1 "$DASH_PASS")"
printf '%s:%s\n' "$DASH_USER" "$HASH" > "$HERE/dynamic/users"
chmod 600 "$HERE/dynamic/users"

echo "[certs] certificates: $DIR/weather.crt"
echo "[certs] root CA:      $DIR/rootCA.crt"
echo "[certs] import the root CA into your trust store, then open https://weather.local"
