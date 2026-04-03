FROM node:20-alpine

WORKDIR /app
COPY frontend/package.json /app/package.json
COPY frontend/tsconfig.json /app/tsconfig.json
COPY frontend/next-env.d.ts /app/next-env.d.ts
COPY frontend/next.config.ts /app/next.config.ts
COPY frontend/src /app/src
RUN npm install

EXPOSE 3000
CMD ["sh", "-c", "npm run dev -- --hostname 0.0.0.0 --port ${FRONTEND_PORT:-3000}"]
