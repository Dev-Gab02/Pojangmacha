from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
import os
import uuid
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
container_name = os.getenv("AZURE_STORAGE_CONTAINER")

# Validate environment variables
if not connection_string:
    logger.error("AZURE_STORAGE_CONNECTION_STRING not set in .env")
if not container_name:
    logger.error("AZURE_STORAGE_CONTAINER not set in .env")

def upload_food_image(file_path):
    """
    Upload food image to Azure Blob Storage
    
    Args:
        file_path: Path to the image file
        
    Returns:
        str: Image URL if successful, None if failed
        
    Raises:
        ValueError: If Azure credentials are missing
    """
    
    # Validate inputs
    if not connection_string:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING is not configured")
    if not container_name:
        raise ValueError("AZURE_STORAGE_CONTAINER is not configured")
    if not file_path or not os.path.exists(file_path):
        raise ValueError(f"File not found: {file_path}")
    
    try:
        # Initialize client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Generate unique filename
        filename = f"{uuid.uuid4()}_{os.path.basename(file_path)}"
        
        # Get blob client
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=filename
        )
        
        # Upload file
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        
        logger.info(f"Successfully uploaded: {filename}")
        return blob_client.url
        
    except Exception as e:
        error_msg = f"Blob upload error: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)