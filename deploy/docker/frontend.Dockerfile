FROM node:24-alpine AS build
WORKDIR /workspace
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/admin-web ./apps/admin-web
COPY apps/screen-web ./apps/screen-web
COPY apps/user-web ./apps/user-web
RUN npm install --global pnpm@11.16.0 \
    && pnpm install --frozen-lockfile --filter @active/admin-web --filter @active/screen-web --filter @active/user-web
RUN pnpm --filter @active/admin-web exec vue-tsc --noEmit \
    && pnpm --filter @active/admin-web exec vite build --base=/admin/ \
    && pnpm --filter @active/screen-web exec vue-tsc --noEmit \
    && pnpm --filter @active/screen-web exec vite build --base=/screen/ \
    && pnpm --filter @active/user-web exec vue-tsc --noEmit \
    && pnpm --filter @active/user-web exec vite build --base=/user/

FROM nginx:1.28-alpine
COPY --from=build /workspace/apps/admin-web/dist /usr/share/nginx/html/admin
COPY --from=build /workspace/apps/screen-web/dist /usr/share/nginx/html/screen
COPY --from=build /workspace/apps/user-web/dist /usr/share/nginx/html/user
COPY deploy/nginx/default.conf /etc/nginx/conf.d/default.conf
