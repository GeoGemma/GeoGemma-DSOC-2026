#!/bin/bash
# Deploy GeoGemma backend to Google Cloud Run (fixed version)

set -e

# === CONFIG ===
PROJECT_ID="geogemma-458120"
REGION="us-central1"
SERVICE_NAME="geogemma-backend"
SA_NAME="earthengine-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE_TAG="v$(date +%s)"  # Unique tag based on timestamp

# === BANNER ===
echo "==================================================="
echo "  Deploying ${SERVICE_NAME} to Cloud Run"
echo "  Project: ${PROJECT_ID}"
echo "  Region:  ${REGION}"
echo "  SA:      ${SA_EMAIL}"
echo "==================================================="

# === CHECK GCLOUD ===
if ! command -v gcloud &> /dev/null; then
    echo "gcloud CLI is not installed"
    exit 1
fi

# === SET PROJECT ===
gcloud config set project ${PROJECT_ID}

# === ENABLE APIS ===
echo "Enabling required APIs..."
gcloud services enable \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  serviceusage.googleapis.com \
  earthengine.googleapis.com

# === ENSURE SERVICE ACCOUNT EXISTS ===
if ! gcloud iam service-accounts describe ${SA_EMAIL} &> /dev/null; then
  echo "Creating service account ${SA_NAME}..."
  gcloud iam service-accounts create ${SA_NAME} \
    --display-name="Earth Engine Service Account"
fi

# === ASSIGN REQUIRED ROLES TO SA ===
echo "Granting required roles to ${SA_EMAIL}..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/earthengine.writer"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/serviceusage.serviceUsageConsumer"

gcloud secrets add-iam-policy-binding ee-service-key \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

# === BUILD + PUSH TO ARTIFACT REGISTRY ===
IMAGE_URL="us-central1-docker.pkg.dev/${PROJECT_ID}/backend-repo/backend:${IMAGE_TAG}"

echo "Submitting build to Cloud Build: ${IMAGE_URL}..."
gcloud builds submit --tag "${IMAGE_URL}"

# === DEPLOY TO CLOUD RUN ===
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image=${IMAGE_URL} \
  --region=${REGION} \
  --platform=managed \
  --allow-unauthenticated \
  --service-account=${SA_EMAIL} \
  --set-secrets=GOOGLE_APPLICATION_CREDENTIALS=ee-service-key:latest \
  --set-secrets=GEMINI_API_KEY=gemini-api-key:latest \
  --update-env-vars=EE_SERVICE_ACCOUNT_EMAIL=${SA_EMAIL}

echo "==================================================="
echo "✅  Deployment complete!"
echo "🔗  View your service: $(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')"
echo "==================================================="
