# Real Estate Factory — console.
#
# Vercel is the deploy target and does not use this file. It exists so the whole
# stack can be brought up with compose, and so a firm that needs the console
# inside its own network has a supported way to run it.
#
# Note the build-time env: anything with a VITE_ prefix is compiled into the
# bundle, so the API base URL is baked in at build, not read at runtime, and no
# secret can be passed this way.

FROM node:22-alpine AS build

WORKDIR /app

COPY package.json yarn.lock ./
COPY frontend/package.json ./frontend/
COPY packages/api-types/package.json ./packages/api-types/
RUN yarn install --frozen-lockfile

COPY frontend ./frontend
COPY packages ./packages

ARG VITE_API_BASE_URL=http://localhost:8004/api/v1
ARG VITE_MAP_STYLE_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_MAP_STYLE_URL=$VITE_MAP_STYLE_URL
RUN yarn workspace realestate-factory-frontend build


FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/frontend/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/ >/dev/null || exit 1
