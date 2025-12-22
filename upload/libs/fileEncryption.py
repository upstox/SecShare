import sys
import os

# Add the parent directory to the Python path to locate 'shared'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import boto3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
from flask import current_app
from shared.utils.logger import logger

class FileEncryption:
    def __init__(self):
        logger.debug('Initializing FileEncryption')
        # Get the KMS client from the app config
        self.kms_client = boto3.client('kms', region_name=current_app.config['aws_region'])

    def generate_data_encryption_key(self, kms_key_id):
        logger.debug('Generating data encryption key')
        # Generate a data encryption key using KMS
        response = self.kms_client.generate_data_key(KeyId=kms_key_id, KeySpec='AES_256')
        return response['Plaintext'], base64.b64encode(response['CiphertextBlob']).decode('utf-8')

    def encrypt_file_content(self, file_content, dek):
        logger.debug('Encrypting file content')
        # Encrypt file content using AES
        cipher = AES.new(dek, AES.MODE_CBC)
        iv = cipher.iv
        encrypted_content = cipher.encrypt(pad(file_content, AES.block_size))
        return iv, encrypted_content