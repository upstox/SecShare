import boto3
import os
import yaml
from botocore.client import Config
from shared.libs.secretsManager import SecretsManager

def load_config():
    # Get environment (uat or prod) from environment variable #
    node_env = os.environ.get('NODE_ENV', '').lower()  # Default to 'uat' if missing
    print('node_env is:', node_env)

    # Dynamically set the base URL depending on the environment
    if node_env == 'prod':
        # Production environment URLs
        base_url = 'https://secshare.company.com'  # External URL for download (public)
        upload_base_url = 'https://secshare.company.app'  # Internal URL for upload (private)
    elif node_env == 'uat':
        # UAT environment URLs
        base_url = 'https://secshare-uat.company.com'  # External URL for download (public)
        upload_base_url = 'https://secshare-file-sharing-tool.uat.company.app'  # Internal URL for upload (private)
    else:
        # Default for local development or other environments
        base_url = 'http://localhost:5001'  # Localhost URL for download (public)
        upload_base_url = 'http://localhost:5000'  # Localhost URL for upload (private)

    # Placeholder URL structure for reject, approve, manager download, and user download
    reject_url = f"{upload_base_url}/api/reject/unique_id_placeholder"  # Upload URL for rejection
    approve_url = f"{upload_base_url}/api/approve/unique_id_placeholder"  # Upload URL for approval
    manager_download_url = f"{base_url}/manager/unique_id_placeholder"  # Download URL for manager
    user_download_link = f"{base_url}/user/unique_id_placeholder"  # Download URL for user

    # Determine config bucket based on environment
    if node_env == 'prod':
        config_bucket = 'company-secshare-appsec'
    else:
        config_bucket = 'company-uat-secshare-appsec'

    s3 = boto3.client('s3', region_name='ap-south-1', config=Config(signature_version='s3v4'))
    response = s3.get_object(Bucket=config_bucket, Key='config_secshare.yaml')
    config = yaml.safe_load(response['Body'].read().decode('utf-8'))
    env_config = config[node_env]

    # S3 
    aws_region = env_config.get('s3', {}).get('region')
    s3_bucket_name = env_config['s3']['bucket_name']

    # Extract secrets info from config (secrets ARN and region)
    secret_name = env_config.get('secrets', {}).get('secret_name')
    region_name = env_config.get('secrets', {}).get('region_name')

    # Fetch secrets (smtp, db password, azure client secret, salt, turnstile) from Secrets Manager
    secrets = SecretsManager().get_secrets(
        env_config['secrets']['secret_name'], 
        env_config['secrets']['region_name']
    )

    db_writer_password = secrets.get('api.external.db.mysql.writer_password')
    db_reader_password = secrets.get('api.external.db.mysql.reader_password')
    azure_client_secret = secrets.get('api.external.azure.client_secret')
    fixed_salt = secrets.get('api.external.salt_secret').strip()
    secret_key = secrets.get('api.external.secret_key').strip()
    smtp_username = secrets.get('api.external.smtp.smtp_username')
    smtp_password = secrets.get('api.external.smtp.smtp_password')
    turnstile_secret = secrets.get('api.external.turnstile_secret')
    aws_kms_key_id = secrets.get('api.external.s3.kms_key_secret')

    # Database 
    db_writer_host = env_config.get('db', {}).get('mysql', {}).get('writer_host')
    db_reader_host = env_config.get('db', {}).get('mysql', {}).get('reader_host')
    db_writer_user = env_config.get('db', {}).get('mysql', {}).get('writer_user')
    db_reader_user = env_config.get('db', {}).get('mysql', {}).get('reader_user')
    db_name = env_config.get('db', {}).get('mysql', {}).get('database')
    db_port = env_config.get('db', {}).get('mysql', {}).get('port')

    # Azure client details (from config_secshare.yaml directly)
    azure_client_id = env_config.get('azure', {}).get('client_id')
    azure_tenant_id = env_config.get('azure', {}).get('tenant_id')

    # Mail details
    mail_port = env_config.get('mail', {}).get('mail_port')
    mail_server = env_config.get('mail', {}).get('mail_server')

    # Turnstile
    turnstile_site_key = env_config.get('turnstile', {}).get('site_key')

    # File
    file_config = env_config.get('file')
    max_file_size = env_config['file']['max_size']
    allowed_extensions = env_config['file']['allowed_extensions']

    # Admin
    admin_access = env_config.get('admin_access', {}).get('users')

    # Return the environment config values
    env_config_values = {
        'node_env': node_env,
        'base_url': base_url,
        'upload_base_url': upload_base_url,
        'reject_url': reject_url,
        'approve_url': approve_url,
        'manager_download_url': manager_download_url,
        'user_download_link': user_download_link,
        'config_bucket': config_bucket,
        'aws_region': aws_region,
        's3_bucket_name': s3_bucket_name,
        'db_writer_password': db_writer_password,
        'db_reader_password': db_reader_password,
        'azure_client_secret': azure_client_secret,
        'fixed_salt': fixed_salt,
        'secret_key': secret_key,
        'smtp_username': smtp_username,
        'smtp_password': smtp_password,
        'turnstile_secret': turnstile_secret,
        'aws_kms_key_id': aws_kms_key_id,
        'db_writer_host': db_writer_host,
        'db_reader_host': db_reader_host,
        'db_writer_user': db_writer_user,
        'db_reader_user': db_reader_user,
        'db_name': db_name,
        'db_port': db_port,
        'azure_client_id': azure_client_id,
        'azure_tenant_id': azure_tenant_id,
        'mail_port': mail_port,
        'mail_server': mail_server,
        'turnstile_site_key': turnstile_site_key,
        'file_config': file_config,
        'max_file_size': max_file_size,
        'allowed_extensions': allowed_extensions,
        'admin_access': admin_access
    }

    return env_config_values
