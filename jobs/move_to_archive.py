#!/usr/bin/env python3
import os
import boto3
import yaml
import logging
import unicodedata
import sys
import time
import random
from botocore.client import Config
from datetime import datetime
from shared.libs.secretsManager import SecretsManager
from shared.libs.s3_handler import S3Handler
from shared.libs.file_manager import FileManager

# Configure logging: logs to both file and console.
logging.basicConfig(
    level=logging.DEBUG,  # Adjust level as needed.
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_normalize_and_prefix.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION (same as in your upload.py) ---
node_env = os.environ.get('NODE_ENV', '').lower()
logger.info("node_env lala is: %s", node_env)

def load_config_from_s3(config_file="config_secshare.yaml", bucket_name=None):
    if not bucket_name:
        raise ValueError("Bucket name must be provided to load config from S3")
    try:
        s3 = boto3.client('s3', region_name='ap-south-1', config=Config(signature_version='s3v4'))
        response = s3.get_object(Bucket=bucket_name, Key=config_file)
        config_content = response['Body'].read().decode('utf-8')
        return yaml.safe_load(config_content)
    except Exception as e:
        logger.error("Error loading config from S3: %s", e)
        raise

if node_env == 'prod':
    config_bucket = "company-secshare-appsec"
else:
    config_bucket = "company-uat-secshare-appsec"

def get_secrets(secret_name, region_name):
    secretmanager = SecretsManager()
    try:
        return secretmanager.get_secrets(secret_name, region_name)
    except Exception as e:
        logger.error("Error getting secrets: %s", e)
        raise

config = load_config_from_s3("config_secshare.yaml", bucket_name=config_bucket)
env_config = config.get(node_env, {})

secret_name = env_config.get("secrets", {}).get("secret_name")
region_name = env_config.get("secrets", {}).get("region_name")
aws_secrets = get_secrets(secret_name, region_name)
db_writer_password = aws_secrets.get("api.external.db.mysql.writer_password")
db_reader_password = aws_secrets.get("api.external.db.mysql.reader_password")

aws_s3_bucket_name = env_config.get("s3", {}).get("bucket_name")
aws_region = env_config.get("s3", {}).get("region")
aws_kms_key_id = aws_secrets.get("api.external.s3.kms_key_secret")

db_writer_host = env_config.get("db", {}).get("mysql", {}).get("writer_host")
db_reader_host = env_config.get("db", {}).get("mysql", {}).get("reader_host")
db_writer_user = env_config.get("db", {}).get("mysql", {}).get("writer_user")
db_reader_user = env_config.get("db", {}).get("mysql", {}).get("reader_user")
db_name = env_config.get("db", {}).get("mysql", {}).get("database")
db_port = env_config.get("db", {}).get("mysql", {}).get("port")

BUCKET_NAME = aws_s3_bucket_name
AWS_REGION = aws_region
KMS_KEY_ID = aws_kms_key_id

# Initialize S3 and KMS clients.
s3_client = boto3.client('s3', region_name=AWS_REGION, config=Config(signature_version='s3v4'))
kms_client = boto3.client('kms', region_name=AWS_REGION)
s3_handler = S3Handler(BUCKET_NAME)

# Use reader for SELECT operations.
file_manager_writer = FileManager(
    host=db_writer_host,
    user=db_writer_user,
    password=db_writer_password,
    database=db_name,
    port=db_port,
    ssl={"ssl-mode": "DISABLED"}
)

file_manager_reader = FileManager(
    host=db_reader_host,
    user=db_reader_user,
    password=db_reader_password,
    database=db_name,
    port=db_port,
    ssl={"ssl-mode": "DISABLED"}
)

S3_KEY_PREFIX = "uploads/"

# ------------------------------------------------------------------------------
def fetch_s3_keys():
    """List all objects in the S3 bucket under 'uploads/' prefix."""
    s3_keys = []
    try:
        logger.info("🔍 Fetching keys from S3 (Prefix: 'uploads/')...")
        response = s3_client.list_objects_v2(Bucket=aws_s3_bucket_name, Prefix="uploads/")

        if "Contents" in response:
            s3_keys = [obj["Key"] for obj in response["Contents"]]
            logger.info("✅ Found %d keys in S3.", len(s3_keys))
        else:
            logger.warning("⚠ No files found under 'uploads/'.")
    except Exception as e:
        logger.error("Error fetching S3 keys: %s", e)

    return s3_keys

# ------------------------------------------------------------------------------
def find_exact_s3_key(s3_keys, db_key):
    """Compare DB key to S3-stored keys to find an exact match."""
    logger.info("🔍 Searching for a matching key in S3...")

    normalized_db_key = unicodedata.normalize("NFKC", db_key)

    for s3_key in s3_keys:
        normalized_s3_key = unicodedata.normalize("NFKC", s3_key)

        if normalized_db_key == normalized_s3_key:
            logger.info("✅ Exact match found: DB key '%s' matches S3 key '%s'", db_key, s3_key)
            return s3_key

    logger.error("No exact match found for '%s' in S3.", db_key)
    return None

# ------------------------------------------------------------------------------
def get_all_files_from_db():
    """Retrieve all unarchived file names from the database (only those marked 'no')."""
    connection = file_manager_reader.get_db_connection()
    file_list = []

    try:
        with connection.cursor() as cursor:
            query = "SELECT unique_id, file_name FROM file_metadata_archive WHERE deep_archive_status = 'no' ORDER BY expiry DESC"
            cursor.execute(query)
            rows = cursor.fetchall()
            file_list = [{"unique_id": row[0], "file_name": row[1]} for row in rows]
    except Exception as e:
        logger.error("Error fetching file names from DB: %s", e)
    finally:
        connection.close()

    return file_list

# ------------------------------------------------------------------------------
def check_files_in_s3():
    """Check all files from the database against S3."""
    logger.info("🚀 Checking all files in database against S3...")

    db_files = get_all_files_from_db()  # ✅ Now contains [{"unique_id": id, "file_name": name}]
    s3_keys = fetch_s3_keys()

    if not db_files:
        logger.warning("⚠ No files retrieved from the database.")
        return [], []

    matched_files = []
    missing_files = []

    for db_file in db_files:
        unique_id = db_file["unique_id"]  # ✅ Extract unique_id
        file_name = db_file["file_name"]
        full_db_key = f"{S3_KEY_PREFIX}{file_name}"  # ✅ Ensure full key format

        matched_s3_key = find_exact_s3_key(s3_keys, full_db_key)

        if matched_s3_key:
            # ✅ HEAD request to confirm file exists
            try:
                s3_client.head_object(Bucket=aws_s3_bucket_name, Key=matched_s3_key)
                logger.info("✅ HEAD successful for '%s'", matched_s3_key)
                matched_files.append({"unique_id": unique_id, "file_name": matched_s3_key})  # ✅ Use correct format
            except Exception as e:
                logger.error("HEAD failed for '%s' => %s", matched_s3_key, e)
                missing_files.append({"unique_id": unique_id, "file_name": matched_s3_key})  # ✅ Include unique_id
        else:
            missing_files.append({"unique_id": unique_id, "file_name": full_db_key})  # ✅ Include unique_id

    # 📝 Summary Report
    logger.info("🎯 SUMMARY: %d matched, %d missing.", len(matched_files), len(missing_files))
    logger.info("✅ Matched Files:\n%s", "\n".join([f"{x['unique_id']}: {x['file_name']}" for x in matched_files]))
    logger.error("Missing Files:\n%s", "\n".join([f"{x['unique_id']}: {x['file_name']}" for x in missing_files]))

    return matched_files, missing_files  # ✅ Now returns list of dictionaries

def is_already_in_deep_archive(file_key, unique_id):
    """Check if the file is already in Glacier Deep Archive before transitioning."""
    
    # Step 1: Check DB for deep_archive_status
    connection = file_manager_reader.get_db_connection()
    try:
        with connection.cursor() as cursor:
            query = "SELECT deep_archive_status FROM file_metadata_archive WHERE unique_id = %s"
            cursor.execute(query, (unique_id,))
            result = cursor.fetchone()

            if result and result[0] == "yes":
                logger.info("🔍 DB: File '%s' is already in Glacier Deep Archive. Skipping S3 check.", file_key)
                return True  # No need to query S3

    except Exception as e:
        logger.error("❌ Error checking DB for deep_archive_status of '%s': %s", file_key, e)
    finally:
        connection.close()

    # Step 2: Check S3 if not found in DB
    try:
        response = s3_client.head_object(Bucket=BUCKET_NAME, Key=file_key)
        storage_class = response.get("StorageClass", "STANDARD")  # Default to STANDARD if not found

        if storage_class == "DEEP_ARCHIVE":
            logger.info("🔍 S3: File '%s' is already in Glacier Deep Archive. Updating DB...", file_key)
            update_deep_archive_status(unique_id, status="yes") 
            return True

        return False

    except Exception as e:
        logger.error("Failed to check StorageClass for '%s': %s", file_key, e)
        return False

def transition_to_glacier_deep_archive(file_objects):
    """Transitions the given list of S3 files to Glacier Deep Archive if not already archived."""
    if not file_objects:
        logger.warning("⚠ No files to transition.")
        return

    for file_obj in file_objects:
        unique_id = file_obj["unique_id"]
        file_key = file_obj["file_name"]

        if is_already_in_deep_archive(file_key, unique_id):
            continue  # Skip if already archived

        try:
            logger.info("🚀 Transitioning '%s' to Glacier Deep Archive...", file_key)

            # Copy object to Glacier Deep Archive
            s3_client.copy_object(
                Bucket=BUCKET_NAME,
                CopySource={'Bucket': BUCKET_NAME, 'Key': file_key},
                Key=file_key,
                StorageClass='DEEP_ARCHIVE',
                MetadataDirective='COPY'
            )

            logger.info("✅ Successfully transitioned '%s' to Glacier Deep Archive.", file_key)

            # ✅ Update DB status after transition
            update_deep_archive_status(unique_id, status='yes')

        except Exception as e:
            logger.error("❌ Failed to transition '%s': %s", file_key, e)

        time.sleep(1)  # ✅ Prevent rate-limiting issues

# Helper function: Update deep_archive_status in file_metadata_archive (use writer for updates)
def update_deep_archive_status(unique_id, status='yes'):
    connection = file_manager_writer.get_db_connection()  # Use writer for update operations
    try:
        with connection.cursor() as cursor:
            query = "UPDATE file_metadata_archive SET deep_archive_status = %s WHERE unique_id = %s"
            cursor.execute(query, (status, unique_id))
        connection.commit()
        logger.info("✅ Updated deep_archive_status in DB for %s to %s", unique_id, status)
    except Exception as e:
        logger.error("❌ Error updating deep_archive_status in DB for %s: %s", unique_id, e)
    finally:
        connection.close()

# Execute transition after checking files
if __name__ == "__main__":
    matched_files, missing_files = check_files_in_s3()
    transition_to_glacier_deep_archive(matched_files)
    