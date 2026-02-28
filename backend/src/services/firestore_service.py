import os
import json
import logging
from typing import Any, Dict, List, Optional
from google.cloud import firestore
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

class FirestoreService:
    """
    Service for Firestore database operations.
    
    This service provides a clean interface to Firestore with error handling,
    connection pooling, and transactions.
    """
    
    # Singleton instance
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'FirestoreService':
        """Get the singleton instance of FirestoreService."""
        if cls._instance is None:
            cls._instance = FirestoreService()
        return cls._instance
    
    def __init__(self):
        self.db = self._initialize_firestore()
        self.is_initialized = self.db is not None
    
    def _initialize_firestore(self) -> Optional[firestore.Client]:
        """
        Initialize the Firestore client with proper credentials handling.
        Returns a NoOpFirestore if initialization fails.
        """
        try:
            # Check if there's a service account JSON file path in the environment
            service_account_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            
            if service_account_path and os.path.exists(service_account_path):
                # If the GOOGLE_APPLICATION_CREDENTIALS environment variable is set and valid
                logger.info(f"Initializing Firestore with service account from: {service_account_path}")
                return firestore.Client()
            else:
                # Look for service account JSON in multiple directories
                service_account_file = self._find_service_account_file()
                
                if service_account_file:
                    logger.info(f"Found service account file: {service_account_file}")
                    credentials = service_account.Credentials.from_service_account_file(
                        service_account_file,
                        scopes=["https://www.googleapis.com/auth/cloud-platform"]
                    )
                    return firestore.Client(credentials=credentials)
                else:
                    # Try Firebase config from environment
                    firebase_config = os.environ.get('FIREBASE_CONFIG')
                    if firebase_config:
                        try:
                            config = json.loads(firebase_config)
                            project_id = config.get('projectId')
                            if project_id:
                                logger.info(f"Initializing Firestore with project ID from environment: {project_id}")
                                return firestore.Client(project=project_id)
                            else:
                                raise ValueError("No projectId found in FIREBASE_CONFIG")
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.error(f"Error parsing FIREBASE_CONFIG: {e}")
                            raise
                    else:
                        logger.warning("No Firestore credentials found. Using NoOpFirestore as fallback.")
                        return NoOpFirestore()
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            return NoOpFirestore()
    
    def _find_service_account_file(self) -> Optional[str]:
        """Find a service account file in the current directory or parent directories."""
        possible_files = [
            'firebase-adminsdk.json',
            'firebase-service-account.json',
            'firestore-service-account.json',
            'service-account.json',
            'geogemma-f32a4-firebase-adminsdk-fbsvc-204a010d07.json'  # Known file in the project
        ]
        
        # Also look for any file matching common patterns
        for filename in os.listdir('.'):
            if filename.endswith('.json') and ('firebase' in filename or 'firestore' in filename):
                if filename not in possible_files:
                    possible_files.append(filename)
        
        # Check current directory first
        for file in possible_files:
            if os.path.exists(file):
                return file
        
        # Check parent directory
        for file in possible_files:
            parent_path = os.path.join('..', file)
            if os.path.exists(parent_path):
                return parent_path
        
        # Check specific project paths
        root_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'geogemma-f32a4-firebase-adminsdk-fbsvc-204a010d07.json')
        if os.path.exists(root_file):
            return root_file
        
        return None
    
    # --- User Profiles & Preferences ---
    
    def create_user_profile(self, user_id: str, profile: Dict[str, Any]) -> None:
        """Create or update a user profile."""
        try:
            logger.info(f"Creating user profile for user_id={user_id}")
            self.db.collection("users").document(user_id).set(profile)
        except Exception as e:
            logger.error(f"Error creating user profile: {e}")
            raise
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user profile by ID."""
        try:
            logger.info(f"Fetching user profile for user_id={user_id}")
            doc = self.db.collection("users").document(user_id).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> None:
        """Update a user profile with partial data."""
        try:
            logger.info(f"Updating user profile for user_id={user_id} with updates={updates}")
            self.db.collection("users").document(user_id).update(updates)
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            raise
    
    # --- Saved Map Layers ---
    
    def save_map_layer(self, user_id: str, layer_id: str, layer_data: Dict[str, Any]) -> None:
        """Save a map layer for a user."""
        try:
            logger.info(f"Saving map layer for user_id={user_id}, layer_id={layer_id}")
            self.db.collection("users").document(user_id).collection("layers").document(layer_id).set(layer_data)
        except Exception as e:
            logger.error(f"Error saving map layer: {e}")
            raise
    
    def get_map_layers(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all map layers for a user."""
        try:
            logger.info(f"Fetching map layers for user_id={user_id}")
            layers = self.db.collection("users").document(user_id).collection("layers").stream()
            return [layer.to_dict() for layer in layers]
        except Exception as e:
            logger.error(f"Error getting map layers: {e}")
            return []
    
    def delete_map_layer(self, user_id: str, layer_id: str) -> None:
        """Delete a map layer."""
        try:
            logger.info(f"Deleting map layer for user_id={user_id}, layer_id={layer_id}")
            self.db.collection("users").document(user_id).collection("layers").document(layer_id).delete()
        except Exception as e:
            logger.error(f"Error deleting map layer: {e}")
            raise
    
    def clear_user_layers(self, user_id: str) -> None:
        """Clear all map layers for a user."""
        try:
            logger.info(f"Clearing all map layers for user_id={user_id}")
            # Get all layers for the user
            layers_ref = self.db.collection("users").document(user_id).collection("layers")
            batch = self.db.batch()
            
            # Firestore limits batches to 500 operations
            docs = list(layers_ref.limit(500).stream())
            
            if not docs:
                logger.info(f"No layers found to clear for user_id={user_id}")
                return
                
            # Add each document to the batch delete
            for doc in docs:
                batch.delete(doc.reference)
            
            # Commit the batch
            batch.commit()
            logger.info(f"Cleared {len(docs)} layers for user_id={user_id}")
        except Exception as e:
            logger.error(f"Error clearing user layers: {e}")
            raise
    
    # --- Analysis Results ---
    
    def save_analysis(self, user_id: str, analysis_id: str, analysis_data: Dict[str, Any]) -> None:
        """Save an analysis result."""
        try:
            logger.info(f"Saving analysis for user_id={user_id}, analysis_id={analysis_id}")
            self.db.collection("users").document(user_id).collection("analyses").document(analysis_id).set(analysis_data)
        except Exception as e:
            logger.error(f"Error saving analysis: {e}")
            raise
    
    def get_analyses(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all analyses for a user."""
        try:
            logger.info(f"Fetching analyses for user_id={user_id}")
            analyses = self.db.collection("users").document(user_id).collection("analyses").stream()
            return [a.to_dict() for a in analyses]
        except Exception as e:
            logger.error(f"Error getting analyses: {e}")
            return []
    
    # --- User Query & Chat History ---
    
    def save_chat_message(self, user_id: str, message_id: str, message_data: Dict[str, Any]) -> None:
        """Save a chat message."""
        try:
            logger.info(f"Saving chat message for user_id={user_id}, message_id={message_id}")
            self.db.collection("users").document(user_id).collection("chat_history").document(message_id).set(message_data)
        except Exception as e:
            logger.error(f"Error saving chat message: {e}")
            raise
    
    def get_chat_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a user, ordered by timestamp."""
        try:
            logger.info(f"Fetching chat history for user_id={user_id}")
            messages = self.db.collection("users").document(user_id).collection("chat_history").order_by("timestamp").stream()
            return [m.to_dict() for m in messages]
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []
    
    # --- Custom Areas/Locations ---
    
    def save_custom_area(self, user_id: str, area_id: str, area_data: Dict[str, Any]) -> None:
        """Save a custom area."""
        try:
            logger.info(f"Saving custom area for user_id={user_id}, area_id={area_id}")
            self.db.collection("users").document(user_id).collection("custom_areas").document(area_id).set(area_data)
        except Exception as e:
            logger.error(f"Error saving custom area: {e}")
            raise
    
    def get_custom_areas(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all custom areas for a user."""
        try:
            logger.info(f"Fetching custom areas for user_id={user_id}")
            areas = self.db.collection("users").document(user_id).collection("custom_areas").stream()
            return [a.to_dict() for a in areas]
        except Exception as e:
            logger.error(f"Error getting custom areas: {e}")
            return []
    
    # --- Usage Analytics/Logs ---
    
    def log_usage(self, event: Dict[str, Any]) -> None:
        """Log a usage event."""
        try:
            logger.info(f"Logging analytics event: {event}")
            self.db.collection("analytics").add(event)
        except Exception as e:
            logger.error(f"Error logging usage: {e}")


# A placeholder class that logs warnings but doesn't throw exceptions
class NoOpFirestore:
    """
    A no-op implementation of Firestore client.
    This allows the app to start even if Firestore isn't configured.
    """
    
    def collection(self, *args, **kwargs):
        logger.warning(f"Firestore not initialized. Ignoring collection({args}, {kwargs})")
        return self
        
    def document(self, *args, **kwargs):
        logger.warning(f"Firestore not initialized. Ignoring document({args}, {kwargs})")
        return self
        
    def set(self, *args, **kwargs):
        logger.warning(f"Firestore not initialized. Ignoring set({args}, {kwargs})")
        return None
        
    def update(self, *args, **kwargs):
        logger.warning(f"Firestore not initialized. Ignoring update({args}, {kwargs})")
        return None
        
    def get(self, *args, **kwargs):
        logger.warning(f"Firestore not initialized. Ignoring get({args}, {kwargs})")
        
        class MockDoc:
            @property
            def exists(self):
                return False
                
            def to_dict(self):
                return None
                
        return MockDoc()
        
    def stream(self, *args, **kwargs):
        logger.warning(f"Firestore not initialized. Ignoring stream({args}, {kwargs})")
        return []
        
    def add(self, *args, **kwargs):
        logger.warning(f"Firestore not initialized. Ignoring add({args}, {kwargs})")
        return None
    
    def delete(self, *args, **kwargs):
        logger.warning(f"Firestore not initialized. Ignoring delete({args}, {kwargs})")
        return None
    
    def limit(self, *args, **kwargs):
        logger.warning(f"Firestore not initialized. Ignoring limit({args}, {kwargs})")
        return self
    
    def order_by(self, *args, **kwargs):
        logger.warning(f"Firestore not initialized. Ignoring order_by({args}, {kwargs})")
        return self
    
    def batch(self, *args, **kwargs):
        logger.warning(f"Firestore not initialized. Ignoring batch({args}, {kwargs})")
        return self


# Export the singleton instance
firestore_service = FirestoreService.get_instance() 