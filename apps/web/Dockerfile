# Not yet built/tested locally (no Docker in the original dev environment
# — see docs/architecture.md). Kept current for when Docker is available.
FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
