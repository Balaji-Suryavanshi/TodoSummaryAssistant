# DevOps Assessment Report - Final Local Pass

## 1. Summary of Work and Fixes (Final Pass)
- **Docker Verification**: Verified `docker info` works (Docker Desktop is active). However, building and pulling multiple images took excessive time and could not complete within the assessment window. Section 1 (Runtime Verification) is marked as **PARTIAL/NOT VERIFIED**.
- **Static Validation**: Successfully validated `docker-compose.yml`, `docker-compose.prod.yml`, `prometheus.yml`, and `alert-rules.yml` syntax using `docker compose config` and `promtool`. Ran `mvn test` and `npm run build` successfully.
- **SSM OIDC Auto-Deployment**: Updated the SSM command in `.github/workflows/ci-cd.yml` to automatically `git clone` or `git fetch` the repo into `/opt/todo`, passing GitHub secrets (Docker Hub token) down to `aws/deploy.sh`.
- **Docker Hub Login**: Updated `aws/deploy.sh` to accept `$DOCKERHUB_TOKEN` and `$DOCKERHUB_USER` via stdin to authenticate before pulling images.
- **Accessing Monitoring**: Added a dedicated section in `README.md` and `aws-setup.md` explaining how to use AWS SSM Port Forwarding to securely access Grafana (3000) and Prometheus (9090) over `127.0.0.1`.
- **AWS EC2 Bootstrap**: Provided a user-data script in `aws-setup.md` recommending **Amazon Linux 2023** and pre-installing Git, Docker, Compose plugin, and `mkdir /opt/todo`.
- **Secrets Tracking**: Added `.env` to `.gitignore` and removed `.env` from tracking (`git rm --cached .env`). Validated with `git check-ignore`. Checked git history for secrets with `git grep`.
- **Grafana Provisioning**: Fixed missing dashboard by properly injecting a UID in `grafana-dashboard.json` and provisioning it via `dashboard.yml`. Fixed missing UID mismatch in `alerting/rules.yml`.
- **Metrics Accuracy**: Refactored Prometheus queries to exclude Kubernetes-specific metrics (e.g. `kube_pod_container_status_restarts_total`) in favor of `cAdvisor` metrics (e.g. `container_start_time_seconds{name!=""}`). Filtered disk space panels/alerts specifically to root filesystem. Replaced container CPU summing with host node CPU for accurate utilization percentages. Used `or vector(0)` for HTTP 5xx error rate to prevent empty queries breaking dashboards.

---

## 2. Table of Fixes & Validation Status

| Requirement | Status | Evidence / Command Output (Trimmed) |
| ----------- | ------ | ----------------------------------- |
| **docker-compose.prod.yml NO db service** | **DONE** | File `docker-compose.prod.yml` validated via `docker compose -f docker-compose.prod.yml config`. No `db` service exists, no `depends_on: db`. |
| **EC2 file gap / deploy.sh repo clone** | **DONE** | SSM command updated to `sudo mkdir -p /opt/todo`, `git clone ...`, `git fetch --all`, `git reset --hard $SHA`. |
| **Monitoring bound to 127.0.0.1 & SSM Port Forward docs** | **DONE** | Configured `127.0.0.1:3000:3000` etc. Added SSM instructions to README.md and aws-setup.md. |
| **aws-setup.md Amazon Linux 2023 + Bootstrap** | **DONE** | Added User-Data script to install `git`, `docker`, `docker-compose` plugin, and `chown ec2-user:ec2-user /opt/todo`. |
| **Docker Hub Login** | **DONE** | Added `echo "$DOCKERHUB_TOKEN" \| docker login -u "$DOCKERHUB_USER" --password-stdin` in `deploy.sh`. |
| **Render architecture diagram (.png)** | **DONE** | Command run: `npx -y @mermaid-js/mermaid-cli -i aws/architecture-diagram.mmd -o aws/architecture-diagram.png`. |
| **README, FAILURE, MONITORING docs match** | **DONE** | Fully synchronized docs with SSM deployment, rolling updates, and Prometheus alert rules. |

---

## 3. Static Validation Results (Section 2)

| Validation | Status | Evidence (Trimmed Output) |
| ---------- | ------ | ------------------------- |
| `docker compose config` | **VERIFIED** | `name: todosummaryassistant` `services: backend: depends_on: db: ...` (Valid YAML) |
| `docker compose -f prod config` | **VERIFIED** | `name: todosummaryassistant` `services: backend: ... frontend: ...` (No db service) |
| `promtool check config` | **VERIFIED** | `Checking /etc/prometheus/prometheus.yml` <br/> `SUCCESS: 1 rule files found` <br/> `SUCCESS: /etc/prometheus/prometheus.yml is valid` |
| `promtool check rules` | **VERIFIED** | `Checking /monitoring/alert-rules.yml` <br/> `SUCCESS: 7 rules found` |
| `actionlint` / `shellcheck` | **NOT VERIFIED** | Not natively installed on the Windows environment. |
| `bash -n aws/deploy.sh` | **NOT VERIFIED** | Windows WSL not properly configured for `/bin/bash` execution natively. |
| `mvn test` | **VERIFIED** | `[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0` <br/> `[INFO] BUILD SUCCESS` |
| `npm run build` | **VERIFIED** | `The build folder is ready to be deployed.` |
| `git check-ignore .env` | **VERIFIED** | Output: `.env` |
| `git grep` for secrets | **VERIFIED** | Output showed NO real secrets, only placeholders in `.env.example` and variables. |

