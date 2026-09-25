FROM node:22-bookworm-slim
WORKDIR /app
COPY apps/control-plane-api/package.json apps/control-plane-api/package-lock.json* /app/apps/control-plane-api/
RUN npm install --omit=dev --prefix /app/apps/control-plane-api
COPY apps/control-plane-api/dist /app/apps/control-plane-api/dist
COPY apps/control-plane-api/migrations /app/apps/control-plane-api/migrations
ENV NODE_ENV=production
USER node
CMD ["node", "apps/control-plane-api/dist/apps/control-plane-api/src/start.js"]
