FROM node:22-alpine AS build

ARG APP_DIR
WORKDIR /workspace
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps ./apps
RUN corepack enable && pnpm install --frozen-lockfile
RUN pnpm --filter @active/${APP_DIR} build

FROM nginx:alpine
ARG APP_DIR
COPY --from=build /workspace/apps/${APP_DIR}/dist /usr/share/nginx/html
COPY deploy/nginx/default.conf /etc/nginx/conf.d/default.conf
