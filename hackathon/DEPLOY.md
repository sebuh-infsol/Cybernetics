# Deploy Cybernetics Broker to Google Cloud Run

## Prerequisites

1. **Install gcloud CLI**
   ```bash
   # Download and install gcloud CLI
   curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/google-cloud-cli-linux-x86_64.tar.gz
   tar -xzf google-cloud-cli-linux-x86_64.tar.gz -C /opt/
   ln -sf /opt/google-cloud-sdk/bin/gcloud /usr/local/bin/gcloud
   ln -sf /opt/google-cloud-sdk/bin/gcloud.sh /usr/local/bin/gcloud.sh
   ```

2. **Authenticate with Google Cloud**
   ```bash
   gcloud auth application-default login
   ```

3. **Set the project**
   ```bash
   gcloud config set project strawberry-fields-496517
   ```

## Deployment Steps

### 1. Build and Push Docker Image
```bash
# Build the Docker image
docker build -t gcr.io/strawberry-fields-496517/cybernetics-broker:latest -f hackathon/Dockerfile .

# Push to Google Container Registry
docker push gcr.io/strawberry-fields-496517/cybernetics-broker:latest
```

### 2. Deploy to Cloud Run
```bash
# Deploy the service
gcloud run deploy cybernetics-broker \
  --image gcr.io/strawberry-fields-496517/cybernetics-broker:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 256Mi \
  --min-instances 0 \
  --max-instances 1
```

### 3. Verify Deployment
```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe cybernetics-broker --platform managed --region us-central1 --format='value(status.url)')
echo "Service URL: $SERVICE_URL"

# Test the health endpoint
curl "$SERVICE_URL/health"
```

## Alternative: Python API Deployment

If you prefer to use the Python API instead of gcloud CLI:

```bash
# Install dependencies
pip3 install --break-system-packages google-cloud-run

# Run the deployment script
python3.14 /home/sebuh/Cybernetics/hackathon/deploy.py strawberry-fields-496517
```

## Troubleshooting

### Authentication Issues
- Make sure you're logged in: `gcloud auth list`
- Check if ADC is set: `gcloud auth application-default list`
- If using a service account key: `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`

### Docker Build Issues
- Make sure Docker is running: `docker info`
- Check if you have enough disk space: `df -h`
- Check if the Dockerfile is valid: `docker build --no-cache -t test -f hackathon/Dockerfile .`

### Cloud Run Deployment Issues
- Check if the project is enabled: `gcloud services list --enabled`
- Check if the Cloud Run API is enabled: `gcloud services enable run.googleapis.com`
- Check if you have enough permissions: `gcloud projects get-iam-policy strawberry-fields-496517`
