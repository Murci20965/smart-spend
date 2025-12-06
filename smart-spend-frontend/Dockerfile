# smart-spend-frontend/Dockerfile

# Use Node image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files first to leverage Docker cache
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the app
COPY . .

# Expose Vite's default port
EXPOSE 5173

# Start dev server with --host to expose to Docker network
CMD ["npm", "run", "dev", "--", "--host"]