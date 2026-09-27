# Not yet built/tested locally (no Docker in the original dev environment
# — see docs/architecture.md). Kept current for when Docker is available.
#
# The app is a static export (next.config.ts: output "export"), so the
# image is just nginx serving files; no Node.js at runtime. The API address
# is compiled into the bundle, hence a build argument, not a runtime env var.
FROM node:20-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/out /usr/share/nginx/html
# trailingSlash export: /contracts/view/ -> contracts/view/index.html
RUN printf 'server {\n  listen 3000;\n  root /usr/share/nginx/html;\n  location / { try_files $uri $uri/ $uri/index.html =404; }\n  error_page 404 /404.html;\n}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 3000
