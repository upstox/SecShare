import base64
from Crypto.Cipher import AES
from urllib.parse import quote
from flask import Response
from botocore.exceptions import NoCredentialsError, ClientError

from shared.utils.logger import logger

class FileDecryptor:
    """FileDecryptor class for decrypting and downloading files from S3"""
    
    def __init__(self, s3_client, kms_client, bucket_name):
        """Initialize the FileDecryptor with AWS clients and bucket name"""
        self.s3_client = s3_client
        self.kms_client = kms_client
        self.bucket_name = bucket_name
    
    def decrypt_and_download_file(self, filename, unique_id):
        """Decrypt and download a file from S3"""
        file_key = f"uploads/{filename}"
        
        try:
            logger.debug(f'Starting decryption for unique_id: {unique_id}')
            logger.debug(f'file_key: {file_key}')
            
            # Fetch file details from S3
            s3_object = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
            logger.debug(f'S3 object retrieved successfully')
            
            # Retrieve nonce from metadata
            nonce_hex = s3_object['Metadata'].get('nonce')
            if not nonce_hex:
                logger.error(f'Missing nonce metadata for file: {file_key}')
                raise ValueError('Missing encryption metadata (nonce)')
            
            nonce = bytes.fromhex(nonce_hex)
            logger.debug(f'Nonce retrieved successfully')
            
            # Decrypt DEK using KMS
            encrypted_dek = s3_object['Metadata'].get('x-amz-key')
            if not encrypted_dek:
                logger.error(f'Missing encrypted DEK metadata for file: {file_key}')
                raise ValueError('Missing encryption metadata (DEK)')
                
            decrypted_dek = self.kms_client.decrypt(
                CiphertextBlob=base64.b64decode(encrypted_dek)
            )['Plaintext']
            logger.debug(f'DEK decrypted successfully')
            
            # Initialize the cipher in CTR mode with the retrieved nonce
            cipher = AES.new(decrypted_dek, AES.MODE_CTR, nonce=nonce)
            
            # Create a generator to stream decrypted chunks
            def generate_decrypted():
                for chunk in iter(lambda: s3_object['Body'].read(4096), b''):
                    yield cipher.decrypt(chunk)
            
            logger.debug(f'File decryption successful for unique_id: {unique_id}')
            
            # Create response with proper filename encoding
            filename_encoded = quote(filename, safe='')
            return Response(
                generate_decrypted(),
                mimetype='application/octet-stream',
                headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"}
            )
            
        except (NoCredentialsError, ClientError) as e:
            logger.error(f'AWS error during file processing for unique_id {unique_id}: {e}')
            raise Exception(f"AWS error: {str(e)}")
        except Exception as e:
            logger.error(f'Error during file decryption for unique_id {unique_id}: {e}')
            raise Exception(f"Decryption error: {str(e)}")
    
    def validate_bucket_name(self):
        """
        Validate that the bucket name is properly configured
        
        Returns:
            bool: True if bucket name is valid
            
        Raises:
            ValueError: If bucket name is invalid
        """
        logger.debug(f'Validating bucket name: {self.bucket_name}')
        if not self.bucket_name or not isinstance(self.bucket_name, str):
            logger.error(f'Invalid bucket_name: {self.bucket_name}')
            raise ValueError('Configuration error: Invalid S3 bucket name')
        logger.debug(f'Bucket name validated successfully')
        return True
