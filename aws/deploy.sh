#!/bin/bash
set -e

echo "Starting deployment for tag: ${IMAGE_TAG}"

# Fetch secrets from AWS SSM Parameter Store (requires IAM role on EC2)
DB_URL=$(aws ssm get-parameter --name "/todo/DB_URL" --with-decryption --query "Parameter.Value" --output text)
export DB_URL
DB_USERNAME=$(aws ssm get-parameter --name "/todo/DB_USERNAME" --with-decryption --query "Parameter.Value" --output text)
export DB_USERNAME
DB_PASSWORD=$(aws ssm get-parameter --name "/todo/DB_PASSWORD" --with-decryption --query "Parameter.Value" --output text)
export DB_PASSWORD
COHERE_API_KEY=$(aws ssm get-parameter --name "/todo/COHERE_API_KEY" --with-decryption --query "Parameter.Value" --output text)
export COHERE_API_KEY
SLACK_WEBHOOK_URL=$(aws ssm get-parameter --name "/todo/SLACK_WEBHOOK_URL" --with-decryption --query "Parameter.Value" --output text)
export SLACK_WEBHOOK_URL
# Get the EC2 public IP or use an environment variable for FRONTEND_URL
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
EC2_IP=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4)
export FRONTEND_URL="http://${EC2_IP}"

# Pull new images
docker-compose -f docker-compose.prod.yml pull

# Record previous tag for rollback
if [ -f .last_good_tag ]; then
  PREV_TAG=$(cat .last_good_tag)
else
  PREV_TAG=""
fi

# Deploy
docker-compose -f docker-compose.prod.yml up -d

echo "Waiting for backend to be healthy..."
sleep 15
RETRIES=10
HEALTHY=false
for i in $(seq 1 $RETRIES); do
  STATUS=$(curl -s http://localhost:8080/actuator/health | grep '"status":"UP"' || true)
  if [ -n "$STATUS" ]; then
    HEALTHY=true
    break
  fi
  echo "Backend not ready, waiting 5 seconds... ($i/$RETRIES)"
  sleep 5
done

if [ "$HEALTHY" = true ]; then
  echo "Deployment successful!"
  echo "${IMAGE_TAG}" > .last_good_tag
else
  echo "Health check failed! Initiating rollback..."
  if [ -n "$PREV_TAG" ]; then
    export IMAGE_TAG=$PREV_TAG
    echo "Rolling back to tag: $PREV_TAG"
    docker-compose -f docker-compose.prod.yml up -d
  else
    echo "No previous tag found for rollback. Bringing down the stack."
    docker-compose -f docker-compose.prod.yml down
  fi
  exit 1
fi
