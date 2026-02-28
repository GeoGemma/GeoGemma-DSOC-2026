# Google Earth Engine Setup Guide

This guide will help you set up Google Earth Engine authentication for the GIS Agent.

## Prerequisites

1. A Google Cloud Platform (GCP) account
2. Earth Engine API enabled in your GCP project
3. A service account with Earth Engine access

## Step 1: Create a GCP Project

If you don't already have a GCP project:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click on "Select a project" at the top of the page
3. Click "New Project"
4. Enter a project name and click "Create"

Make note of your Project ID, which you'll need later.

## Step 2: Enable the Earth Engine API

1. Go to the [Earth Engine API page](https://console.cloud.google.com/apis/library/earthengine.googleapis.com)
2. Make sure your new project is selected
3. Click "Enable"

## Step 3: Register for Earth Engine

1. Visit the [Earth Engine sign-up page](https://signup.earthengine.google.com/)
2. Complete the registration form
3. Wait for approval (usually within 1-2 business days)

## Step 4: Create a Service Account

1. Go to the [Service Accounts page](https://console.cloud.google.com/iam-admin/serviceaccounts) in GCP
2. Select your project
3. Click "Create Service Account"
4. Enter a name (e.g., "earth-engine-service")
5. Click "Create and Continue"
6. In the "Grant this service account access to project" section, add the "Earth Engine Resource Viewer" and "Earth Engine Resource Creator" roles
7. Click "Done"

## Step 5: Create a Service Account Key

1. Find your service account in the list
2. Click the three dots menu (⋮) and select "Manage Keys"
3. Click "Add Key" → "Create new key"
4. Select "JSON" and click "Create"
5. The JSON key file will be downloaded to your computer

## Step 6: Configure GIS Agent to Use Your Service Account

1. Move the downloaded JSON key file to a secure location (e.g., the GIS_Agent directory)
2. Create a copy of the api_keys.yaml.example file:
   ```
   cp config/api_keys.yaml.example config/api_keys.yaml
   ```
3. Edit the api_keys.yaml file:
   ```yaml
   google_earth_engine:
     service_account: "your-service-account@your-project.iam.gserviceaccount.com"  # From the JSON file
     private_key_file: "path/to/your-key-file.json"  # Path to the JSON file
     project_id: "your-gcp-project-id"  # Your GCP Project ID
   ```

## Step 7: Test Your Earth Engine Authentication

Run the test script to verify your Earth Engine authentication:

```bash
python examples/test_earth_engine_auth.py --service-account-file "path/to/your-key-file.json" --project-id "your-gcp-project-id"
```

If successful, you should see a message confirming that Earth Engine is properly authenticated.

## Alternative: Using Default Authentication

If you're running the GIS Agent on your personal machine and prefer to use your personal Google account instead of a service account:

1. Install the Earth Engine CLI:
   ```
   pip install earthengine-api
   ```

2. Authenticate with Earth Engine:
   ```
   earthengine authenticate
   ```

3. Initialize with your project:
   ```
   earthengine init --project=your-gcp-project-id
   ```

4. Run the GIS Agent without specifying a service account file.

## Troubleshooting

If you encounter authentication errors:

1. Ensure your service account has the necessary Earth Engine permissions
2. Verify your project has the Earth Engine API enabled
3. Check that the file path to your JSON key file is correct
4. Confirm your GCP project ID is correct
5. Ensure your Earth Engine account is fully activated

For more information, see the [Earth Engine Documentation](https://developers.google.com/earth-engine/guides/service_account). 