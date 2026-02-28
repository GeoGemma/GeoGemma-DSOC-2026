# --- authenticate_ee.py ---
import os
import logging
import ee
import json
import tempfile

# ------------------------------------------------------------------
# Logging setup (unchanged)
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("earth_engine_auth")

# ------------------------------------------------------------------
# If you keep a dev‑only JSON in the repo, allow it for local runs
# ------------------------------------------------------------------
FALLBACK_LOCAL_KEY = "/Users/khalil/Documents/Github/GeoGemma/backend/ee-service-account.json"
if os.path.exists(FALLBACK_LOCAL_KEY):
    logger.info(
        "Detected Earth Engine credentials at %s; "
        "configuring GOOGLE_APPLICATION_CREDENTIALS for local run.",
        FALLBACK_LOCAL_KEY,
    )
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = FALLBACK_LOCAL_KEY

# ------------------------------------------------------------------
# Internal helper – decide which credential object to use
# ------------------------------------------------------------------
def _build_credentials():
    """
    Return an ee.Credentials‑compatible object for service account authentication.
    
    This function handles two scenarios:
    1. GOOGLE_APPLICATION_CREDENTIALS points to a valid file path
    2. GOOGLE_APPLICATION_CREDENTIALS contains the JSON content of the service account key
    
    In both cases, a service account email is required in EE_SERVICE_ACCOUNT_EMAIL.
    """
    key_content = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    sa_email = os.getenv("EE_SERVICE_ACCOUNT_EMAIL")
    
    # Validate the service account email
    if not sa_email:
        raise RuntimeError(
            "EE_SERVICE_ACCOUNT_EMAIL environment variable is required."
        )
    
    # Check if GOOGLE_APPLICATION_CREDENTIALS is not set
    if not key_content:
        raise RuntimeError(
            "GOOGLE_APPLICATION_CREDENTIALS environment variable is not set."
        )
    
    # Case 1: GOOGLE_APPLICATION_CREDENTIALS is a file path
    if os.path.isfile(key_content):
        logger.info("Using ServiceAccountCredentials from file path: %s", key_content)
        return ee.ServiceAccountCredentials(sa_email, key_content)
    
    # Case 2: GOOGLE_APPLICATION_CREDENTIALS contains JSON content (Cloud Run with --set-secrets)
    # Try to parse it as JSON
    try:
        # Check if the content appears to be JSON
        if key_content.strip().startswith("{") and "private_key" in key_content:
            logger.info("GOOGLE_APPLICATION_CREDENTIALS contains JSON content, writing to temp file")
            
            # Create a temporary file to store the credentials
            tmp_dir = tempfile.gettempdir()
            tmp_key_path = os.path.join(tmp_dir, "ee_service_account_key.json")
            
            # Write the JSON content to the temporary file
            with open(tmp_key_path, "w") as f:
                f.write(key_content)
            
            logger.info("Created temporary credentials file at: %s", tmp_key_path)
            return ee.ServiceAccountCredentials(sa_email, tmp_key_path)
    except Exception as e:
        logger.error("Failed to parse JSON content from GOOGLE_APPLICATION_CREDENTIALS: %s", e)
    
    # If we got here, neither case worked
    raise RuntimeError(
        "GOOGLE_APPLICATION_CREDENTIALS must either be a valid file path "
        "or contain valid JSON content of a service account key."
    )

# ------------------------------------------------------------------
# Public function – call this during FastAPI startup
# ------------------------------------------------------------------
def initialize_ee(project_id: str):
    """
    Initialize Earth Engine for the given billing project.

    Returns:
        (success: bool, error_message: str | None)
    """
    if not project_id:
        msg = "Project ID was not provided to initialize_ee."
        logger.error(msg)
        return False, msg

    try:
        # Always use service account credentials
        creds = _build_credentials()

        # Always initialize with explicit project and credentials
        ee.Initialize(
            credentials=creds,
            project=project_id,
            opt_url="https://earthengine-highvolume.googleapis.com",
        )
        
        # Quick probe – forces a request, catches bad perms early
        ee.Image(1).getInfo()

        logger.info("Earth Engine initialized successfully for project %s", project_id)
        return True, None

    except Exception as e:
        logger.error("Earth Engine initialization failed: %s", e, exc_info=True)
        return False, str(e)

# ------------------------------------------------------------------
# CLI test hook – unchanged except for using the new initialize_ee
# ------------------------------------------------------------------
if __name__ == "__main__":
    from dotenv import load_dotenv

    print("Running EE Authentication Test…")
    load_dotenv()  # allow .env when executed directly

    test_project_id = os.getenv("EE_PROJECT_ID")
    if not test_project_id:
        print(
            "\nERROR: EE_PROJECT_ID not found in environment variables or .env file."
            "\nPlease set EE_PROJECT_ID for testing."
        )
    else:
        print(f"Attempting initialization with Project ID: {test_project_id}")
        success, error = initialize_ee(test_project_id)
        if success:
            print("\nAuthentication and initialization successful!")
        else:
            print(f"\nError: {error}")
