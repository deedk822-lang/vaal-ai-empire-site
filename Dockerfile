# Vaal AI Empire - Staging Server
# Multi-stage build for production optimization

# ============================================
# Build Stage
# ============================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY server/package*.json ./

# Install all dependencies (including devDependencies for build if needed)
RUN npm ci

# Copy source code
COPY server/ ./

# ============================================
# Production Stage
# ============================================
FROM node:20-alpine AS production

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init

# Create app directory
WORKDIR /app

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# Copy package files and install production dependencies only
COPY server/package*.json ./
RUN npm ci --only=production && npm cache clean --force

# Copy only necessary application code from builder (node_modules excluded)
COPY --from=builder --chown=nodejs:nodejs /app/server.js ./
COPY --from=builder --chown=nodejs:nodejs /app/config ./config/
COPY --from=builder --chown=nodejs:nodejs /app/controllers ./controllers/
COPY --from=builder --chown=nodejs:nodejs /app/lib ./lib/
COPY --from=builder --chown=nodejs:nodejs /app/middleware ./middleware/
COPY --from=builder --chown=nodejs:nodejs /app/models ./models/
COPY --from=builder --chown=nodejs:nodejs /app/routes ./routes/
COPY --from=builder --chown=nodejs:nodejs /app/agents ./agents/
COPY --from=builder --chown=nodejs:nodejs /app/tests ./tests/
# NOTE: builder node_modules is NOT copied - we use the production node_modules installed above

# Switch to non-root user
USER nodejs

# Expose port
EXPOSE 4242

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD node -e "require('http').get('http://localhost:4242/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Start the server
CMD ["node", "server.js"]
