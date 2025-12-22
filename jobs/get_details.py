import pymysql
import requests
from requests.exceptions import RequestException
import warnings
import logging
import time
import os
import yaml
import boto3
import secrets
from botocore.client import Config
from botocore.exceptions import NoCredentialsError, ClientError

from shared.libs.secretsManager import SecretsManager
from shared.libs.s3_handler import S3Handler
from shared.libs.file_manager import FileManager  # Use the updated FileManager with RDS

# Suppress SSL warnings (not recommended in production)
from requests.packages.urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)

# Get environment
node_env = os.environ.get('NODE_ENV', '').lower()
print("node_env is:", node_env)

# New function to load config_secshare.yaml from S3
def load_config_from_s3(config_file="config_secshare.yaml", bucket_name=None):
    if not bucket_name:
        raise ValueError("Bucket name must be provided to load config from S3")
    try:
        s3 = boto3.client('s3', region_name='ap-south-1', config=Config(signature_version='s3v4'))
        response = s3.get_object(Bucket=bucket_name, Key=config_file)
        config_content = response['Body'].read().decode('utf-8')
        return yaml.safe_load(config_content)
    except Exception as e:
        print(f"Error loading config from S3: {e}")
        raise

# Determine config bucket based on environment
if node_env == 'prod':
    config_bucket = "company-secshare-appsec"
else:
    config_bucket = "company-uat-secshare-appsec"

# Get secrets from AWS Secrets Manager
def get_secrets(secret_name, region_name):
    secretmanager = SecretsManager()
    try:
        secrets = secretmanager.get_secrets(secret_name, region_name)
        return secrets
    except Exception as e:
        print(e)

# Load config_secshare.yaml from S3
config = load_config_from_s3("config_secshare.yaml", bucket_name=config_bucket)
env_config = config.get(node_env, {})

# Extract secrets info from config
secret_name = env_config.get("secrets", {}).get("secret_name")
region_name = env_config.get("secrets", {}).get("region_name")

# Fetch secrets from AWS Secrets Manager
aws_secrets = get_secrets(secret_name, region_name)
db_writer_password = aws_secrets.get("api.external.db.mysql.writer_password")
db_reader_password = aws_secrets.get("api.external.db.mysql.reader_password")
azure_client_details_secret = aws_secrets.get("api.external.azure.client_details_secret")

# AWS config from config_secshare.yaml
aws_s3_bucket_name = env_config.get("s3", {}).get("bucket_name")
aws_region = env_config.get("s3", {}).get("region")
aws_kms_key_id = aws_secrets.get("api.external.s3.kms_key_secret")

# Database connection details from config
db_writer_host = env_config.get("db", {}).get("mysql", {}).get("writer_host")
db_reader_host = env_config.get("db", {}).get("mysql", {}).get("reader_host")
db_writer_user = env_config.get("db", {}).get("mysql", {}).get("writer_user")
db_reader_user = env_config.get("db", {}).get("mysql", {}).get("reader_user")

db_name = env_config.get("db", {}).get("mysql", {}).get("database")
db_port = env_config.get("db", {}).get("mysql", {}).get("port")

# Azure client details (from config_secshare.yaml directly)
azure_client_id = env_config.get("azure_details", {}).get("client_id")
azure_tenant_id = env_config.get("azure", {}).get("tenant_id")

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("employee_manager_details.log"),
        logging.StreamHandler()
    ]
)

BUCKET_NAME = aws_s3_bucket_name
AWS_REGION = aws_region
KMS_KEY_ID = aws_kms_key_id

# Initialize S3 and KMS clients
s3_client = boto3.client('s3', region_name=AWS_REGION, config=Config(signature_version='s3v4'))
kms_client = boto3.client('kms', region_name=AWS_REGION)
s3_handler = S3Handler(BUCKET_NAME)

# Initialize FileManager for writer (for updates)
file_manager_writer = FileManager(
    host=db_writer_host,
    user=db_writer_user,
    password=db_reader_password,
    database=db_name,
    port=db_port,
    ssl={"ssl-mode": "DISABLED"}
)

# OPTIONAL: Create a dictionary of DB config parameters (for use with pymysql)
db_config = {
    "host": db_writer_host,
    "user": db_writer_user,
    "password": db_writer_password,
    "database": db_name,
    "port": db_port,
    "ssl": {"ssl-mode": "DISABLED"}
}

# Azure AD B2C setup
CLIENT_ID = azure_client_id
TENANT_ID = azure_tenant_id
CLIENT_SECRET = azure_client_details_secret

def get_access_token():
    """Fetch access token from Azure AD."""
    logging.info("Fetching access token from Azure AD...")
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': 'https://graph.microsoft.com/.default',
        'grant_type': 'client_credentials'
    }
    
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        token_data = response.json()
        logging.info("Successfully fetched access token.")
        return token_data.get('access_token')
    except RequestException as e:
        logging.error(f"Error fetching access token: {e}")
        return None

