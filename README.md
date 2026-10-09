# Todo Summary Assistant - DevOps Architecture

## Project Overview
This project is a React frontend and Spring Boot backend application for managing tasks, enhanced with AI summarization using Cohere and Slack integration.
As part of the DevOps transition, the application has been containerized and configured for CI/CD deployment on AWS EC2 via AWS SSM and OIDC, with fully externalized configurations.

## Architecture
- **Frontend**: React SPA served by Nginx (`todo-frontend`).
- **Backend**: Spring Boot 3 Java API (`todo-backend`).
- **Database**: Local MySQL (for development) and AWS RDS MySQL (for production).
- **Monitoring**: Prometheus, Node Exporter, cAdvisor, and Grafana.
- **CI/CD**: GitHub Actions building and pushing images to Docker Hub, then deploying via AWS SSM Send-Command (OIDC).

## Prerequisites
- Docker and Docker Compose
- Java 17, Node 20 (for local development)
- AWS Account (for production)

## Local Run Steps
1. Create a `.env` file in the root based on `.env.example`:
   ```bash
   cp .env.example .env
   ```
   (Fill in `COHERE_API_KEY` and `SLACK_WEBHOOK_URL` with real values or leave as fake if not using them).
2. Start the local stack:
   ```bash
   docker compose up -d --build
   ```
3. Access:
   - Frontend: http://localhost
   - Backend API: http://localhost:8080
   - Grafana: http://localhost:3000 (auto-provisioned dashboard)
   - Prometheus: http://localhost:9090

## Environment Variables
| Variable | Description |
| -------- | ----------- |
| `DB_URL` | MySQL JDBC URL |
| `DB_USERNAME` | DB username |
| `DB_PASSWORD` | DB password |
| `COHERE_API_KEY` | API Key for Cohere |
| `SLACK_WEBHOOK_URL` | Webhook URL for Slack |
| `FRONTEND_URL` | CORS frontend origin (local dev only) |
| `REACT_APP_API_URL` | Build arg injected for React relative proxying |

## Docker Design Choices
- **Backend**: Multi-stage build (`eclipse-temurin:17-jdk-jammy` for build, `17-jre-jammy` for runtime). Uses a non-root user `spring` for security. Added JVM container-aware flags (`-XX:+UseContainerSupport`) to respect container memory limits. Added Docker HEALTHCHECK targeting `/actuator/health`.
- **Frontend**: Multi-stage build (`node:20` for build, `nginx-unprivileged` for serving). Uses non-privileged ports (`8080`) internally for security. Includes SPA fallback routing (`try_files`) and proxies `/api/` directly to the backend in `nginx.conf`.
- **Compose**: Defined networks and persistent volumes. Used named volumes for DB and Monitoring. Used healthchecks and `depends_on: condition: service_healthy` for proper startup sequence.

## CI/CD Pipeline
Defined in `.github/workflows/ci-cd.yml`:
1. **Test Stage**: Runs `mvn test` (with H2 in-memory DB) and `npm run build` concurrently.
2. **Docker Build & Push**: On `main` branch, builds and pushes images tagged with the commit SHA and `latest` to Docker Hub. Injects `REACT_APP_API_URL=/api/todos` for the frontend.
3. **Deployment**: Uses GitHub OIDC to assume an AWS IAM role. Calls `aws ssm send-command` to trigger the EC2 instance to clone the repository to `/opt/todo`, log into Docker Hub, fetch secrets from AWS SSM, and execute `aws/deploy.sh`. The script performs a rolling update via Docker Compose and automatically rolls back if the backend health check fails.

## Accessing Grafana/Prometheus (Production)
In production, monitoring ports (`9090`, `3000`, `9100`, `8081`) are bound to `127.0.0.1` inside the EC2 instance for security. They are not accessible from the public internet. 

To access them securely from your laptop, use **AWS SSM Port Forwarding** (requires the AWS CLI and Session Manager plugin):
```bash
# For Grafana:
aws ssm start-session --target <instance-id> --document-name AWS-StartPortForwardingSession --parameters '{"portNumber":["3000"],"localPortNumber":["3000"]}'
# Visit http://localhost:3000
```
```bash
# For Prometheus:
aws ssm start-session --target <instance-id> --document-name AWS-StartPortForwardingSession --parameters '{"portNumber":["9090"],"localPortNumber":["9090"]}'
# Visit http://localhost:9090
```

## How to Deploy
1. Complete the AWS steps outlined in `aws/aws-setup.md`.
2. Add the required GitHub Secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `AWS_ROLE_ARN`, `AWS_REGION`, `EC2_INSTANCE_ID`, `EC2_USER`.
3. Push to the `main` branch. GitHub Actions will automate the rest.

## Code Changes Made
- `application.properties`: Replaced hardcoded values with `${VAR_NAME}` syntax for database, API keys, and URLs with no fallback strings. Hardened Actuator with `show-details=never`.
- `todoService.js`: Replaced hardcoded backend URL with `process.env.REACT_APP_API_URL` falling back to relative `/api/todos` to allow dynamic Nginx proxying.
- `nginx.conf`: Added a location block to proxy `/api/` calls to the backend container.
- `pom.xml`: Added dependencies for `spring-boot-starter-actuator`, `micrometer-registry-prometheus`, and `h2` (test scope).
- `application-test.properties`: Added for H2 database during tests.

## Cleanup
If you deploy this in your AWS account, remember to delete your EC2 instance and RDS database when finished to avoid charges.
