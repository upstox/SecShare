from flask import redirect, request, session, url_for, flash, g, current_app, jsonify, render_template, Response
import os, hashlib, time, base64
from urllib.parse import quote
from Crypto.Cipher import AES
from botocore.exceptions import NoCredentialsError, ClientError
import boto3

from shared.utils.logger import logger
from shared.utils.decorators import verify_turnstile
from download.libs.fileDecryptor import FileDecryptor

def favicon():
    logger.debug('Favicon request received')
    return "", 204  # Return empty response with HTTP 204 No Content

def home():
    logger.debug('Home page request received')
    return render_template('download_home.html')

def download_file(unique_id):
    logger.debug(f'Download file request received for unique_id: {unique_id}')
    db_manager_reader = current_app.config['db_manager_reader']
    metadata = db_manager_reader.get_file_name(unique_id)
    if metadata is None:
        flash('File not found or invalid unique ID.', 'error')
        return redirect(url_for('appRoute.home'))

    # Check if the file is valid (i.e. not expired)
    if not db_manager_reader.is_file_valid(unique_id):
        logger.error(f'File expired for unique_id: {unique_id}')
        flash('This file has expired.', 'error')
        return redirect(url_for('appRoute.home'))
    
    filename = metadata['file_name']
    if db_manager_reader.is_file_valid(unique_id):
        return render_template(
            'password_prompt.html', 
            unique_id=unique_id,
            filename=filename,
            turnstile_site_key = current_app.config['turnstile_site_key']
        )
    else:
        flash('The file is either expired or invalid.', 'error')
        return redirect(url_for('appRoute.home'))

@verify_turnstile
def manager_download_file(unique_id):
    logger.debug(f'Manager download file request received for unique_id: {unique_id}')
    # Clear existing flash messages
    session.pop('_flashes', None)

    db_manager_reader = current_app.config['db_manager_reader']
    file_metadata = db_manager_reader.get_file_name(unique_id)

    # Check if the file metadata exists
    if not file_metadata:
        logger.error(f'File not found for unique_id: {unique_id}')
        flash('File not found.', 'error')
        return redirect(url_for('appRoute.home'))
    
    # Check if the file is valid (i.e. not expired)
    if not db_manager_reader.is_file_valid(unique_id):
        logger.error(f'File expired for unique_id: {unique_id}')
        flash('This file has expired.', 'error')
        return redirect(url_for('appRoute.home'))
    
    filename = file_metadata['file_name']

    if request.method == 'POST':
        password = request.form['password']

        # Hash the provided password and compare it with the stored hash
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        stored_password_hash = db_manager_reader.get_stored_manager_password(unique_id)

        if hashed_password == stored_password_hash:
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

            except Exception as e:
                flash(f'Error: {str(e)}', 'error')
                logger.error(f'Error during file processing for unique_id: {unique_id}. Error: {e}')
                return render_template(
                    'manager_password_prompt.html', 
                    unique_id=unique_id,
                    filename=filename,
                    turnstile_site_key = current_app.config['turnstile_site_key']
                )                
        else:
            flash('Invalid password. Please try again.', 'error')
            logger.error(f'Password mismatch for unique_id: {unique_id}')
            return render_template(
                'manager_password_prompt.html', 
                unique_id=unique_id,
                filename=filename,
                turnstile_site_key = current_app.config['turnstile_site_key']
            )

    return render_template(
        'manager_password_prompt.html', 
        unique_id=unique_id,
        filename=filename,
        turnstile_site_key = current_app.config['turnstile_site_key']
    )

def user_download_file(unique_id):
    logger.debug(f'User download file request received for unique_id: {unique_id}')
    # Clear existing flash messages
    session.pop('_flashes', None)

    db_manager_reader = current_app.config['db_manager_reader']

    file_metadata = db_manager_reader.get_file_name(unique_id)

    # Check if the file metadata exists
    if not file_metadata:
        logger.error(f'File not found for unique_id: {unique_id}')
        flash('File not found.', 'error')
        return redirect(url_for('appRoute.home'))
    
    # Check if the file is valid (i.e. not expired)
    if not db_manager_reader.is_file_valid(unique_id):
        logger.error(f'File expired for unique_id: {unique_id}')
        flash('This file has expired.', 'error')
        return redirect(url_for('appRoute.home'))
    
    filename = file_metadata['file_name']
    user_password_hash = file_metadata.get('user_password_hash')
    if request.method == 'POST':
        password = request.form['password']

        # Verify the password against user_password_hash
        if hashlib.sha256(password.encode()).hexdigest() == user_password_hash:
            try:
                s3_client = current_app.config['s3_client']
                kms_client = current_app.config['kms_client']
                bucket_name = current_app.config['aws_s3_bucket_name']
                
                file_decryptor = FileDecryptor(s3_client, kms_client, bucket_name)
                
                # Validate bucket name
                file_decryptor.validate_bucket_name()
                
                # Decrypt and download the file
                return file_decryptor.decrypt_and_download_file(filename, unique_id)
            
            except Exception as e:
                logger.error(f'Error during user file download: {e}')
                flash('An error occurred while processing the file. Please try again.', 'error')
                return redirect(url_for('appRoute.home'))
        else:
            flash('Invalid password. Please try again.', 'error')
            return redirect(url_for('appRoute.user_download_file', unique_id=unique_id))

    return render_template(
        'password_prompt.html', 
        unique_id=unique_id,
        filename=filename,
        turnstile_site_key = current_app.config['turnstile_site_key']
    )

def health_check():
    logger.debug('Health check request received')
    try:
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500