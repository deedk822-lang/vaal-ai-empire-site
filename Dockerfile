# Use Node.js for the frontend/server
FROM node:25-slim AS base
WORKDIR /app

# Install system dependencies for native modules
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install root dependencies
COPY package*.json ./
RUN npm install --omit=dev

# Install server dependencies
COPY server/package*.json ./server/
RUN cd server && npm install --omit=dev

# Copy application code
COPY . .

# Expose the application port
EXPOSE 3000

# Start the application from server directory
WORKDIR /app/server
CMD ["node", "server.js"]
