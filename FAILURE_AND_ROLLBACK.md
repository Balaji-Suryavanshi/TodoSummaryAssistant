# Failure Scenarios & Recovery Procedures

## 1. Faulty version deployed (Rollback)
If a faulty version is pushed to production, the `deploy.sh` script automatically detects a failure via the `/actuator/health` health check running directly on the instance.
- **Auto-rollback**: The script automatically falls back to `.last_good_tag`, restarts the container with the previous tag, and fails the CI/CD pipeline command invocation.
- **Manual Rollback**: Connect to EC2 (via SSM Session Manager or SSH), run `export IMAGE_TAG=<previous_working_sha>`, and run `docker-compose -f docker-compose.prod.yml up -d`.

## 2. Application crashes after deployment (Runtime)
- The container orchestrator (Docker Compose) uses `restart: unless-stopped`, which will automatically restart the container.
- If it crash-loops, Prometheus/Grafana will trigger the **ContainerRestarting** alert.
- Check logs: `docker logs todo-backend_1` or `docker logs todo-frontend_1`.
- Follow Manual Rollback (above) to revert to a stable image while diagnosing the issue locally.

## 3. CI/CD tool unavailable (Manual Deploy)
If GitHub Actions is down, you can still deploy manually:
1. Build locally: `docker build -t your-dockerhub/todo-backend:latest ./Backend/todo-summary-assistant`
2. Push manually: `docker push your-dockerhub/todo-backend:latest`
3. Connect to EC2 via AWS SSM Session Manager (or SSH if allowed).
4. Run deployment manually: `cd /opt/todo && export IMAGE_TAG=latest && ./aws/deploy.sh`

## 4. Secrets leaked
If secrets (e.g. DB Password, Cohere API key) are leaked:
1. Revoke the leaked secret in the third-party provider (e.g., reset DB password in RDS, revoke Cohere key).
2. Go to AWS Systems Manager (SSM) Parameter Store.
3. Update the value of the affected parameter (e.g., `/todo/DB_PASSWORD`).
4. Re-run the deployment via GitHub actions or trigger `aws/deploy.sh` manually to fetch the new secrets and restart the containers.
5. Invalidate any compromised JWT or session tokens if applicable.

## 5. EC2 instance fails (Compute recovery)
Since this is a single EC2 instance setup, instance failure causes downtime.
- **Recovery**: Launch a new EC2 instance following `aws-setup.md`. Attach the IAM role, install Docker, and update GitHub Secrets with the new `EC2_INSTANCE_ID`. The CI/CD pipeline will deploy the latest version on the next run.

## 6. RDS unavailable (Database recovery)
If RDS fails, the backend will fail health checks and alert via `HighErrorRate` or `ServiceDown`.
- **Impact**: The app becomes read/write unavailable.
- **Recovery**: AWS RDS automatically performs daily backups. You can restore the database to any point in time within the retention period by selecting "Restore to point in time" in the RDS console.
