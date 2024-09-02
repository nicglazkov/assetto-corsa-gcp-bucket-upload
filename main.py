import os
import shutil
from zipfile import ZipFile
from google.cloud import storage
from dotenv import load_dotenv
from base_content import BASE_GAME_CARS, BASE_GAME_TRACKS  # Import base content
import subprocess
import json  # Import for reading and writing JSON files

# Load environment variables from .env file
load_dotenv()

# Print environment variables for debugging
print("GCP_BUCKET_NAME:", os.getenv("GCP_BUCKET_NAME"))
print("ASSETTO_CORSA_DIR:", os.getenv("ASSETTO_CORSA_DIR"))

# Load environment-specific variables
gcp_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
bucket_name = os.getenv("GCP_BUCKET_NAME")
assetto_corsa_dir = os.getenv("ASSETTO_CORSA_DIR")
vm_instance_name = os.getenv("GCP_VM_INSTANCE_NAME")  # VM instance name
vm_zone = os.getenv("GCP_VM_ZONE")  # VM zone
vm_destination_path = os.getenv("GCP_VM_DESTINATION_PATH")  # VM destination path

# Verify that all required environment variables are set
if (
    not gcp_credentials_path
    or not bucket_name
    or not assetto_corsa_dir
    or not vm_instance_name
    or not vm_zone
    or not vm_destination_path
):
    print("Error: Missing required environment variables. Please check your .env file.")
    exit(1)

# Set the environment variable for Google Cloud authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcp_credentials_path


def find_non_base_content(zip_file_path):
    """Identify non-base game content in the zip file."""
    car_files_to_upload = set()
    track_files_to_upload = set()

    try:
        with ZipFile(zip_file_path, "r") as zip_ref:
            # Iterate over each file in the zip archive
            for file in zip_ref.namelist():
                if file.startswith("content/cars/"):
                    car_name = file.split("/")[2]
                    if car_name not in BASE_GAME_CARS:
                        car_files_to_upload.add(car_name)
                elif file.startswith("content/tracks/"):
                    track_name = file.split("/")[2]
                    if track_name not in BASE_GAME_TRACKS:
                        track_files_to_upload.add(track_name)

        return list(car_files_to_upload), list(track_files_to_upload)

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
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        # Use forward slashes for GCS paths
        destination_blob_name = (
            f"{destination_path}/{os.path.basename(file_path)}".replace("\\", "/")
        )

        # Check if file already exists in GCS
        print(f"Checking if {destination_blob_name} exists in GCS...")
        if file_exists_in_gcs(bucket_name, destination_blob_name):
            print(
                f"File {destination_blob_name} already exists in GCS. Skipping upload."
            )
            return

        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(file_path)
        blob.make_public()
        print(f"File {file_path} uploaded to {blob.public_url}")
    except Exception as e:
        print(f"Error uploading file {file_path} to GCS: {e}")


def upload_to_gcp_vm(local_file_path):
    """Uploads the given file to a specified GCP VM instance using gcloud compute scp."""
    try:
        # Construct the command to upload the file to the VM instance
        scp_command = [
            "gcloud",
            "compute",
            "scp",
            local_file_path,
            f"{vm_instance_name}:{vm_destination_path}",
            "--zone",
            vm_zone,
        ]

        # Execute the command
        print("Uploading file to GCP VM instance...")

        subprocess.run(
            scp_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        print(
            f"File {local_file_path} uploaded to GCP VM instance at {vm_destination_path}."
        )
    except subprocess.CalledProcessError as e:
        print(f"Error uploading file to GCP VM: {e.stderr.decode()}")


def unzip_file(zip_file_path, extract_to):
    """Unzip the file to the specified directory."""
    try:
        with ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"Unzipped {zip_file_path} to {extract_to}.")
    except Exception as e:
        print(f"Error unzipping file {zip_file_path}: {e}")


def update_json_file(json_path, car_files, track_files):
    """Update the content.json file with missing URLs."""
    try:
        if os.path.exists(json_path):
            with open(json_path, "r") as json_file:
                content = json.load(json_file)
        else:
            content = {"cars": {}, "track": {}}

        # Update cars
        for car in car_files:
            if car not in content["cars"] or not content["cars"][car].get("url"):
                content["cars"][car] = {
                    "url": f"https://storage.googleapis.com/{bucket_name}/cars/{car}.zip"
                }

        # Update tracks
        for track in track_files:
            if track not in content["track"] or not content["track"].get("url"):
                content["track"][track] = {
                    "url": f"https://storage.googleapis.com/{bucket_name}/tracks/{track}.zip"
                }

        # Save the updated content back to the JSON file
        with open(json_path, "w") as json_file:
            json.dump(content, json_file, indent=2)

        print(f"Updated {json_path} with missing URLs.")

    except Exception as e:
        print(f"Error updating JSON file {json_path}: {e}")


def print_json_content(file_path):
    """Prints the contents of a JSON file if it exists."""
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as json_file:
                content = json.load(json_file)
                print(f"Contents of {file_path}:\n{json.dumps(content, indent=2)}")
        else:
            print(f"{file_path} does not exist.")
    except Exception as e:
        print(f"Error reading JSON file {file_path}: {e}")


def main():
    try:
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

        # Prepare directories for zipping and uploading
        os.makedirs("uploads", exist_ok=True)

        # Process car files
        for car in car_files:
            car_dir = os.path.join(assetto_corsa_dir, "cars", car)
            if os.path.exists(car_dir):
                zip_filename = os.path.join("uploads", car)

                # Check if the zip file already exists in GCS
                gcs_path = f"cars/{car}.zip"
                if file_exists_in_gcs(bucket_name, gcs_path):
                    print(
                        f"Zip file {gcs_path} already exists in GCS. Skipping upload."
                    )
                    continue  # Skip zipping and uploading if file already exists

                # Zip and upload the car directory
                zipped_file = zip_directory(car_dir, zip_filename)
                if zipped_file:
                    upload_file_to_gcs(zipped_file, bucket_name, "cars")
                    upload_to_gcp_vm(zipped_file)  # Upload to VM
            else:
                print(f"Car directory does not exist: {car_dir}")

        # Process track files
        for track in track_files:
            track_dir = os.path.join(assetto_corsa_dir, "tracks", track)
            if os.path.exists(track_dir):
                zip_filename = os.path.join("uploads", track)

                # Check if the zip file already exists in GCS
                gcs_path = f"tracks/{track}.zip"
                if file_exists_in_gcs(bucket_name, gcs_path):
                    print(
                        f"Zip file {gcs_path} already exists in GCS. Skipping upload."
                    )
                    continue  # Skip zipping and uploading if file already exists

                # Zip and upload the track directory
                zipped_file = zip_directory(track_dir, zip_filename)
                if zipped_file:
                    upload_file_to_gcs(zipped_file, bucket_name, "tracks")
                    upload_to_gcp_vm(zipped_file)  # Upload to VM
            else:
                print(f"Track directory does not exist: {track_dir}")

        # Unzip the original zip file locally after processing
        unzip_directory = os.path.join("uploads", "unzipped_content")
        os.makedirs(unzip_directory, exist_ok=True)
        unzip_file(zip_file_path, unzip_directory)

        # Update the JSON file with missing URLs
        content_json_path = os.path.join(
            unzip_directory, "cfg", "cm_content", "content.json"
        )
        update_json_file(content_json_path, car_files, track_files)

        # Print the contents of content.json if it exists
        print_json_content(content_json_path)

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
