"""
Firebase storage module for the GIS AI Agent.

This module provides functionality for persisting chat history and session data
in Firebase Realtime Database, including encryption for sensitive data.
"""

import json
import logging
import asyncio
import time
import base64
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import os
import aiohttp
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configure logging
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
RETRY_DELAY = 0.5  # seconds

class FirebaseStorage:
    """
    Firebase Realtime Database storage for chat history and sessions.
    
    This class manages:
    - Session persistence
    - Chat history storage
    - Encryption/decryption of sensitive data
    - Data synchronization
    """
    
    def __init__(self, 
                database_url: Optional[str] = None,
                api_key: Optional[str] = None,
                encryption_key: Optional[str] = None,
                disabled: bool = False):
        """
        Initialize the Firebase storage.
        
        Args:
            database_url: Firebase Realtime Database URL. 
                          If None, uses FIREBASE_DB_URL environment variable.
            api_key: Firebase API key.
                     If None, uses FIREBASE_API_KEY environment variable.
            encryption_key: Key used to encrypt sensitive data.
                            If None, uses FIREBASE_ENCRYPTION_KEY environment variable.
            disabled: If True, Firebase storage will be disabled and all operations will be no-ops.
        """
        # Check if Firebase is explicitly disabled
        self.disabled = disabled or os.environ.get("DISABLE_FIREBASE", "").lower() == "true"
        
        if self.disabled:
            logger.info("Firebase storage is explicitly disabled")
            self.is_configured = False
            self.database_url = None
            self.api_key = None
            self.cipher = None
            self._session = None
            self._database_exists = False
            return
            
        self.database_url = database_url or os.environ.get("FIREBASE_DB_URL")
        self.api_key = api_key or os.environ.get("FIREBASE_API_KEY")
        
        # Fix the database URL format if needed
        if self.database_url:
            # Remove trailing slash
            if self.database_url.endswith('/'):
                self.database_url = self.database_url[:-1]
                logger.info("Removed trailing slash from Firebase database URL")
                
            # Ensure it has the correct format
            if not 'firebaseio.com' in self.database_url:
                # Add 'https://' prefix if missing
                if not self.database_url.startswith('http'):
                    self.database_url = f"https://{self.database_url}"
                    logger.info("Added https:// prefix to Firebase database URL")
                    
                # Add firebaseio.com suffix if missing
                if not self.database_url.endswith('firebaseio.com'):
                    # Add period if needed
                    if not self.database_url.endswith('.'):
                        self.database_url = f"{self.database_url}."
                    self.database_url = f"{self.database_url}firebaseio.com"
                    logger.info(f"Updated Firebase database URL format: {self.database_url}")
        
        # Set up encryption
        self._initialize_encryption(encryption_key or os.environ.get("FIREBASE_ENCRYPTION_KEY"))
        
        # Check if we have the required configuration
        self.is_configured = bool(self.database_url and self.api_key and self.cipher)
        
        if not self.is_configured:
            missing = []
            if not self.database_url:
                missing.append("database_url")
            if not self.api_key:
                missing.append("api_key")
            if not self.cipher:
                missing.append("encryption_key")
            
            logger.warning(f"Firebase storage not fully configured (missing: {', '.join(missing)}), will operate in memory-only mode")
            # Explicitly mark as disabled if not configured
            self.disabled = True
        else:
            logger.info(f"Firebase storage initialized with database URL: {self.database_url}")
            
        # For connection pooling
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Flag to track if database exists - will be set during first request
        self._database_exists = None
    
    def _initialize_encryption(self, key: Optional[str]) -> None:
        """
        Initialize the encryption cipher with the provided key.
        
        Args:
            key: Encryption key or passphrase.
        """
        self.cipher = None
        
        if not key:
            logger.warning("No encryption key provided for Firebase storage")
            return
        
        try:
            # If the key is not in the correct format, derive a key using PBKDF2
            if len(key) != 44 or not key.endswith('='):
                # Generate a key using PBKDF2
                salt = b'GISAgent'  # Static salt - in production, this should be stored securely
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
                self.cipher = Fernet(derived_key)
                logger.info("Initialized encryption with derived key")
            else:
                # Key is already in the correct format
                self.cipher = Fernet(key.encode())
                logger.info("Initialized encryption with provided Fernet key")
                
        except Exception as e:
            logger.error(f"Error initializing encryption: {e}")
            self.cipher = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """
        Get or create an aiohttp ClientSession.
        
        Returns:
            A ClientSession for making HTTP requests.
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        
        return self._session
    
    async def close(self) -> None:
        """Close resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def _encrypt_data(self, data: Union[str, Dict, List]) -> str:
        """
        Encrypt data using the configured cipher.
        
        Args:
            data: The data to encrypt (will be converted to JSON).
            
        Returns:
            Base64-encoded encrypted data.
        """
        if not self.cipher:
            raise ValueError("Encryption not configured")
        
        # Convert data to JSON string if it's not already a string
        if not isinstance(data, str):
            data = json.dumps(data)
        
        # Encrypt the data
        encrypted_data = self.cipher.encrypt(data.encode())
        
        # Convert to a Base64 string for storage
        return base64.b64encode(encrypted_data).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> Any:
        """
        Decrypt data using the configured cipher.
        
        Args:
            encrypted_data: Base64-encoded encrypted data.
            
        Returns:
            Decrypted data, parsed as JSON if possible.
        """
        if not self.cipher:
            raise ValueError("Encryption not configured")
        
        # Decode from Base64
        encrypted_bytes = base64.b64decode(encrypted_data)
        
        # Decrypt the data
        decrypted_data = self.cipher.decrypt(encrypted_bytes).decode()
        
        # Try to parse as JSON
        try:
            return json.loads(decrypted_data)
        except json.JSONDecodeError:
            # Return as string if not valid JSON
            return decrypted_data
            
    async def _firebase_request(self, method: str, path: str, json_data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make a request to Firebase with automatic retries.
        
        Args:
            method: HTTP method ('get', 'put', 'patch', 'delete')
            path: Path to the Firebase resource
            json_data: JSON data to send (for PUT, PATCH)
            
        Returns:
            Response data as dict or None on error
        """
        if self.disabled:
            logger.debug(f"Firebase is disabled, skipping {method} request")
            return None
            
        if not self.is_configured:
            logger.warning(f"Firebase not configured, skipping {method} request to {path}")
            return None
            
        # If we've already determined the database doesn't exist, fail fast
        if self._database_exists is False and method.lower() != 'get':
            logger.debug(f"Skipping {method} request - database doesn't exist")
            return None
            
        # Ensure the database URL is properly formatted
        base_url = self.database_url
        if not base_url.endswith('.firebaseio.com'):
            # Check if we need to add the default RTD suffix
            if not 'firebaseio.com' in base_url:
                if not base_url.endswith('.'):
                    base_url = f"{base_url}."
                base_url = f"{base_url}firebaseio.com"
            
        # Add .json suffix if not present to the path
        if not path.endswith('.json'):
            path = f"{path}.json"
            
        # Ensure path starts with /
        if not path.startswith('/'):
            path = f"/{path}"
        
        # Build the complete URL
        url = f"{base_url}{path}"
        
        # Add query parameters
        params = {}
        if self.api_key:
            params['auth'] = self.api_key
        
        # Log the request details (excluding sensitive info)
        masked_url = url.replace(self.api_key, "***") if self.api_key and self.api_key in url else url
        logger.debug(f"Firebase {method.upper()} request to {masked_url}")
        
        session = await self.get_session()
        retries = 0
        
        while retries < MAX_RETRIES:
            try:
                if method.lower() == 'get':
                    async with session.get(url, params=params) as response:
                        if response.status == 404:
                            # Record that the database doesn't exist to avoid future requests
                            if path == '/.json' and self._database_exists is None:
                                self._database_exists = False
                                logger.warning("Firebase database does not exist - disabling write operations")
                                
                            logger.debug(f"Resource not found: {path}")
                            return None
                        elif response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Firebase {method} error: {response.status} - {error_text}")
                            retries += 1
                            if retries < MAX_RETRIES:
                                await asyncio.sleep(RETRY_DELAY * (2 ** retries))  # Exponential backoff
                                continue
                            return None
                        
                        # If we get here successfully, the database exists
                        if path == '/.json' and self._database_exists is None:
                            self._database_exists = True
                            logger.info("Verified Firebase database exists")
                            
                        return await response.json()
                        
                elif method.lower() == 'put':
                    # Skip if we know the database doesn't exist
                    if self._database_exists is False:
                        logger.debug(f"Skipping PUT request - database doesn't exist")
                        return None
                        
                    async with session.put(url, json=json_data, params=params) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Firebase {method} error: {response.status} - {error_text}")
                            
                            # If the database doesn't exist, mark it
                            if response.status == 404:
                                self._database_exists = False
                                logger.warning("Firebase database does not exist - disabling write operations")
                                # Return empty dict for 404 to emulate success when database doesn't exist
                                # This prevents cascading errors
                                return {}
                                
                            retries += 1
                            if retries < MAX_RETRIES:
                                await asyncio.sleep(RETRY_DELAY * (2 ** retries))
                                continue
                            return None
                        return await response.json()
                        
                elif method.lower() == 'patch':
                    # Skip if we know the database doesn't exist
                    if self._database_exists is False:
                        logger.debug(f"Skipping PATCH request - database doesn't exist")
                        return None
                        
                    async with session.patch(url, json=json_data, params=params) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Firebase {method} error: {response.status} - {error_text}")
                            
                            # If the database doesn't exist, mark it
                            if response.status == 404:
                                self._database_exists = False
                                logger.warning("Firebase database does not exist - disabling write operations")
                                # Return empty dict for 404 to emulate success when database doesn't exist
                                # This prevents cascading errors
                                return {}
                                
                            retries += 1
                            if retries < MAX_RETRIES:
                                await asyncio.sleep(RETRY_DELAY * (2 ** retries))
                                continue
                            return None
                        return await response.json()
                        
                elif method.lower() == 'delete':
                    # Skip if we know the database doesn't exist
                    if self._database_exists is False:
                        logger.debug(f"Skipping DELETE request - database doesn't exist")
                        return None
                        
                    async with session.delete(url, params=params) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Firebase {method} error: {response.status} - {error_text}")
                            
                            # If the database doesn't exist, mark it
                            if response.status == 404:
                                self._database_exists = False
                                logger.warning("Firebase database does not exist - disabling write operations")
                                # Return empty dict for 404 to emulate success when database doesn't exist
                                # This prevents cascading errors
                                return {}
                                
                            retries += 1
                            if retries < MAX_RETRIES:
                                await asyncio.sleep(RETRY_DELAY * (2 ** retries))
                                continue
                            return None
                        
                        # Firebase sometimes returns empty response for delete operations
                        # that actually succeeded, so we handle this special case
                        try:
                            return await response.json()
                        except (json.JSONDecodeError, aiohttp.ContentTypeError):
                            logger.info(f"Empty response from Firebase delete operation (this is normal)")
                            return {}  # Return empty dict instead of None to indicate success
                
            except aiohttp.ClientError as e:
                logger.error(f"Firebase request error: {e}")
                retries += 1
                if retries < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY * (2 ** retries))
                    continue
                return None
                
            except asyncio.TimeoutError:
                logger.error(f"Firebase request timeout")
                retries += 1
                if retries < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY * (2 ** retries))
                    continue
                return None
                
            break  # Exit loop on success
                
        return None  # Return None if all retries failed
    
    async def check_database_exists(self) -> bool:
        """
        Check if the Firebase database exists.
        
        Returns:
            True if the database exists, False otherwise.
        """
        if self.disabled:
            return False
            
        if not self.is_configured:
            return False
            
        # If we've already checked, return the result
        if self._database_exists is not None:
            return self._database_exists
            
        # Try to access the root node
        result = await self._firebase_request('get', "/")
        
        # _firebase_request will set self._database_exists
        return self._database_exists or False
    
    async def save_chat_history(self, session_id: str, messages: List[Dict[str, Any]]) -> bool:
        """
        Save chat history for a session to Firebase.
        
        Args:
            session_id: The session ID.
            messages: List of message dictionaries.
            
        Returns:
            True if saved successfully, False otherwise.
        """
        if self.disabled:
            return True  # Pretend success when disabled
            
        if not self.is_configured:
            logger.debug("Not saving chat history: Firebase not configured")
            return True  # Pretend success when not configured
            
        # If we know the database doesn't exist, fail fast
        if self._database_exists is False:
            logger.debug("Not saving chat history: Firebase database doesn't exist")
            return True  # Pretend success to avoid errors
        
        try:
            # Encrypt the messages
            encrypted_data = self._encrypt_data(messages)
            
            # Create the payload
            payload = {
                "updated_at": datetime.now().isoformat(),
                "messages": encrypted_data
            }
            
            # Save to Firebase using the helper method
            result = await self._firebase_request('put', f"/chat_history/{session_id}", payload)
            
            if result is not None:
                logger.debug(f"Saved chat history for session {session_id} to Firebase")
                return True
            else:
                # If database doesn't exist, log once but don't treat as error
                if self._database_exists is False:
                    logger.debug(f"Skipped saving chat history (database doesn't exist)")
                    return True
                else:
                    logger.error(f"Failed to save chat history for session {session_id}")
                    return False
        
        except Exception as e:
            logger.error(f"Error saving chat history to Firebase: {e}")
            return False
    
    async def load_chat_history(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Load chat history for a session from Firebase.
        
        Args:
            session_id: The session ID.
            
        Returns:
            List of message dictionaries, or None if no history found or error occurred.
        """
        if self.disabled:
            return None
            
        if not self.is_configured:
            logger.debug("Not loading chat history: Firebase not configured")
            return None
        
        try:
            # Load from Firebase using the helper method
            data = await self._firebase_request('get', f"/chat_history/{session_id}")
            
            if not data or "messages" not in data:
                logger.debug(f"No chat history found for session {session_id}")
                return None
            
            # Decrypt the messages
            try:
                messages = self._decrypt_data(data["messages"])
                logger.debug(f"Loaded chat history for session {session_id} from Firebase")
                return messages
            except Exception as e:
                logger.error(f"Error decrypting chat history: {e}")
                return None
        
        except Exception as e:
            logger.error(f"Error loading chat history from Firebase: {e}")
            return None
    
    async def delete_chat_history(self, session_id: str) -> bool:
        """
        Delete chat history for a session from Firebase.
        
        Args:
            session_id: The session ID.
            
        Returns:
            True if deleted successfully, False otherwise.
        """
        if self.disabled:
            return True  # Pretend success when disabled
            
        if not self.is_configured:
            logger.debug("Not deleting chat history: Firebase not configured")
            return True  # Pretend success when not configured
            
        # If we know the database doesn't exist, fail fast
        if self._database_exists is False:
            logger.debug("Not deleting chat history: Firebase database doesn't exist")
            return True  # Pretend success to avoid errors
        
        try:
            # Delete from Firebase using the helper method
            result = await self._firebase_request('delete', f"/chat_history/{session_id}")
            
            # Check if Firebase returned a successful response
            if result is not None:
                logger.debug(f"Deleted chat history for session {session_id} from Firebase")
                return True
            else:
                # As a backup verification, try to load the data after deletion
                # If it's gone, that means deletion was successful despite the error
                verification = await self.load_chat_history(session_id)
                if verification is None:
                    logger.debug(f"Deletion verified for session {session_id} (data not found)")
                    return True
                
                logger.error(f"Failed to delete chat history for session {session_id}")
                return False
        
        except Exception as e:
            logger.error(f"Error deleting chat history from Firebase: {e}")
            return False
    
    async def save_session_metadata(self, session_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Save session metadata to Firebase.
        
        Args:
            session_id: The session ID.
            metadata: Session metadata.
            
        Returns:
            True if saved successfully, False otherwise.
        """
        if self.disabled:
            return True  # Pretend success when disabled
            
        if not self.is_configured:
            return True  # Pretend success when not configured
            
        # If we know the database doesn't exist, fail fast
        if self._database_exists is False:
            logger.debug("Not saving session metadata: Firebase database doesn't exist")
            return True  # Pretend success to avoid errors
        
        try:
            # Create the payload
            payload = {
                "updated_at": datetime.now().isoformat(),
                "user_id": metadata.get("user_id", "anonymous"),
                "created_at": metadata.get("created_at", datetime.now().isoformat()),
                "last_activity": datetime.now().isoformat(),
                "client_info": self._encrypt_data(metadata.get("client_info", {}))
            }
            
            # Save to Firebase using the helper method
            result = await self._firebase_request('put', f"/sessions/{session_id}", payload)
            
            if result is not None:
                logger.debug(f"Saved session metadata for {session_id} to Firebase")
                return True
            else:
                # If database doesn't exist, log once but don't treat as error
                if self._database_exists is False:
                    logger.debug(f"Skipped saving session metadata (database doesn't exist)")
                    return True
                else:
                    logger.error(f"Failed to save session metadata for {session_id}")
                    return False
        
        except Exception as e:
            logger.error(f"Error saving session metadata: {e}")
            return False
    
    async def update_last_activity(self, session_id: str) -> bool:
        """
        Update the last activity timestamp for a session.
        
        Args:
            session_id: The session ID.
            
        Returns:
            True if updated successfully, False otherwise.
        """
        if self.disabled:
            return True  # Pretend success when disabled
            
        if not self.is_configured:
            return True  # Pretend success when not configured
            
        # If we know the database doesn't exist, fail fast
        if self._database_exists is False:
            logger.debug("Not updating last activity: Firebase database doesn't exist")
            return True  # Pretend success to avoid errors
        
        try:
            # Create the payload
            payload = {
                "last_activity": datetime.now().isoformat()
            }
            
            # Update in Firebase using the helper method
            result = await self._firebase_request('patch', f"/sessions/{session_id}", payload)
            
            if result is not None:
                logger.debug(f"Updated last activity for session {session_id}")
                return True
            else:
                # If database doesn't exist, log once but don't treat as error
                if self._database_exists is False:
                    logger.debug(f"Skipped updating last activity (database doesn't exist)")
                    return True
                else:
                    logger.error(f"Failed to update last activity for session {session_id}")
                    return False
        
        except Exception as e:
            logger.error(f"Error updating last activity: {e}")
            return False
    
    async def verify_database_connection(self) -> bool:
        """
        Verify that the Firebase database exists and is accessible.
        
        Returns:
            True if the database is accessible, False otherwise.
        """
        if self.disabled:
            return False
            
        if not self.is_configured:
            return False
            
        # Try to read the root node
        result = await self._firebase_request('get', "/")
        if result is not None:
            logger.info("Successfully verified Firebase database connection")
            return True
        elif self._database_exists is False:
            logger.warning("Firebase database does not exist")
            return False
        else:
            logger.error("Failed to connect to Firebase database - check permissions and database existence")
            return False


# Create a singleton instance
_firebase_storage = None


def get_firebase_storage(disabled: bool = False) -> FirebaseStorage:
    """
    Get the Firebase storage instance.
    
    Args:
        disabled: If True, return a disabled Firebase storage instance.
    
    Returns:
        A FirebaseStorage instance.
    """
    global _firebase_storage
    
    # Check environment variable for disabling Firebase
    env_disabled = os.environ.get("DISABLE_FIREBASE", "").lower() == "true"
    
    # If disabled via arg or env var, and we already have an instance, create a new disabled one
    if (disabled or env_disabled) and _firebase_storage is not None and not _firebase_storage.disabled:
        logger.info("Creating new disabled Firebase storage instance")
        _firebase_storage = FirebaseStorage(disabled=True)
    
    # If not already created, create it
    if _firebase_storage is None:
        if disabled or env_disabled:
            logger.info("Creating disabled Firebase storage instance due to explicit disable flag")
        _firebase_storage = FirebaseStorage(disabled=disabled or env_disabled)
    
    return _firebase_storage 