---

## 4. Runtime Verification (Section 1)

Docker was validated to be running via `docker info`. However, the full stack compilation and pulling of large images (Java JRE, Node) exceeded practical local constraints. 

**Status: NOT VERIFIED**. Please run the following commands manually to perform the runtime verification:

```bash
# 1. Bring up stack and check status
docker compose up -d --build
docker compose ps

# 2. Check health endpoints
curl localhost:8080/actuator/health
curl localhost:8080/actuator/prometheus | head

# 3. Check Prometheus targets and rules
curl -s localhost:9090/api/v1/targets
curl localhost:9090/api/v1/rules

# 4. Check Container Images & Non-root User
docker images
docker compose exec backend id
docker compose exec frontend id
```

---

## 5. Files Changed in Final Pass
- `.github/workflows/ci-cd.yml` (SSM /opt/todo automated clone + token passing)
- `aws/deploy.sh` (Docker login mechanism)
- `aws/aws-setup.md` (Amazon Linux 2023 user-data bootstrap script, SSM Port Forwarding instructions)
- `README.md` (SSM Port Forwarding, Architecture design notes)
- `FAILURE_AND_ROLLBACK.md` (Updated path to `/opt/todo` for manual deployments)
- `.gitignore` (Added `.env`)
- `.gitattributes` (Added `*.sh text eol=lf`)
- `aws/architecture-diagram.png` (Rendered Mermaid chart)
- `monitoring/grafana-dashboard.json` (Injected UID, updated metrics to be accurate)
- `monitoring/grafana/provisioning/dashboards/dashboard.yml` (Added auto-provisioning mapping)
- `monitoring/grafana/provisioning/alerting/rules.yml` (Fixed UID references, updated host CPU metric query)
- `monitoring/alert-rules.yml` (Updated Prometheus alert queries with fixes for 5xx, host CPU, disk mountpoint, and cAdvisor container restart metrics)

---

## 6. Problems Hit and Fixes
- **`.env` tracked in git**: `.env` was mistakenly tracked. Fixed by writing `.env` into `.gitignore` and running `git rm --cached .env`.
- **promtool volume mapping**: Initially, `promtool check config` failed in Docker because the internal prometheus config pointed to `/etc/prometheus/alert-rules.yml` while I mounted to `/monitoring`. Fixed by mapping `-v ".../monitoring:/etc/prometheus"`.
- **Windows Subsystem Execution**: Attempting `bash -n aws/deploy.sh` locally threw a WSL relay error. Handled via visual syntax validation.

---

## 7. Final Manual Checklist (For You)

1. **AWS Console Steps (in order)**:
   - Create VPC & Subnets.
   - Create `ec2-sg` (Ports 80 public) and `rds-sg` (3306 from `ec2-sg`).
   - Create RDS MySQL Database.
   - Create IAM Role `TodoApp-EC2-Role` (attach `AmazonSSMManagedInstanceCore` and inline SSM Parameter read policy).
   - Create SSM Parameters: `/todo/DB_URL`, `/todo/DB_USERNAME`, `/todo/DB_PASSWORD`, `/todo/COHERE_API_KEY`, `/todo/SLACK_WEBHOOK_URL`.
   - Launch EC2 Instance (Amazon Linux 2023, attach `TodoApp-EC2-Role`, attach `ec2-sg`, paste the User Data script from `aws-setup.md`).
   - Create AWS IAM OIDC Provider (`token.actions.githubusercontent.com`).
   - Create IAM Role `TodoApp-GitHub-Deploy-Role` using the OIDC Provider, restrict trust policy to your repo, attach SSM SendCommand policy.
2. **GitHub Secrets Needed (Exact Names)**:
   - `DOCKERHUB_USERNAME`
   - `DOCKERHUB_TOKEN`
   - `AWS_ROLE_ARN`
   - `AWS_REGION`
   - `EC2_INSTANCE_ID`
   - `EC2_USER`
3. **Trigger First Deploy**:
   - `git push origin main` (This triggers Actions which builds, pushes, and deploys via SSM).
4. **Screenshots for Submission**:
   - **GitHub Actions**: A green, successful workflow run (build, test, deploy).
   - **Grafana Dashboard**: Connect via SSM Port Forwarding (`aws ssm start-session ...`), open `http://localhost:3000`, and screenshot the dashboard showing data.
   - **Prometheus Targets**: Open `http://localhost:9090/targets` via Port Forwarding and screenshot the `UP` states.
