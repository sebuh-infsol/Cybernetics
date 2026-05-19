#!/bin/bash
# Deploy Cybernetics Broker to Google Cloud Run
# This script automates the deployment process

set -e

PROJECT_ID="strawberry-fields-496517"
REGION="us-central1"
SERVICE_NAME="cybernetics-broker"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "=========================================="
echo "Deploying Cybernetics Broker to Cloud Run"
echo "=========================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI not found. Please install it first."
    echo "See: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found. Please install it first."
    exit 1
fi

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "Error: Not authenticated with Google Cloud."
    echo "Please run: gcloud auth application-default login"
    exit 1
fi

# Set project
echo "Setting project to ${PROJECT_ID}..."
gcloud config set project ${PROJECT_ID}

# Build Docker image
echo "Building Docker image..."
docker build -t ${IMAGE_NAME} -f hackathon/Dockerfile .

# Push to Google Container Registry
echo "Pushing to Google Container Registry..."
docker push ${IMAGE_NAME}

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 8080 \
  --memory 256Mi \
  --min-instances 0 \
  --max-instances 1

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --format='value(status.url)')
echo "=========================================="
echo "Deployment Complete!"
echo "Service URL: ${SERVICE_URL}"
echo "=========================================="

# Test the health endpoint
echo "Testing health endpoint..."
curl -s "${SERVICE_URL}/health" | python3 -m json.tool
