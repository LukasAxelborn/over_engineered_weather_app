#!/bin/sh
# Runs in the web builder stage. Outputs a fully self-hosted static bundle
# to ../dist (no runtime CDNs). All paths are relative to this script's dir.
set -e

cd "$(dirname "$0")"   # ensure we run from /build/web regardless of caller's cwd

echo "[web] building static bundle..."

rm -rf ../dist
mkdir -p ../dist/assets/fonts

# 1) Compile Tailwind (JIT-scans app/** for class usage).
npx tailwindcss -c ./tailwind.config.js -i ./src/input.css -o ../dist/assets/app.css --minify

# 2) Bundle Chart.js (UMD build, no CDN).
cp ./node_modules/chart.js/dist/chart.umd.js ../dist/assets/chart.umd.js

# 3) Self-host Inter via @fontsource (copied woff2 + generated @font-face CSS).
for w in 300 400 500 600 700; do
  for subset in latin latin-ext; do
    src="./node_modules/@fontsource/inter/files/inter-${subset}-${w}-normal.woff2"
    if [ -f "$src" ]; then
      cp "$src" "../dist/assets/fonts/"
    else
      echo "[web] warn: missing font file $src (falling back to system-ui)"
    fi
  done
done

cat > ../dist/assets/fonts.css <<'EOF'
/* Self-hosted Inter (subset: latin, latin-ext). */
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 300;
  font-display: swap;
  src: url('fonts/inter-latin-300-normal.woff2') format('woff2');
}
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('fonts/inter-latin-400-normal.woff2') format('woff2');
}
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 500;
  font-display: swap;
  src: url('fonts/inter-latin-500-normal.woff2') format('woff2');
}
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url('fonts/inter-latin-600-normal.woff2') format('woff2');
}
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url('fonts/inter-latin-700-normal.woff2') format('woff2');
}
EOF

# 4) Copy the app shell.
cp ../app/index.html ../app/icon.svg ../app/manifest.webmanifest ../app/sw.js ../dist/

echo "[web] done:"
ls -la ../dist
