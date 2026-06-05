# Stage 1: Build frontend
FROM node:22-alpine AS frontend
WORKDIR /build
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2: Production
FROM python:3.12-slim
WORKDIR /app

# Install Python dependencies
COPY server/requirements.txt ./server/
RUN pip install --no-cache-dir -r server/requirements.txt

# Copy backend code
COPY server/ ./server/

# Copy built frontend
COPY --from=frontend /build/dist ./web/dist/

# Copy data pipeline scripts (optional, for on-server data updates)
COPY src/ ./src/

EXPOSE 8765

CMD ["bash", "server/start.sh"]
