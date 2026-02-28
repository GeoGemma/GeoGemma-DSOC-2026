import os
import json
import logging
from google.cloud import firestore
from google.oauth2 import service_account
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Firestore client with proper credentials handling
try:
    # Check if there's a service account JSON file path in the environment
    service_account_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    if service_account_path and os.path.exists(service_account_path):
        # If the GOOGLE_APPLICATION_CREDENTIALS environment variable is set and points to a valid file
        logging.info(f"Initializing Firestore with service account from: {service_account_path}")
        db = firestore.Client()
    else:
        # Look for service account JSON in the local directory (common file names)
        possible_files = [
            'firebase-adminsdk.json',
            'firebase-service-account.json',
            'firestore-service-account.json',
            'service-account.json'
        ]
        
        # Also look for any file matching the pattern *-firebase-*.json
        for filename in os.listdir('.'):
            if filename.endswith('.json') and ('firebase' in filename or 'firestore' in filename):
                if filename not in possible_files:
                    possible_files.append(filename)
        
        service_account_file = None
        for file in possible_files:
            if os.path.exists(file):
                service_account_file = file
                break
        
        if service_account_file:
            logging.info(f"Found service account file: {service_account_file}")
            # Initialize with the found service account file
            credentials = service_account.Credentials.from_service_account_file(
                service_account_file,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            db = firestore.Client(credentials=credentials)
        else:
            # Extract credentials from Firebase config if available in environment
            firebase_config = os.environ.get('FIREBASE_CONFIG')
            if firebase_config:
                try:
                    config = json.loads(firebase_config)
                    project_id = config.get('projectId')
                    if project_id:
                        logging.info(f"Initializing Firestore with project ID from environment: {project_id}")
                        db = firestore.Client(project=project_id)
                    else:
                        raise ValueError("No projectId found in FIREBASE_CONFIG")
                except (json.JSONDecodeError, ValueError) as e:
                    logging.error(f"Error parsing FIREBASE_CONFIG: {e}")
                    raise
            else:
                logging.error("No credentials found. Set GOOGLE_APPLICATION_CREDENTIALS environment variable or place service account JSON in project directory.")
                raise ValueError("No Firebase credentials found")
                
    logging.info("Firestore client initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize Firestore: {e}")
    # Create a placeholder DB object that will log errors but not throw exceptions
    # This allows the app to start even if Firebase isn't configured
    class NoOpFirestore:
        def collection(self, *args, **kwargs):
            logging.warning(f"Firestore not initialized. Ignoring collection({args}, {kwargs})")
            return self
            
        def document(self, *args, **kwargs):
            logging.warning(f"Firestore not initialized. Ignoring document({args}, {kwargs})")
            return self
            
        def set(self, *args, **kwargs):
            logging.warning(f"Firestore not initialized. Ignoring set({args}, {kwargs})")
            return None
            
        def update(self, *args, **kwargs):
            logging.warning(f"Firestore not initialized. Ignoring update({args}, {kwargs})")
            return None
            
        def get(self, *args, **kwargs):
            logging.warning(f"Firestore not initialized. Ignoring get({args}, {kwargs})")
            
            class MockDoc:
                @property
                def exists(self):
                    return False
                    
                def to_dict(self):
                    return None
                    
            return MockDoc()
            
        def stream(self, *args, **kwargs):
            logging.warning(f"Firestore not initialized. Ignoring stream({args}, {kwargs})")
            return []
            
        def add(self, *args, **kwargs):
            logging.warning(f"Firestore not initialized. Ignoring add({args}, {kwargs})")
            return None
    
    db = NoOpFirestore()
    logging.warning("Using NoOp Firestore client. Firebase operations will be logged but not executed.")

# --- User Profiles & Preferences ---
def create_user_profile(user_id: str, profile: Dict[str, Any]) -> None:
    logging.info(f"Creating user profile for user_id={user_id}")
    db.collection("users").document(user_id).set(profile)

def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    logging.info(f"Fetching user profile for user_id={user_id}")
    doc = db.collection("users").document(user_id).get()
    return doc.to_dict() if doc.exists else None

def update_user_profile(user_id: str, updates: Dict[str, Any]) -> None:
    logging.info(f"Updating user profile for user_id={user_id} with updates={updates}")
    db.collection("users").document(user_id).update(updates)

# --- Saved Map Layers ---
def save_map_layer(user_id: str, layer_id: str, layer_data: Dict[str, Any]) -> None:
    logging.info(f"Saving map layer for user_id={user_id}, layer_id={layer_id}")
    db.collection("users").document(user_id).collection("layers").document(layer_id).set(layer_data)

def get_map_layers(user_id: str) -> List[Dict[str, Any]]:
    logging.info(f"Fetching map layers for user_id={user_id}")
    layers = db.collection("users").document(user_id).collection("layers").stream()
    return [layer.to_dict() for layer in layers]

def delete_map_layer(user_id: str, layer_id: str) -> None:
    logging.info(f"Deleting map layer for user_id={user_id}, layer_id={layer_id}")
    db.collection("users").document(user_id).collection("layers").document(layer_id).delete()

def clear_user_layers(user_id: str) -> None:
    logging.info(f"Clearing all map layers for user_id={user_id}")
    # Get all layers for the user
    layers_ref = db.collection("users").document(user_id).collection("layers")
    batch = db.batch()
    
    # Firestore limits batches to 500 operations
    # So we need to get documents in smaller chunks if there might be many
    docs = list(layers_ref.limit(500).stream())
    
    if not docs:
        logging.info(f"No layers found to clear for user_id={user_id}")
        return
        
    # Add each document to the batch delete
    for doc in docs:
        batch.delete(doc.reference)
    
    # Commit the batch
    batch.commit()
    logging.info(f"Cleared {len(docs)} layers for user_id={user_id}")

# --- Analysis Results ---
def save_analysis(user_id: str, analysis_id: str, analysis_data: Dict[str, Any]) -> None:
    logging.info(f"Saving analysis for user_id={user_id}, analysis_id={analysis_id}")
    db.collection("users").document(user_id).collection("analyses").document(analysis_id).set(analysis_data)

def get_analyses(user_id: str) -> List[Dict[str, Any]]:
    logging.info(f"Fetching analyses for user_id={user_id}")
    analyses = db.collection("users").document(user_id).collection("analyses").stream()
    return [a.to_dict() for a in analyses]

# --- User Query & Chat History ---
def save_chat_message(user_id: str, message_id: str, message_data: Dict[str, Any]) -> None:
    logging.info(f"Saving chat message for user_id={user_id}, message_id={message_id}")
    db.collection("users").document(user_id).collection("chat_history").document(message_id).set(message_data)

def get_chat_history(user_id: str) -> List[Dict[str, Any]]:
    logging.info(f"Fetching chat history for user_id={user_id}")
    messages = db.collection("users").document(user_id).collection("chat_history").order_by("timestamp").stream()
    return [m.to_dict() for m in messages]

# --- Custom Areas/Locations ---
def save_custom_area(user_id: str, area_id: str, area_data: Dict[str, Any]) -> None:
    logging.info(f"Saving custom area for user_id={user_id}, area_id={area_id}")
    db.collection("users").document(user_id).collection("custom_areas").document(area_id).set(area_data)

def get_custom_areas(user_id: str) -> List[Dict[str, Any]]:
    logging.info(f"Fetching custom areas for user_id={user_id}")
    areas = db.collection("users").document(user_id).collection("custom_areas").stream()
    return [a.to_dict() for a in areas]

# --- Usage Analytics/Logs ---
def log_usage(event: Dict[str, Any]) -> None:
    logging.info(f"Logging analytics event: {event}")
    db.collection("analytics").add(event)