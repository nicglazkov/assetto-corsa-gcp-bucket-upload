import os
import shutil
from zipfile import ZipFile
from google.cloud import storage
from dotenv import load_dotenv
from base_content import BASE_GAME_CARS, BASE_GAME_TRACKS  # Import base content

# Load environment variables from .env file
load_dotenv()

# Load environment-specific variables
gcp_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
bucket_name = os.getenv("GCP_BUCKET_NAME")
assetto_corsa_dir = os.getenv("ASSETTO_CORSA_DIR")

# Verify that all required environment variables are set
if not gcp_credentials_path or not bucket_name or not assetto_corsa_dir:
    print("Error: Missing required environment variables. Please check your .env file.")
    exit(1)

# Set the environment variable for Google Cloud authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcp_credentials_path


def find_non_base_content(zip_file_path):
    """Identify non-base game content in the zip file."""
    car_files_to_upload = []
    track_files_to_upload = []

    try:
        with ZipFile(zip_file_path, "r") as zip_ref:
            # Iterate over each file in the zip archive
            for file in zip_ref.namelist():
                if file.startswith("content/cars/"):
                    car_name = file.split("/")[2]
                    if car_name not in BASE_GAME_CARS:
                        car_files_to_upload.append(car_name)
                elif file.startswith("content/tracks/"):
                    track_name = file.split("/")[2]
                    if track_name not in BASE_GAME_TRACKS:
                        track_files_to_upload.append(track_name)

        return car_files_to_upload, track_files_to_upload

    except Exception as e:
        print(f"Error reading zip file: {e}")
        return [], []


def zip_directory(source_dir, output_filename):
    """Zip the specified directory."""
    try:
        shutil.make_archive(output_filename, "zip", source_dir)
        print(f"Zipped {source_dir} to {output_filename}.zip")
        return f"{output_filename}.zip"
    except Exception as e:
        print(f"Error zipping directory {source_dir}: {e}")
        return None


def file_exists_in_gcs(bucket_name, destination_blob_name):
    """Checks if a file already exists in the specified GCS bucket."""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        return blob.exists()
    except Exception as e:
        print(f"Error checking if file exists in GCS: {e}")
        return False


def upload_file_to_gcs(file_path, bucket_name, destination_path):
    """Uploads a single file to the specified Google Cloud Storage bucket."""
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)

    # Use forward slashes for GCS paths
    destination_blob_name = f"{destination_path}/{os.path.basename(file_path)}".replace(
        "\\", "/"
    )

    # Check if file already exists in GCS
    if file_exists_in_gcs(bucket_name, destination_blob_name):
        print(f"File {destination_blob_name} already exists in GCS. Skipping upload.")
        return

    try:
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(file_path)
        blob.make_public()
        print(f"File {file_path} uploaded to {blob.public_url}")
    except Exception as e:
        print(f"Error uploading file {file_path} to GCS: {e}")


def main():
    # Get user input for zip file
    zip_file_path = input("Enter the path to the zip file: ").strip()

    # Verify that the file exists
    if not os.path.exists(zip_file_path):
        print(f"Error: The file {zip_file_path} does not exist.")
        return

    print(f"Processing zip file: {zip_file_path}")

    # Identify non-base content from the zip file
    car_files, track_files = find_non_base_content(zip_file_path)

    if not car_files and not track_files:
        print("No non-base content found in the zip file. Nothing to upload.")
        return

    print(
        f"Found {len(car_files)} car files and {len(track_files)} track files to upload."
    )

    # Process car files
    for car in car_files:
        car_dir = os.path.join(assetto_corsa_dir, "cars", car)
        if os.path.exists(car_dir):
            zip_filename = os.path.join("uploads", car)
            os.makedirs("uploads", exist_ok=True)
            zipped_file = zip_directory(car_dir, zip_filename)
            if zipped_file:
                upload_file_to_gcs(zipped_file, bucket_name, "cars")
        else:
            print(f"Car directory does not exist: {car_dir}")

    # Process track files
    for track in track_files:
        track_dir = os.path.join(assetto_corsa_dir, "tracks", track)
        if os.path.exists(track_dir):
            zip_filename = os.path.join("uploads", track)
            os.makedirs("uploads", exist_ok=True)
            zipped_file = zip_directory(track_dir, zip_filename)
            if zipped_file:
                upload_file_to_gcs(zipped_file, bucket_name, "tracks")
        else:
            print(f"Track directory does not exist: {track_dir}")


if __name__ == "__main__":
    main()
