# Setting Up Firebase Authentication for GeoGemma

This guide will walk you through setting up Firebase Authentication and Firestore for GeoGemma.

## Step 1: Create a Firebase Project

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project" and follow the prompts to create a new project
3. Name your project (e.g., "GeoGemma")
4. Enable Google Analytics if desired
5. Click "Create project"

## Step 2: Set Up Authentication

1. In the Firebase Console, go to your project
2. In the left sidebar, click "Authentication"
3. Click "Get started"
4. In the "Sign-in method" tab, enable "Google" as a sign-in provider
5. Configure the Google provider:
   - Enter your project's support email
   - Save the changes

## Step 3: Create a Firestore Database

1. In the Firebase Console, go to your project
2. In the left sidebar, click "Firestore Database"
3. Click "Create database"
4. Choose "Start in test mode" for now (you can secure it later)
5. Select a database location closest to your users
6. Click "Enable"

## Step 4: Set Up a Web App

1. In the Firebase Console, go to your project
2. Click the web icon (</>) on the project overview page
3. Register your app:
   - Enter a nickname (e.g., "GeoGemma Web")
   - Check "Also set up Firebase Hosting" if desired
   - Click "Register app"
4. Copy the Firebase configuration object

## Step 5: Configure GeoGemma

### Backend Configuration

Create a `.env` file in the root directory of your project with the following:

```
# Firebase Configuration 
FIREBASE_CONFIG={"apiKey":"your-api-key","authDomain":"your-project-id.firebaseapp.com","projectId":"your-project-id","storageBucket":"your-project-id.appspot.com","messagingSenderId":"your-messaging-sender-id","appId":"your-app-id"}
```

Replace the values with your Firebase configuration.

### Frontend Configuration

Create a `.env` file in the `frontend` directory with the following:

```
# Firebase Configuration
VITE_FIREBASE_API_KEY=your-firebase-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your-messaging-sender-id
VITE_FIREBASE_APP_ID=your-app-id
```

Replace the values with your Firebase configuration.

## Step 6: Set Up Service Account for Backend (Optional)

For secure server-side operations, you should set up a service account:

1. In the Firebase Console, go to Project Settings
2. Go to the "Service accounts" tab
3. Click "Generate new private key"
4. Save the JSON file securely
5. Set the path to this file in your `.env`:

```
GOOGLE_APPLICATION_CREDENTIALS=path/to/your-service-account.json
```

## Step 7: Security Rules

After testing, update your Firestore security rules to secure your data:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
      
      match /{document=**} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
    }
    
    match /analytics/{document} {
      allow create: if request.auth != null;
      allow read: if false;
    }
  }
}
```

These rules ensure that:
- Users can only access their own data
- Analytics can be created but not read by clients

## Troubleshooting

- **Auth Popup Blocked**: Make sure to handle popup blocks by catching the error and providing a retry option
- **CORS Issues**: Ensure your Firebase project is configured to allow requests from your domain
- **Missing Credentials**: Double-check that all environment variables are set correctly 