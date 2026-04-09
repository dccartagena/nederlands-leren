# syntax=docker/dockerfile:1
FROM node:20-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN npm ci

# Development: source is mounted via volume, dev server enabled
FROM base AS development
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Build stage: compile the production bundle
FROM base AS build
COPY . .
RUN npm run build

# Production: serve compiled assets with nginx
FROM nginx:alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
