from azure.storage.blob import BlobServiceClient
import os

# 🔹 Paste your connection string

# 🔹 Your container name
container_name = "container1"
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
# Create blob service client
blob_service_client = BlobServiceClient.from_connection_string(connection_string)


def upload_user_file(user_id, local_file_path):
    """
    Uploads a file to Azure Blob Storage under user folder
    Returns user_id, file_name, and blob link
    """

    # Extract file name from path
    file_name = os.path.basename(local_file_path)

    # Create blob path: user_101/file.txt
    blob_path = f"user_{user_id}/{file_name}"

    # Get blob client
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_path
    )

    # Upload file
    with open(local_file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    # Create public URL
    account_name = blob_service_client.account_name
    blob_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_path}"

    return {
        "user_id": user_id,
        "file_name": file_name,
        "blob_link": blob_url
    }