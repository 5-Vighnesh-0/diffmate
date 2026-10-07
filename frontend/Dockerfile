# Dev server for local compose. Phase 6 replaces this with a static build behind Caddy.
FROM node:22-slim
RUN corepack enable && mkdir /app && chown node:node /app
WORKDIR /app
USER node
COPY --chown=node:node package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY --chown=node:node index.html vite.config.ts tsconfig.json ./
COPY --chown=node:node src ./src
EXPOSE 5173
CMD ["pnpm", "dev"]
