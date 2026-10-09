# AWS Setup Guide

Follow these steps manually in the AWS Management Console to set up the production environment for the Todo Summary Assistant.

## 1. VPC & Networking
1. Go to **VPC** and ensure you use the **default VPC** (or a VPC configured similarly).
2. For the EC2 instance, you must use a **public subnet** with **auto-assign public IP** enabled (the SSM agent requires internet access to connect to AWS).
3. For RDS, create a **DB Subnet Group** that spans at least two subnets in different Availability Zones.

## 2. Security Groups
Create two Security Groups (SGs) in your VPC:
**EC2 Security Group (`ec2-sg`)**:
- Inbound: HTTP (port 80) from anywhere (0.0.0.0/0).
- Outbound: All traffic.

**RDS Security Group (`rds-sg`)**:
- Inbound: MySQL/Aurora (port 3306) from **`ec2-sg` ONLY**.
- Outbound: All traffic.

## 3. RDS (MySQL) Setup
1. Go to **RDS** -> **Create Database**.
2. Select **MySQL** (Free Tier if available).
3. Set DB instance identifier to `todo-db`.
4. Set Master username (e.g., `admin`) and Master password.
5. In Connectivity:
   - Select your VPC.
   - **Public access**: `No`.
   - Choose the `rds-sg` Security Group.
6. In Additional Configuration, specify the Initial database name as `todo_db`.
7. Click **Create Database**. (Note the Endpoint URL once created).

## 4. IAM Role for EC2
1. Go to **IAM** -> **Roles** -> **Create role**.
2. Trusted entity type: **AWS service** -> **EC2**.
3. Attach managed policy: **AmazonSSMManagedInstanceCore** (Required for SSM deployments).
4. Create a new inline policy (or managed policy) for SSM Parameter access:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter",
                "ssm:GetParameters",
                "ssm:GetParametersByPath"
            ],
            "Resource": "arn:aws:ssm:*:*:parameter/todo/*"
        },
        {
            "Effect": "Allow",
            "Action": "kms:Decrypt",
            "Resource": "*"
        }
    ]
}
```
5. Name the role `TodoApp-EC2-Role`.

## 4.5. IAM Role for GitHub Actions (OIDC)
To allow GitHub Actions to deploy without SSH keys:
1. In AWS IAM, create an **Identity Provider** for OIDC:
   - Provider URL: `https://token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`
2. Create a new Role, select **Web identity**, and choose the GitHub OIDC provider.
3. Edit the Trust Relationship to restrict it to your repository and main branch:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:<YOUR_GITHUB_USERNAME>/<YOUR_REPO_NAME>:ref:refs/heads/main"
                }
            }
        }
    ]
}
```
4. Attach an inline policy allowing it to run SSM commands on your EC2 instance:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ssm:SendCommand",
                "ssm:GetCommandInvocation"
            ],
            "Resource": [
                "arn:aws:ec2:<REGION>:<ACCOUNT_ID>:instance/<INSTANCE_ID>",
                "arn:aws:ssm:<REGION>::document/AWS-RunShellScript"
            ]
        }
    ]
}
```
5. Name the role `TodoApp-GitHub-Deploy-Role`. Note the Role ARN.

## 5. SSM Parameter Store
Create the following SecureString parameters using AWS CLI (or AWS Console):
```bash
aws ssm put-parameter --name "/todo/DB_URL" --value "jdbc:mysql://<RDS_ENDPOINT>:3306/todo_db" --type "SecureString"
aws ssm put-parameter --name "/todo/DB_USERNAME" --value "admin" --type "SecureString"
aws ssm put-parameter --name "/todo/DB_PASSWORD" --value "your_db_password" --type "SecureString"
aws ssm put-parameter --name "/todo/COHERE_API_KEY" --value "your_cohere_key" --type "SecureString"
aws ssm put-parameter --name "/todo/SLACK_WEBHOOK_URL" --value "your_slack_webhook" --type "SecureString"
```

## 6. EC2 Setup
1. Go to **EC2** -> **Launch Instance**.
2. Name: `TodoApp-Server`.
3. AMI: **Amazon Linux 2023** (or Ubuntu 22.04).
4. Instance type: `t2.micro` or `t3.micro`.
5. Key pair: Select or create your key pair.
6. Network settings: Select your VPC and attach `ec2-sg`. Auto-assign Public IP should be Enabled.
7. Advanced Details -> **IAM instance profile**: Select `TodoApp-EC2-Role`.
8. User Data (to install Git, Docker, Docker Compose, and prep /opt/todo):
```bash
#!/bin/bash
sudo yum update -y
sudo yum install git docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
sudo mkdir -p /opt/todo
sudo chown -R ec2-user:ec2-user /opt/todo
```
9. Launch Instance.

## 7. GitHub Actions Secrets
In your GitHub repo, go to **Settings -> Secrets and variables -> Actions** and add:
- `DOCKERHUB_USERNAME`: Your Docker Hub username.
- `DOCKERHUB_TOKEN`: Your Docker Hub access token (only used by the GitHub Actions runner to push images).
- `AWS_ROLE_ARN`: The ARN of the `TodoApp-GitHub-Deploy-Role`.
- `AWS_REGION`: Your AWS region (e.g., `us-east-1`).
- `EC2_INSTANCE_ID`: The ID of your EC2 instance (e.g., `i-0abcdef1234567890`).

**Important**: Because the EC2 instance pulls images without logging in, your Docker Hub repositories (`todo-frontend` and `todo-backend`) must be set to **Public**.

Once all steps are complete, triggering a push to the `main` branch will deploy the application!

## 8. Accessing Grafana/Prometheus
Because monitoring ports (9090, 3000) are bound to `127.0.0.1` inside the EC2 instance for security, they are not accessible from the public internet. 

To access them securely from your laptop, use **AWS SSM Port Forwarding** (requires the [AWS CLI](https://aws.amazon.com/cli/) and [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)):

**For Grafana:**
```bash
aws ssm start-session --target <instance-id> \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["3000"],"localPortNumber":["3000"]}'
```
Then visit `http://localhost:3000` in your browser.

**For Prometheus:**
```bash
aws ssm start-session --target <instance-id> \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["9090"],"localPortNumber":["9090"]}'
```
Then visit `http://localhost:9090` in your browser.
