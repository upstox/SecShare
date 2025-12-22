import boto3
import json
import logging
from botocore.exceptions import NoCredentialsError, ClientError

# Use standard logging instead of shared logger to avoid circular imports
logger = logging.getLogger(__name__)

class SecretsManager:
    def __init__(self):
        logger.debug('Initializing SecretsManager')
        self.client = boto3.client('secretsmanager', region_name='ap-south-1')  # Change region if needed

    def get_secrets(self, secret_name, region_name=None):
        '''Fetch secrets from AWS Secrets Manager.'''
        logger.debug('Fetching secrets from AWS Secrets Manager')
        try:
            secret_value = self.client.get_secret_value(SecretId=secret_name)
            if 'SecretString' in secret_value:
                return json.loads(secret_value['SecretString'])
            else:
                return secret_value['SecretBinary']
        except (NoCredentialsError, ClientError) as e:
            logger.error(f'Error fetching secret {secret_name}: {e}')
            raise e
