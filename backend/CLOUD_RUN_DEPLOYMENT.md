# Deploying GeoGemma Backend to Google Cloud Run

This guide provides step-by-step instructions for deploying the GeoGemma backend to Google Cloud Run.

## Prerequisites

- Google Cloud account with billing enabled
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed
- Docker installed locally
- Basic familiarity with command line and Google Cloud

## Step 1: Setting Up the Project

1. Authenticate with Google Cloud:
   ```bash
   gcloud auth login
   ```

2. Set your project ID:
   ```bash
   gcloud config set project geogemma-458120
   ```

3. Enable the required APIs:
   ```bash
   gcloud services enable \
     earthengine.googleapis.com \
     run.googleapis.com \
     containerregistry.googleapis.com \
     cloudbuild.googleapis.com \
     serviceusage.googleapis.com
   ```

## Step 2: Earth Engine Authentication

1. Create a service account for Earth Engine:
   ```bash
   gcloud iam service-accounts create ee-service-account \
     --display-name="Earth Engine Service Account"
   ```

2. Grant necessary permissions to the service account:
   ```bash
   # Grant Earth Engine user role
   gcloud projects add-iam-policy-binding geogemma-458120 \
     --member="serviceAccount:ee-service-account@geogemma-458120.iam.gserviceaccount.com" \
     --role="roles/earthengine.user"
     
   # Grant Service Usage Consumer role (required for Earth Engine API access)
   gcloud projects add-iam-policy-binding geogemma-458120 \
     --member="serviceAccount:ee-service-account@geogemma-458120.iam.gserviceaccount.com" \
     --role="roles/serviceusage.serviceUsageConsumer"
   ```

3. Generate and download the service account key:
   ```bash
   gcloud iam service-accounts keys create ee-service-account.json \
     --iam-account=ee-service-account@geogemma-458120.iam.gserviceaccount.com
   ```

4. Move the key file to the backend directory to be included in the Docker build:
   ```bash
   mv ee-service-account.json /path/to/GeoGemma/backend/
   ```

## Step 3: Building and Pushing the Docker Image

1. Navigate to the backend directory:
   ```bash
   cd /path/to/GeoGemma/backend
   ```

2. Build the Docker image:
   ```bash
   docker build -t gcr.io/geogemma-458120/geogemma-backend:latest .
   ```

3. Configure Docker for Google Container Registry:
   ```bash
   gcloud auth configure-docker
   ```

4. Push the image to Google Container Registry:
   ```bash
   docker push gcr.io/geogemma-458120/geogemma-backend:latest
   ```

## Step 4: Deploying to Cloud Run

1. Deploy the image to Cloud Run:
   ```bash
   gcloud run deploy geogemma-backend \
     --image=gcr.io/geogemma-458120/geogemma-backend:latest \
     --region=us-central1 \
     --platform=managed \
     --allow-unauthenticated \
     --memory=2Gi \
     --cpu=1 \
     --set-env-vars=EE_PROJECT_ID=geogemma-458120,SECRET_KEY=your-production-secret-key
   ```

   Note: Replace `your-production-secret-key` with a secure random string for production.

2. Get the deployed service URL:
   ```bash
   gcloud run services describe geogemma-backend --region=us-central1 --format='value(status.url)'
   ```

## Step 5: Verifying the Deployment

1. Test the API:
   ```bash
   curl https://your-service-url.run.app/api/health
   ```

2. Check the API documentation at:
   ```
   https://your-service-url.run.app/api/docs
   ```

## Troubleshooting

### Earth Engine Authentication Issues

If you encounter Earth Engine authentication issues, check:

1. That the `EE_PROJECT_ID` environment variable is correctly set
2. That the service account has both the `roles/earthengine.user` AND `roles/serviceusage.serviceUsageConsumer` roles
3. That the service account key is correctly included in the Docker image
4. If still failing, check the Cloud Run logs for specific error messages

### Memory or Performance Issues

For better performance, you can adjust the memory and CPU settings:

```bash
gcloud run services update geogemma-backend \
  --memory=4Gi \
  --cpu=2 \
  --region=us-central1
```

### Cold Start Times

Cloud Run services can experience cold starts. For improved startup times:
- Consider using the [min-instances](https://cloud.google.com/run/docs/configuring/min-instances) feature
- Optimize the Docker image to reduce startup time

## Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Earth Engine API Documentation](https://developers.google.com/earth-engine)
- [Cloud Run Service Account Configuration](https://cloud.google.com/run/docs/configuring/service-accounts) 