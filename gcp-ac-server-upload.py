import os
import shutil
from zipfile import ZipFile
from google.cloud import storage
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Now, the environment variable GOOGLE_APPLICATION_CREDENTIALS will be available
gcp_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if not gcp_credentials_path:
    print("Error: The GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
    exit(1)

# Set the environment variable for Google Cloud authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcp_credentials_path

# Define base content
BASE_GAME_CARS = {
    "ks_ferrari_250_gto",
    "ks_ferrari_288_gto",
    "ks_ferrari_312_67",
    "ks_ferrari_330_p4",
    "ks_ferrari_812_superfast",
    "ks_ferrari_f2004",
    "ks_ferrari_sf70h",
    "ks_audi_r8_lms_2016",
    "ks_audi_tt_cup",
    "ks_audi_tt_vln",
    "ks_ferrari_fxx_k",
    "ks_lotus_3_eleven",
    "ks_maserati_mc12_gt1",
    "ks_mclaren_570s",
    "ks_mclaren_p1_gtr",
    "ks_porsche_718_boxster_s",
    "ks_porsche_718_boxster_s_pdk",
    "ks_porsche_718_cayman_s",
    "ks_porsche_718_spyder_rs",
    "ks_porsche_908_lh",
    "ks_porsche_911_carrera_rsr",
    "ks_porsche_911_gt1",
    "ks_porsche_911_gt3_cup_2017",
    "ks_porsche_911_gt3_r_2016",
    "ks_porsche_911_gt3_rs",
    "ks_porsche_911_r",
    "ks_porsche_911_rsr_2017",
    "ks_porsche_917_30",
    "ks_porsche_917_k",
    "ks_porsche_918_spyder",
    "ks_porsche_919_hybrid_2015",
    "ks_porsche_919_hybrid_2016",
    "ks_porsche_935_78_moby_dick",
    "ks_porsche_962c_longtail",
    "ks_porsche_962c_shorttail",
    "ks_porsche_991_carrera_s",
    "ks_porsche_991_turbo_s",
    "ks_porsche_cayman_gt4_clubsport",
    "ks_porsche_cayman_gt4_std",
    "ks_praga_r1",
    "ks_toyota_celica_st185",
    "ks_toyota_ts040",
    "ks_abarth500_assetto_corse",
    "ks_ferrari_488_gt3",
    "ks_ferrari_488_gtb",
    "ks_ferrari_f138",
    "ks_ferrari_sf15t",
    "ks_ford_escort_mk1",
    "ks_lamborghini_aventador_sv",
    "ks_lamborghini_countach_s1",
    "ks_lamborghini_gallardo_sl",
    "ks_lamborghini_gallardo_sl_s3",
    "ks_lamborghini_huracan_gt3",
    "ks_lamborghini_huracan_st",
    "ks_lotus_25",
    "ks_lotus_72d",
    "ks_maserati_250f_6cyl",
    "ks_maserati_250f_12cyl",
    "ks_maserati_gt_mc_gt4",
    "ks_mazda_mx5_cup",
    "ks_mazda_mx5_nd",
    "ks_mazda_rx7_spirit_r",
    "ks_mazda_rx7_tuned",
    "ks_mclaren_650_gt3",
    "ks_mercedes_amg_gt3",
    "ks_nissan_370z",
    "ks_nissan_skyline_r34",
    "ks_ruf_rt12r",
    "ks_ruf_rt12r_awd",
    "ks_toyota_ae86",
    "ks_toyota_ae86_drift",
    "ks_toyota_ae86_tuned",
    "ks_toyota_supra_mkiv",
    "ks_toyota_supra_mkiv_drift",
    "ks_toyota_supra_mkiv_tuned",
    "ks_alfa_romeo_4c",
    "ks_alfa_romeo_155_v6",
    "ks_alfa_romeo_gta",
    "ks_audi_r8_lms",
    "ks_bmw_m4",
    "ks_bmw_m4_akrapovic",
    "ks_bmw_m235i_racing",
    "ks_corvette_c7r",
    "ks_ford_gt40",
    "ks_glickenhaus_scg003",
    "ks_lamborghini_countach",
    "ks_mclaren_f1_gtr",
    "ks_mclaren_p1",
    "ks_mercedes_190_evo2",
    "ks_mercedes_c9",
    "ks_nissan_gtr_gt3",
    "lotus_exige_v6_cup",
    "lotus_exos_125",
    "lotus_exos_125_s1",
    "mclaren_mp412c",
    "mclaren_mp412c_gt3",
    "mercedes_sls",
    "mercedes_sls_gt3",
    "p4-5_2011",
    "pagani_huayra",
    "pagani_zonda_r",
    "ruf_yellowbird",
    "shelby_cobra_427sc",
    "tatuusfa1",
    "ks_audi_r8_plus",
    "ks_audi_sport_quattro",
    "ks_audi_sport_quattro_rally",
    "ks_audi_sport_quattro_s1",
    "ks_corvette_c7_stingray",
    "ks_ferrari_488_challenge_evo",
    "ks_ferrari_488_gt3_2020",
    "ks_ford_mustang_2015",
    "ks_lamborghini_huracan_performante",
    "ks_lamborghini_miura_sv",
    "ks_lamborghini_sesto_elemento",
    "ks_maserati_alfieri",
    "ks_maserati_levante",
    "ks_maserati_quattroporte",
    "ks_mazda_787b",
    "ks_mazda_miata",
    "ks_nissan_gtr",
    "ks_pagani_huayra_bc",
    "ks_porsche_cayenne",
    "ks_porsche_macan",
    "ks_porsche_panamera",
    "ks_toyota_gt86",
    "ktm_xbow_r",
    "lotus_2_eleven",
    "lotus_2_eleven_gt4",
    "lotus_49",
    "lotus_98t",
    "lotus_elise_sc",
    "lotus_elise_sc_s1",
    "lotus_elise_sc_s2",
    "lotus_evora_gtc",
    "lotus_evora_gte",
    "lotus_evora_gte_carbon",
    "lotus_evora_gx",
    "lotus_evora_s",
    "lotus_evora_s_s2",
    "lotus_exige_240",
    "lotus_exige_240_s3",
    "lotus_exige_s",
    "lotus_exige_s_roadster",
    "lotus_exige_scura",
    "abarth500",
    "abarth500_s1",
    "alfa_romeo_giulietta_qv",
    "alfa_romeo_giulietta_qv_le",
    "bmw_1m",
    "bmw_1m_s3",
    "bmw_m3_e30",
    "bmw_m3_e30_drift",
    "bmw_m3_e30_dtm",
    "bmw_m3_e30_gra",
    "bmw_m3_e30_s1",
    "bmw_m3_e92",
    "bmw_m3_e92_drift",
    "bmw_m3_e92_s1",
    "bmw_m3_gt2",
    "bmw_z4",
    "bmw_z4_drift",
    "bmw_z4_gt3",
    "bmw_z4_s1",
    "ferrari_312t",
    "ferrari_458",
    "ferrari_458_gt2",
    "ferrari_458_s3",
    "ferrari_599xxevo",
    "ferrari_f40",
    "ferrari_f40_s3",
    "ferrari_laferrari",
    "ks_abarth_595ss",
    "ks_abarth_595ss_s1",
    "ks_abarth_595ss_s2",
    "ks_alfa_33_stradale",
    "ks_alfa_giulia_qv",
    "ks_alfa_mito_qv",
    "ks_audi_a1s1",
}

BASE_GAME_TRACKS = {
    "ks_barcelona",
    "ks_brands_hatch",
    "ks_red_bull_ring",
    "drift",
    "imola",
    "ks_black_cat_county",
    "ks_drag",
    "ks_highlands",
    "ks_laguna_seca",
    "ks_monza66",
    "ks_nurburgring",
    "ks_silverstone",
    "ks_silverstone1967",
    "ks_vallelunga",
    "ks_zandvoort",
    "magione",
    "monza",
    "mugello",
    "spa",
    "trento-bondone",
}


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

    destination_blob_name = os.path.join(destination_path, os.path.basename(file_path))

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

    # Define the local Assetto Corsa directory
    assetto_corsa_dir = (
        r"C:\Program Files (x86)\Steam\steamapps\common\assettocorsa\content"
    )

    # Identify non-base content from the zip file
    car_files, track_files = find_non_base_content(zip_file_path)

    # Process car files
    for car in car_files:
        car_dir = os.path.join(assetto_corsa_dir, "cars", car)
        if os.path.exists(car_dir):
            zip_filename = os.path.join("uploads", car)
            os.makedirs("uploads", exist_ok=True)
            zipped_file = zip_directory(car_dir, zip_filename)
            if zipped_file:
                upload_file_to_gcs(zipped_file, "gcp-6spd-assetto-corsa", "cars")

    # Process track files
    for track in track_files:
        track_dir = os.path.join(assetto_corsa_dir, "tracks", track)
        if os.path.exists(track_dir):
            zip_filename = os.path.join("uploads", track)
            os.makedirs("uploads", exist_ok=True)
            zipped_file = zip_directory(track_dir, zip_filename)
            if zipped_file:
                upload_file_to_gcs(zipped_file, "gcp-6spd-assetto-corsa", "tracks")


if __name__ == "__main__":
    main()
