import sys
import os

# Add the parent directory to the Python path to locate 'shared'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from shared.utils.logger import logger

class S3Handler:
    def __init__(self, bucket_name=None, kms_key_id=None):
        logger.debug('Initializing S3Handler')
        self.s3_client = boto3.client('s3')
        self.bucket_name = bucket_name
        self.kms_key_id = kms_key_id

    def multipart_upload_file(self, file_obj, file_key, dek, encrypted_dek, tags, part_size=5 * 1024 * 1024):
        '''
        Uploads a file to S3 using multipart upload with streaming encryption (AES in CTR mode).
        '''
        logger.debug('Uploading file to S3')
        # Generate a random nonce (8 bytes recommended for CTR mode)
        nonce = get_random_bytes(8)
        # Initialize the cipher in CTR mode
        cipher = AES.new(dek, AES.MODE_CTR, nonce=nonce)
        
        # Initiate the multipart upload, including nonce in metadata for later decryption
        mpu = self.s3_client.create_multipart_upload(
            Bucket=self.bucket_name,
            Key=file_key,
            ServerSideEncryption='aws:kms',
            SSEKMSKeyId=self.kms_key_id,
            Metadata={'x-amz-key': encrypted_dek, 'nonce': nonce.hex()},
            Tagging=tags
        )
        upload_id = mpu['UploadId']
        parts = []
        part_number = 1

        # Log the start time of the upload
        start_time = datetime.now()
        logger.debug(f"Multipart upload started at {start_time} for file: {file_key}")

        try:
            while True:
                chunk = file_obj.read(part_size)
                if not chunk:
                    break
                # Encrypt the chunk using AES-CTR.
                encrypted_chunk = cipher.encrypt(chunk)
                response = self.s3_client.upload_part(
                    Bucket=self.bucket_name,
                    Key=file_key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=encrypted_chunk
                )
                parts.append({'ETag': response['ETag'], 'PartNumber': part_number})
                part_number += 1

            # Complete the multipart upload
            self.s3_client.complete_multipart_upload(
                Bucket=self.bucket_name,
                Key=file_key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )

            # Record the end time and compute duration
            end_time = datetime.now()
            duration = end_time - start_time
            logger.debug(f'Multipart upload for file {file_key} started at {start_time}, finished at {end_time}, duration: {duration}')

        except Exception as e:
            self.s3_client.abort_multipart_upload(Bucket=self.bucket_name, Key=file_key, UploadId=upload_id)
            logger.error(f'Multipart upload aborted for file: {file_key}. Error: {e}')
            raise e