def fetch_all_users(access_token):
    """Fetch all users in the organization from Microsoft Graph."""
    logging.info("Fetching all users from Azure AD...")
    headers_graph = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    url = "https://graph.microsoft.com/v1.0/users"
    users = []
    
    try:
        while url:
            response = requests.get(url, headers=headers_graph, verify=False)
            response.raise_for_status()
            data = response.json()
            users.extend(data.get('value', []))
            logging.info(f"Fetched {len(users)} users so far...")
            url = data.get('@odata.nextLink')  # Follow pagination if available
        logging.info(f"Successfully fetched a total of {len(users)} users.")
    except RequestException as e:
        logging.error(f"Error fetching users: {e}")
        return []
    
    # Filter out users without valid email addresses
    valid_users = [user for user in users if user.get('mail') and '@' in user.get('mail')]
    logging.info(f"Filtered valid users: {len(valid_users)} out of {len(users)} total.")
    return valid_users

def fetch_user_details(user_email, access_token):
    """
    Fetch department and manager details for a user from Microsoft Graph.
    """
    headers_graph = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    user_url = f"https://graph.microsoft.com/v1.0/users/{user_email}?$select=department,displayName,mail,jobTitle"
    manager_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/manager"

    try:
        user_response = requests.get(user_url, headers=headers_graph, verify=False)
        user_response.raise_for_status()
        user_data = user_response.json()

        employee_name = user_data.get("displayName", "Not Found")
        employee_email = user_data.get("mail", "Not Found")
        employee_designation = user_data.get("jobTitle", "Not Found")
        department = user_data.get("department", "Not Found")

        manager_response = requests.get(manager_url, headers=headers_graph, verify=False)
        if manager_response.status_code == 404:
            manager_name = "Not Found"
            manager_email = "Not Found"
            manager_designation = "Not Found"
        else:
            manager_response.raise_for_status()
            manager_data = manager_response.json()
            manager_name = manager_data.get("displayName", "Not Found")
            manager_email = manager_data.get("mail", "Not Found")
            manager_designation = manager_data.get("jobTitle", "Not Found")

        return {
            "employee_name": employee_name,
            "employee_email": employee_email,
            "employee_designation": employee_designation,
            "department": department,
            "manager_name": manager_name,
            "manager_email": manager_email,
            "manager_designation": manager_designation,
        }
    except RequestException as e:
        logging.error(f"Error fetching details for {user_email}: {e}")
        return {
            "employee_name": "Not Found",
            "employee_email": user_email,
            "employee_designation": "Not Found",
            "department": "Not Found",
            "manager_name": "Not Found",
            "manager_email": "Not Found",
            "manager_designation": "Not Found",
        }

def sanitize_record(record):
    """Ensure all fields are sanitized to avoid NULL values in the database."""
    return {key: (value if value is not None else "Not Found") for key, value in record.items()}

def insert_or_update_database(data, db_config):
    """Insert or update the employee and manager details in the database."""
    logging.info("Inserting/updating records in the database...")
    connection = pymysql.connect(**db_config)
    cursor = connection.cursor()
    
    for idx, record in enumerate(data, start=1):
        logging.info(f"Inserting/updating record {idx}/{len(data)} for email: {record['employee_email']}")
        sanitized_record = sanitize_record(record)
        insert_query = """
        INSERT INTO employee_manager_details (
            employee_name, employee_email, employee_designation, 
            department, manager_name, manager_email, manager_designation
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            employee_name = VALUES(employee_name),
            employee_designation = VALUES(employee_designation),
            department = VALUES(department),
            manager_name = VALUES(manager_name),
            manager_email = VALUES(manager_email),
            manager_designation = VALUES(manager_designation);
        """
        cursor.execute(insert_query, (
            sanitized_record['employee_name'],
            sanitized_record['employee_email'],
            sanitized_record['employee_designation'],
            sanitized_record['department'],
            sanitized_record['manager_name'],
            sanitized_record['manager_email'],
            sanitized_record['manager_designation'],
        ))
    
    connection.commit()
    cursor.close()
    connection.close()
    logging.info("Database update complete.")

if __name__ == "__main__":
    access_token = get_access_token()
    
    if access_token:
        # Process all users
        all_users = fetch_all_users(access_token)
        all_details = []

        for user in all_users:
            user_email = user.get('mail', 'Not Found')
            if user_email == "Not Found":
                logging.warning(f"Skipping user with missing email: {user}")
                continue  # Skip invalid user
            user_details = fetch_user_details(user_email, access_token)
            all_details.append(user_details)

        if all_details:
            # Pass the proper db_config dictionary instead of file_manager_writer
            insert_or_update_database(all_details, db_config)
            logging.info("Successfully processed all valid users.")
        else:
            logging.warning("No valid user details found.")
    else:
        logging.error("Failed to fetch access token.")

# Main function for single user testing
# if __name__ == "__main__":
#     access_token = get_access_token()
    
#     if access_token:
#         test_email = "yogendra.srivastava@rksv.in"
#         user_details = fetch_user_details(test_email, access_token)
#         logging.info(f"Fetched details for {test_email}: {user_details}")
#         insert_or_update_database([user_details], DB_CONFIG)
#     else:
#         logging.error("Failed to fetch access token.")
