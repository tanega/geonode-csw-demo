# Vite/Vue SPA: build the static bundle, then serve it with nginx (used only
# as a static file server for this image — Traefik stays the single reverse
# proxy in front of the stack, per docs/architecture.md).

FROM oven/bun:1 AS build
WORKDIR /app

# vue-tsc's #!/usr/bin/env node shebang needs a *real* Node.js: in this
# image `node` is just a symlink back to bun's own Node-compat shim, which
# doesn't support vue-tsc's .vue module-resolution patching (type-check
# fails with spurious "Cannot find module '*.vue'" for every .vue import).
RUN apt-get update && apt-get install -y --no-install-recommends nodejs && rm -rf /var/lib/apt/lists/*

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .

# Vite inlines VITE_* vars into the bundle at build time, not at container
# runtime — must be passed as build args, not `environment:`.
ARG VITE_GEONODE_API_BASE
ARG VITE_OAUTH_CLIENT_ID
ENV VITE_GEONODE_API_BASE=$VITE_GEONODE_API_BASE
ENV VITE_OAUTH_CLIENT_ID=$VITE_OAUTH_CLIENT_ID

RUN bun run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
