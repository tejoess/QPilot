import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

# 🔹 Connection string from Environment
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

# 🔹 Default container (has public blob access enabled)
DEFAULT_CONTAINER = "container1"

# Create blob service client
if connection_string:
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    except Exception as e:
        print(f"⚠️ Warning: Failed to connect to Azure Storage: {e}")
        blob_service_client = None
else:
    print("⚠️ Warning: AZURE_STORAGE_CONNECTION_STRING not set.")
    blob_service_client = None

def upload_to_azure(local_path_or_bytes, container_name=DEFAULT_CONTAINER, blob_name=None, is_bytes=False):
    """
    Generic upload function for Azure Blob Storage.
    Supports local file paths or raw bytes.
    Returns a public blob URL (container must have public blob access enabled).
    """
    if not blob_service_client:
        return None

    try:
        container_client = blob_service_client.get_container_client(container_name)
        try:
            if not container_client.exists():
                container_client.create_container(public_access="blob")
        except Exception as ce:
            print(f"⚠️ Container creation note: {ce}")

        blob_client = container_client.get_blob_client(blob_name)

        if is_bytes:
            blob_client.upload_blob(local_path_or_bytes, overwrite=True)
        else:
            with open(local_path_or_bytes, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)

        # Plain public URL — works because container1 has public blob access
        account_name = blob_service_client.account_name
        blob_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}"
        return blob_url
    except Exception as e:
        print(f"❌ Azure Upload Error: {e}")
        return None

def upload_user_file(user_id, local_file_path, category="others"):
    """
    Uploads a file to Azure Blob Storage under a user folder.
    Returns user_id, file_name, and public blob link.
    """
    file_name = os.path.basename(local_file_path)
    blob_path = f"user_{user_id}/{category}/{file_name}"

    url = upload_to_azure(
        local_path_or_bytes=local_file_path,
        container_name=DEFAULT_CONTAINER,
        blob_name=blob_path
    )

    return {
        "user_id": user_id,
        "file_name": file_name,
        "blob_link": url
    }