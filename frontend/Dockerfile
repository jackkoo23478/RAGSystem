# Three stages: the first two only build, the last one is what runs and carries no source or build tools.

# 1. install the packages (this layer is reused while package-lock.json does not change)
FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# 2. build the app
FROM node:22-slim AS build
WORKDIR /app
# NEXT_PUBLIC_* values are written into the browser code at BUILD time, not read when the container starts.
# It is the address the BROWSER uses to reach the backend, so it must be reachable from the host.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN mkdir -p public && npm run build

# 3. run: only the small self-contained server that "output: standalone" produces
FROM node:22-slim AS run
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
