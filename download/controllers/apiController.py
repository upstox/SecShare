from flask import redirect, request, session, url_for, flash, g, current_app, jsonify, render_template, Response, stream_with_context
import os, hashlib, time, threading, secrets
from datetime import datetime
from botocore.exceptions import NoCredentialsError, ClientError

from shared.utils.logger import logger
from shared.utils.decorators import verify_turnstile
from download.libs.fileDecryptor import FileDecryptor

@verify_turnstile
def verify_password():
    logger.debug('Verify password API endpoint called')
    session.pop('_flashes', None)

    unique_id = request.form['unique_id']
    filename = request.form['filename']
    password = request.form['password']

    db_manager_reader = current_app.config['db_manager_reader']

    metadata = db_manager_reader.get_file_name(unique_id)
    # Check if the metadata exists
    if not metadata:
        logger.error(f'File not found for unique_id: {unique_id}')
        flash('File not found.', 'error')
        return redirect(url_for("appRoute.home"))
    
    # Check if the file is valid (i.e. not expired)
    if not db_manager_reader.is_file_valid(unique_id):
        logger.error(f'File expired for unique_id: {unique_id}')
        flash('This file has expired.', 'error')
        return redirect(url_for("appRoute.home"))
    
    if metadata:
        stored_user_password_hash = metadata['user_password_hash']
        input_password_hash = hashlib.sha256(password.encode()).hexdigest()

        ttl = metadata['ttl']
        filename = metadata['file_name']
        approval_status = metadata.get('status', '').lower()

        # Ensure the file is approved
        if approval_status != "approved":
            flash('This file is pending manager approval. Please try again later.', 'error')
            logger.warning(f'Approval pending for unique_id: {unique_id}. Status: {approval_status}')
            return redirect(url_for('appRoute.download_file', unique_id=unique_id))

        # Verify the password against user_password_hash
        if input_password_hash == stored_user_password_hash:
            logger.debug(f'Password matched for unique_id: {unique_id}')
            try:

                # Get AWS clients from app config
                s3_client = current_app.config['s3_client']
                kms_client = current_app.config['kms_client']
                bucket_name = current_app.config['aws_s3_bucket_name']
                
                # Initialize file decryptor
                file_decryptor = FileDecryptor(s3_client, kms_client, bucket_name)
                
                # Validate bucket name 
                file_decryptor.validate_bucket_name()
                
                # Decrypt and download the file
                return file_decryptor.decrypt_and_download_file(filename, unique_id)
            except (NoCredentialsError, ClientError) as e:
                flash(f'Error: {str(e)}', 'error')
                logger.error(f'Error fetching or decrypting file for unique_id: {unique_id}. Error: {e}')
                return redirect(url_for('appRoute.home'))
        else:
            flash('Invalid password. Please try again.', 'error')
            logger.error(f'Password mismatch for unique_id: {unique_id}')
            return redirect(url_for('appRoute.download_file', unique_id=unique_id))

    flash('File not found.', 'error')
    logger.error(f'File not found for unique_id: {unique_id}')
    return redirect(url_for('appRoute.home'))

def health_check():
    logger.debug('Health check request received')
    try:
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500