#!/usr/bin/env python3.14
"""
Deploy Cybernetics broker to Google Cloud Run using the google-cloud-run Python library
"""

import sys
import os
import subprocess
from google.cloud import run_v2
from google.auth import default
from google.auth.transport.requests import Request

def authenticate():
    """Authenticate with Google Cloud"""
    credentials, project = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    if credentials.expired:
        credentials.refresh(Request())
    return credentials, project

def build_and_push_image(project_id, region="us-central1"):
    """Build and push Docker image to Google Container Registry"""
    image_name = f"gcr.io/{project_id}/cybernetics-broker:latest"
    
    print("Building Docker image...")
    result = subprocess.run(
        ["docker", "build", "-t", image_name, "-f", "hackathon/Dockerfile", "."],
        capture_output=True, text=True, timeout=120
    )
    
    if result.returncode != 0:
        print(f"Error building Docker image: {result.stderr}")
        sys.exit(1)
    
    print("Pushing to Google Container Registry...")
    result = subprocess.run(
        ["docker", "push", image_name],
        capture_output=True, text=True, timeout=120
    )
    
    if result.returncode != 0:
        print(f"Error pushing Docker image: {result.stderr}")
        sys.exit(1)
    
    return image_name

def deploy_service(project_id, region="us-central1"):
    """Deploy the broker to Cloud Run"""
    credentials, project = authenticate()
    
    # Build and push the Docker image
    image_name = build_and_push_image(project_id, region)
    
    # Create Cloud Run client
    client = run_v2.ServicesClient(credentials=credentials)
    
    # Build the service configuration
    service = run_v2.Service(
        spec=run_v2.ServiceSpec(
            template=run_v2.RevisionTemplate(
                spec=run_v2.RevisionSpec(
                    container=run_v2.Container(
                        image=image_name,
                        ports=[run_v2.ContainerPort(container_port=8080)]
                    ),
                    service_account_name=f"cybernetics-sa@{project_id}.iam.gserviceaccount.com",
                    max_instance_count=1,
                    min_instance_count=0,
                )
            )
        )
    )
    
    # Create the service
    parent = client.common_location_path(project_id, region)
    request = run_v2.CreateServiceRequest(
        parent=parent,
        service=service,
        service_id="cybernetics-broker"
    )
    
    print(f"Deploying to Cloud Run in {region}...")
    operation = client.create_service(request=request)
    print(f"Deployment started: {operation.name}")
    
    return operation.result()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deploy.py <project-id>")
        sys.exit(1)
    
    project_id = sys.argv[1]
    deploy_service(project_id)
