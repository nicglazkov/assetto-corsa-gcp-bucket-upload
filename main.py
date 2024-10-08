import os
import shutil
from zipfile import ZipFile
from google.cloud import storage
from dotenv import load_dotenv
from base_content import BASE_GAME_CARS, BASE_GAME_TRACKS  # Import base content
import subprocess
import json  # Import for reading and writing JSON files
import urllib.parse  # Import for URL encoding
import logging  # Import for logging
import urllib.request  # Import for downloading data_track_params.ini
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init(autoreset=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Load environment variables from .env file
load_dotenv()

# Print environment variables for debugging
logging.info(Fore.BLUE + f"GCP_BUCKET_NAME: {os.getenv('GCP_BUCKET_NAME')}")
logging.info(Fore.BLUE + f"ASSETTO_CORSA_DIR: {os.getenv('ASSETTO_CORSA_DIR')}")

# Load environment-specific variables
gcp_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
bucket_name = os.getenv("GCP_BUCKET_NAME")
assetto_corsa_dir = os.getenv("ASSETTO_CORSA_DIR")
vm_instance_name = os.getenv("GCP_VM_INSTANCE_NAME")  # VM instance name
vm_zone = os.getenv("GCP_VM_ZONE")  # VM zone
vm_destination_path = "/home/nic/assetto"  # Hardcoded for now
vm_user = os.getenv("GCP_VM_USER")  # VM user

# Verify that all required environment variables are set
if (
    not gcp_credentials_path
    or not bucket_name
    or not assetto_corsa_dir
    or not vm_instance_name
    or not vm_zone
    or not vm_destination_path
    or not vm_user  # Check for VM user
):
    logging.error(
        Fore.RED
        + "Error: Missing required environment variables. Please check your .env file."
    )
    exit(1)

# Set the environment variable for Google Cloud authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcp_credentials_path


def find_gcloud_path():
    """Find the path to the gcloud executable using the 'where' command."""
    try:
        # Use subprocess to execute the 'where' command
        result = subprocess.run(
            ["where", "gcloud"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Decode the output and get all results
        paths = result.stdout.decode().splitlines()

        # Filter to find the correct executable path (gcloud.exe or gcloud.cmd)
        for path in paths:
            if path.endswith("gcloud.exe") or path.endswith("gcloud.cmd"):
                logging.info(Fore.BLUE + f"Found gcloud executable at: {path}")
                return path

        # If no valid executable was found, raise an error
        logging.error(
            Fore.RED
            + "Could not find a valid gcloud executable. Ensure it is installed and in your PATH."
        )
        exit(1)

    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        logging.error(
            Fore.RED
            + f"Could not find gcloud executable. Ensure it is installed and in your PATH. Error: {e}"
        )
        exit(1)


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
        logging.error(Fore.RED + f"Error reading zip file: {e}")
        return [], []


def zip_directory(source_dir, output_filename):
    """Zip the specified directory."""
    try:
        shutil.make_archive(output_filename, "zip", source_dir)
        logging.info(Fore.BLUE + f"Zipped {source_dir} to {output_filename}.zip")
        return f"{output_filename}.zip"
    except Exception as e:
        logging.error(Fore.RED + f"Error zipping directory {source_dir}: {e}")
        return None


def unzip_file(zip_file_path, extract_to):
    """Unzip the file to the specified directory."""
    try:
        with ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)
        logging.info(Fore.BLUE + f"Unzipped {zip_file_path} to {extract_to}.")
    except Exception as e:
        logging.error(Fore.RED + f"Error unzipping file {zip_file_path}: {e}")


def download_file(url, destination_path):
    """Downloads a file from the specified URL to the given destination path."""
    try:
        logging.info(
            Fore.BLUE + f"Downloading file from {url} to {destination_path}..."
        )
        urllib.request.urlretrieve(url, destination_path)
        logging.info(
            Fore.GREEN + f"File downloaded successfully to {destination_path}."
        )
    except Exception as e:
        logging.error(Fore.RED + f"Error downloading file from {url}: {e}")


def update_json_file(json_path, car_files, track_files):
    """Update the content.json file with missing URLs, including URL encoding."""
    try:
        # Check if the JSON file exists and has content
        if os.path.exists(json_path) and os.path.getsize(json_path) > 0:
            with open(json_path, "r") as json_file:
                try:
                    content = json.load(json_file)
                except json.JSONDecodeError:
                    logging.error(
                        Fore.RED
                        + f"Error: {json_path} is not a valid JSON file. Resetting to an empty JSON structure."
                    )
                    content = {"cars": {}, "track": {}}
        else:
            logging.info(
                Fore.BLUE
                + f"{json_path} does not exist or is empty. Initializing a new JSON structure."
            )
            content = {"cars": {}, "track": {}}

        # Ensure the "cars" and "track" keys exist
        if "cars" not in content:
            content["cars"] = {}
        if "track" not in content:
            content["track"] = {}

        # Update cars
        for car in car_files:
            encoded_car_name = urllib.parse.quote(car)  # URL-encode the car name
            if car not in content["cars"] or not content["cars"][car].get("url"):
                content["cars"][car] = {
                    "url": f"https://storage.googleapis.com/{bucket_name}/cars/{encoded_car_name}.zip"
                }

        # Update tracks
        for track in track_files:
            encoded_track_name = urllib.parse.quote(track)  # URL-encode the track name
            if track not in content["track"] or not content["track"].get("url"):
                content["track"][track] = {
                    "url": f"https://storage.googleapis.com/{bucket_name}/tracks/{encoded_track_name}.zip"
                }

        # Save the updated content back to the JSON file
        with open(json_path, "w") as json_file:
            json.dump(content, json_file, indent=2)

        logging.info(Fore.BLUE + f"Updated {json_path} with missing URLs.")

    except Exception as e:
        logging.error(Fore.RED + f"Error updating JSON file {json_path}: {e}")


def print_json_content(file_path):
    """Prints the contents of a JSON file if it exists."""
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as json_file:
                content = json.load(json_file)
                logging.info(
                    Fore.BLUE
                    + f"Contents of {file_path}:\n{json.dumps(content, indent=2)}"
                )
        else:
            logging.info(Fore.BLUE + f"{file_path} does not exist.")
    except Exception as e:
        logging.error(Fore.RED + f"Error reading JSON file {file_path}: {e}")


def append_to_file(file_path, text):
    """Appends the specified text to the end of the given file."""
    try:
        with open(file_path, "a") as file:  # Open file in append mode
            file.write(text)
            logging.info(Fore.GREEN + f"Appended text to {file_path}.")
    except Exception as e:
        logging.error(Fore.RED + f"Error appending to file {file_path}: {e}")


def file_exists_in_gcs(bucket_name, destination_blob_name):
    """Checks if a file already exists in the specified GCS bucket."""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        return blob.exists()
    except Exception as e:
        logging.error(Fore.RED + f"Error checking if file exists in GCS: {e}")
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
        logging.info(
            Fore.BLUE + f"Checking if {destination_blob_name} exists in GCS..."
        )
        if file_exists_in_gcs(bucket_name, destination_blob_name):
            logging.info(
                Fore.BLUE
                + f"File {destination_blob_name} already exists in GCS. Skipping upload."
            )
            return

        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(file_path)
        blob.make_public()
        logging.info(Fore.GREEN + f"File {file_path} uploaded to {blob.public_url}")
    except Exception as e:
        logging.error(Fore.RED + f"Error uploading file {file_path} to GCS: {e}")


def create_remote_directory(vm_instance_name, vm_zone, remote_path):
    """Creates a directory on the remote VM using gcloud compute ssh."""
    try:
        # Dynamically find the gcloud path
        gcloud_path = find_gcloud_path()

        # Ensure the remote path is correctly formatted for Unix
        corrected_remote_path = remote_path.replace("\\", "/")

        # Ensure remote path starts with a Unix root (/)
        if not corrected_remote_path.startswith("/"):
            corrected_remote_path = "/" + corrected_remote_path

        # Construct the SSH command to create the directory
        ssh_command = [
            gcloud_path,
            "compute",
            "ssh",
            vm_instance_name,
            "--zone",
            vm_zone,
            "--command",
            f"mkdir -p '{corrected_remote_path}'",  # Use single quotes to ensure Unix-style path
        ]

        # Execute the command
        logging.info(
            Fore.BLUE
            + f"Creating remote directory {corrected_remote_path} on VM instance..."
        )

        subprocess.run(
            ssh_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        logging.info(
            Fore.GREEN
            + f"Successfully created remote directory {corrected_remote_path} on VM instance."
        )
    except subprocess.CalledProcessError as e:
        logging.error(
            Fore.RED + f"Error creating remote directory on GCP VM: {e.stderr.decode()}"
        )


def upload_to_gcp_vm(local_file_path, destination_path):
    """Uploads the given file or directory to a specified GCP VM instance using gcloud compute scp."""
    try:
        # Dynamically find the gcloud path
        gcloud_path = find_gcloud_path()

        # Convert local file path to Unix style (forward slashes)
        corrected_local_file_path = local_file_path.replace("\\", "/")

        # Use the full destination path from the .env file
        corrected_destination_path = destination_path.replace("\\", "/")

        # Ensure remote path starts with a Unix root (/)
        if not corrected_destination_path.startswith("/"):
            corrected_destination_path = "/" + corrected_destination_path

        # Construct the command to upload the file/directory to the VM instance
        scp_command = [
            gcloud_path,
            "compute",
            "scp",
            "--recurse",  # Add --recurse to copy directories
            corrected_local_file_path,
            f"{vm_user}@{vm_instance_name}:{corrected_destination_path}",  # Use user from env
            "--zone",
            vm_zone,
        ]

        # Log the command for debugging purposes
        logging.info(Fore.BLUE + f"Running command: {' '.join(scp_command)}")

        # Execute the command
        result = subprocess.run(
            scp_command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        logging.info(
            Fore.GREEN
            + f"Successfully uploaded {local_file_path} to GCP VM instance at {destination_path}."
        )
        logging.info(
            Fore.BLUE + result.stdout.decode()
        )  # Print command output for debugging
    except FileNotFoundError as e:
        logging.error(
            Fore.RED
            + f"Error: {e}. Ensure that the gcloud CLI is installed and in your PATH."
        )
        raise
    except subprocess.CalledProcessError as e:
        logging.error(Fore.RED + f"Error uploading file to GCP VM: {e.stderr.decode()}")
        # Provide additional error details if permission is denied
        if "permission denied" in e.stderr.decode().lower():
            logging.error(
                Fore.RED
                + "Permission denied. Check directory ownership and permissions on the remote VM."
            )
        raise


def execute_remote_command(vm_instance_name, vm_zone, remote_command):
    """Executes a command on the remote VM using gcloud compute ssh."""
    try:
        # Dynamically find the gcloud path
        gcloud_path = find_gcloud_path()

        # Construct the SSH command
        ssh_command = [
            gcloud_path,
            "compute",
            "ssh",
            vm_instance_name,
            "--zone",
            vm_zone,
            "--command",
            remote_command,
        ]

        # Execute the command
        logging.info(Fore.BLUE + f"Executing remote command: {' '.join(ssh_command)}")
        result = subprocess.run(
            ssh_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        logging.info(Fore.GREEN + "Remote command executed successfully.")
        logging.info(
            Fore.BLUE + result.stdout.decode()
        )  # Print the output for debugging
    except subprocess.CalledProcessError as e:
        logging.error(Fore.RED + f"Error executing remote command: {e.stderr.decode()}")
        return False
    except Exception as e:
        logging.error(Fore.RED + f"Unexpected error executing remote command: {e}")
        return False
    return True


def stop_service_remote():
    """Stops the Assetto Corsa service on the remote VM."""
    if not execute_remote_command(
        vm_instance_name, vm_zone, "sudo systemctl stop assetto.service"
    ):
        logging.error(
            Fore.RED + "Failed to stop the Assetto Corsa service on the remote server."
        )
        raise RuntimeError("Stopping the service failed.")


def replace_directories_remote():
    """Replaces the 'cfg', 'content', 'system' directories on the remote VM."""
    remote_commands = [
        "sudo rm -rf /opt/ac/cfg /opt/ac/content /opt/ac/system",  # Remove existing directories
        f"sudo mv {vm_destination_path}/cfg /opt/ac/",  # Move the new 'cfg' directory
        f"sudo mv {vm_destination_path}/content /opt/ac/",  # Move the new 'content' directory
        f"sudo mv {vm_destination_path}/system /opt/ac/",  # Move the new 'system' directory
        "sudo chown -R ac:ac /opt/ac/",  # Change ownership
    ]

    for command in remote_commands:
        if not execute_remote_command(vm_instance_name, vm_zone, command):
            logging.error(Fore.RED + f"Failed to execute command: {command}")
            raise RuntimeError("Directory replacement failed.")


def start_service_remote():
    """Starts the Assetto Corsa service on the remote VM and checks if it started successfully."""
    if not execute_remote_command(
        vm_instance_name, vm_zone, "sudo systemctl start assetto.service"
    ):
        logging.error(
            Fore.RED + "Failed to start the Assetto Corsa service on the remote server."
        )
        raise RuntimeError("Starting the service failed.")

    if not check_service_status_remote():
        logging.error(
            Fore.RED
            + "Assetto Corsa service did not start successfully on the remote server."
        )
        raise RuntimeError("Service start failed.")
    else:
        logging.info(
            Fore.GREEN
            + "Assetto Corsa service started successfully on the remote server."
        )


def get_full_service_status_remote():
    """Fetches and displays the full output of the Assetto Corsa service status on the remote VM."""
    try:
        gcloud_path = find_gcloud_path()
        status_command = "sudo systemctl status assetto.service --no-pager"
        ssh_command = [
            gcloud_path,
            "compute",
            "ssh",
            vm_instance_name,
            "--zone",
            vm_zone,
            "--command",
            status_command,
        ]

        logging.info(Fore.BLUE + f"Executing remote command: {' '.join(ssh_command)}")
        result = subprocess.run(
            ssh_command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        status_output = result.stdout.decode()
        logging.info(Fore.BLUE + f"Full service status:\n{status_output}")

    except FileNotFoundError as e:
        logging.error(
            Fore.RED
            + f"Error: {e}. Ensure that the gcloud CLI is installed and in your PATH."
        )
    except subprocess.CalledProcessError as e:
        logging.error(
            Fore.RED + f"Error fetching full service status: {e.stderr.decode()}"
        )
    except Exception as e:
        logging.error(Fore.RED + f"Unexpected error fetching full service status: {e}")


def check_service_status_remote():
    """Checks if the Assetto Corsa service is running or has failed on the remote VM."""
    try:
        active_command = "sudo systemctl is-active assetto.service"
        if not execute_remote_command(vm_instance_name, vm_zone, active_command):
            logging.info(Fore.BLUE + "Assetto Corsa service is not active.")
            failed_command = "sudo systemctl is-failed assetto.service"
            if execute_remote_command(vm_instance_name, vm_zone, failed_command):
                logging.error(Fore.RED + "Assetto Corsa service has failed.")
                get_service_logs_remote()
                return False
            else:
                logging.error(
                    Fore.RED + "Assetto Corsa service is not active and has not failed."
                )
                get_service_logs_remote()
                return False

        logging.info(Fore.GREEN + "Checked service status successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(Fore.RED + f"Error checking service status: {e.stderr.decode()}")
        return False
    except Exception as e:
        logging.error(Fore.RED + f"Unexpected error checking service status: {e}")
        return False


def get_service_logs_remote():
    """Fetches and analyzes the last few lines of the Assetto Corsa service logs on the remote VM."""
    try:
        log_command = "sudo journalctl -u assetto.service -n 20 --no-pager"
        log_output = subprocess.run(
            [
                "gcloud",
                "compute",
                "ssh",
                vm_instance_name,
                "--zone",
                vm_zone,
                "--command",
                log_command,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        logs = log_output.stdout.decode()
        logging.info(Fore.BLUE + f"Service logs:\n{logs}")

        # Analyze the logs for known errors
        if "No track params found" in logs:
            logging.error(
                Fore.RED + "Configuration error detected: Missing track parameters."
            )
        elif "Error executing critical background service" in logs:
            logging.error(Fore.RED + "Service encountered a critical error.")
        else:
            logging.info(Fore.BLUE + "No specific errors detected in the service logs.")
    except subprocess.CalledProcessError as e:
        logging.error(Fore.RED + f"Error fetching service logs: {e.stderr.decode()}")
    except Exception as e:
        logging.error(Fore.RED + f"Unexpected error fetching service logs: {e}")


def main():
    try:
        # Get user input for zip file
        zip_file_path = input("Enter the path to the zip file: ").strip()

        # Verify that the file exists
        if not os.path.exists(zip_file_path):
            logging.error(Fore.RED + f"Error: The file {zip_file_path} does not exist.")
            return

        logging.info(Fore.BLUE + f"Processing zip file: {zip_file_path}")

        # Identify non-base content from the zip file
        car_files, track_files = find_non_base_content(zip_file_path)

        if not car_files and not track_files:
            logging.info(
                Fore.BLUE
                + "No non-base content found in the zip file. Nothing to upload."
            )
            return

        logging.info(
            Fore.BLUE
            + f"Found {len(car_files)} car files and {len(track_files)} track files to upload."
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
                    logging.info(
                        Fore.BLUE
                        + f"Zip file {gcs_path} already exists in GCS. Skipping upload."
                    )
                    continue  # Skip zipping and uploading if file already exists

                # Zip and upload the car directory
                zipped_file = zip_directory(car_dir, zip_filename)
                if zipped_file:
                    upload_file_to_gcs(zipped_file, bucket_name, "cars")
            else:
                logging.info(Fore.BLUE + f"Car directory does not exist: {car_dir}")

        # Process track files
        for track in track_files:
            track_dir = os.path.join(assetto_corsa_dir, "tracks", track)
            if os.path.exists(track_dir):
                zip_filename = os.path.join("uploads", track)

                # Check if the zip file already exists in GCS
                gcs_path = f"tracks/{track}.zip"
                if file_exists_in_gcs(bucket_name, gcs_path):
                    logging.info(
                        Fore.BLUE
                        + f"Zip file {gcs_path} already exists in GCS. Skipping upload."
                    )
                    continue  # Skip zipping and uploading if file already exists

                # Zip and upload the track directory
                zipped_file = zip_directory(track_dir, zip_filename)
                if zipped_file:
                    upload_file_to_gcs(zipped_file, bucket_name, "tracks")
            else:
                logging.info(Fore.BLUE + f"Track directory does not exist: {track_dir}")

        # Unzip the original zip file locally after processing
        unzip_directory = os.path.join("uploads", "unzipped_content")
        os.makedirs(unzip_directory, exist_ok=True)
        unzip_file(zip_file_path, unzip_directory)

        # Download the `data_track_params.ini` file after unzipping
        cfg_dir = os.path.join(unzip_directory, "cfg")
        os.makedirs(cfg_dir, exist_ok=True)  # Ensure the cfg directory exists

        ini_file_url = "https://raw.githubusercontent.com/ac-custom-shaders-patch/acc-extension-config/master/config/data_track_params.ini"
        ini_file_path = os.path.join(cfg_dir, "data_track_params.ini")

        download_file(ini_file_url, ini_file_path)

        # Append the specified text to the `data_track_params.ini` file
        additional_text = """
        [CA-9 Saratoga]
        NAME=CA-9 Saratoga
        LATITUDE=37.26034168298367
        LONGITUDE=-122.03281999062112
        TIMEZONE=America/Los_Angeles
        """
        append_to_file(ini_file_path, additional_text)

        # Update the JSON file with missing URLs
        content_json_path = os.path.join(
            unzip_directory, "cfg", "cm_content", "content.json"
        )
        update_json_file(content_json_path, car_files, track_files)

        # Print the contents of content.json if it exists
        print_json_content(content_json_path)

        # Create the remote directory on the VM if it doesn't exist
        create_remote_directory(vm_instance_name, vm_zone, vm_destination_path)

        # Upload folders to GCP VM
        for folder in ["cfg", "content", "system"]:
            folder_path = os.path.join(unzip_directory, folder)
            if os.path.exists(folder_path):
                upload_to_gcp_vm(folder_path, vm_destination_path)
            else:
                logging.warning(
                    Fore.BLUE + f"Folder {folder} does not exist. Skipping upload."
                )

        # Stop the Assetto Corsa service on the remote server
        stop_service_remote()

        # Replace directories on the remote server
        replace_directories_remote()

        # Start the Assetto Corsa service on the remote server
        start_service_remote()

    except RuntimeError as e:
        logging.error(Fore.RED + f"A runtime error occurred: {e}")
    except Exception as e:
        logging.error(Fore.RED + f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
