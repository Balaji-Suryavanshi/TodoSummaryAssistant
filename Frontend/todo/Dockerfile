# Build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG REACT_APP_API_URL=/api/todos
ENV REACT_APP_API_URL=$REACT_APP_API_URL
RUN npm run build

# Run stage
FROM nginxinc/nginx-unprivileged:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
