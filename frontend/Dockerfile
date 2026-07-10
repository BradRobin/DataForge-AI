# Stage 1: Build the application
FROM node:22-alpine AS builder

WORKDIR /app

# Copy dependency files
COPY package*.json ./

# Install all dependencies (including devDependencies for build)
RUN npm ci

# Copy application source
COPY . .

# Set env to disable telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1

# Build Next.js project
RUN npm run build

# Stage 2: Runtime image
FROM node:22-alpine AS runner

WORKDIR /app

# Set env variables
ENV NODE_ENV=production \
    PORT=3000 \
    NEXT_TELEMETRY_DISABLED=1

# Copy build artifacts and dependencies from builder
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# Expose Next.js port
EXPOSE 3000

# Start Next.js server
CMD ["npm", "run", "start"]
