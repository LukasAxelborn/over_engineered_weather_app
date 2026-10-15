# ---- Stage 1: build the self-hosted static bundle ----
FROM node:20-alpine AS builder

WORKDIR /build

# Install deps first for layer caching.
COPY web/package.json ./web/
RUN cd web && npm install --no-audit --no-fund

# Bring in the app source + build tooling.
COPY web/ ./web/
COPY app/ ./app/

RUN sh ./web/build.sh

# ---- Stage 2: serve with nginx ----
FROM nginx:1.27-alpine AS runtime

LABEL org.opencontainers.image.title="weather-web"
LABEL org.opencontainers.image.description="Static weather PWA served by nginx"

COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1

# nginx:alpine already has an entrypoint that starts the daemon.
