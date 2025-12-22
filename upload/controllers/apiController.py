from flask import redirect, request, session, url_for, flash, g, current_app, jsonify, render_template, Response, stream_with_context
import os, hashlib, time, threading, secrets
from datetime import datetime
from botocore.exceptions import NoCredentialsError, ClientError

from shared.utils.logger import logger
from shared.utils.decorators import login_required, verify_turnstile
from upload.libs.s3Handler import S3Handler
from upload.libs.mailHandler import MailHandler
from upload.libs.fileEncryption import FileEncryption

def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    if not filename:
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@login_required
def approve(unique_id):
    logger.debug('Approve request received for unique_id: %s', unique_id)
    user_download_link = current_app.config['user_download_link']
    session.pop('_flashes', None)  # Clear existing flash messages

    password = request.form.get('password', '').strip()

    try:
        # Get file manager instances from app.config
        db_manager_reader = current_app.config['db_manager_reader']
        db_manager_writer = current_app.config['db_manager_writer']

        # Ensure fresh DB connections before approving
        writer_connection = db_manager_writer.get_db_connection()
        reader_connection = db_manager_reader.get_db_connection()


        if not writer_connection or not reader_connection:
            flash('Database connection error. Please try again later.', 'error')
            return redirect(url_for('appRoute.approvals'))

        # Check if already Approved or Rejected
        with reader_connection.cursor() as reader_cursor:
            current_status = db_manager_reader.get_file_status(unique_id)

        if not current_status:
            flash('No file found with this unique ID.', 'error')
            return redirect(url_for('appRoute.approvals'))
        
        # Before approving, validate if the file is still within its TTL.
        if not db_manager_reader.is_file_valid(unique_id):
            flash('This file has expired and cannot be approved.', 'error')
            return redirect(url_for('appRoute.approvals'))

        if current_status in ['Approved', 'Rejected']:
            flash(f'This file is already {current_status.lower()}. No further action possible.', 'error')
            return redirect(url_for('appRoute.approvals'))

        # Validate manager password
        with reader_connection.cursor() as reader_cursor:
            stored_password_hash = db_manager_reader.get_stored_manager_password(unique_id)

        if not stored_password_hash:
            flash('No stored password found for this file.', 'error')
            return redirect(url_for('appRoute.approvals'))

        def looks_like_sha256_digest(s):
            return len(s) == 64 and all(c in '0123456789abcdefABCDEF' for c in s)

        submitted_hash = password if looks_like_sha256_digest(password) else hashlib.sha256(password.encode()).hexdigest()

        if submitted_hash != stored_password_hash:
            flash('Invalid approval password.', 'error')
            logger.error(f'Password mismatch for unique_id: {unique_id}')
            return redirect(url_for('appRoute.approvals'))

        logger.info(f'Password match successful for unique_id: {unique_id}')

        # Start transaction for updates
        try:
            with writer_connection.cursor() as writer_cursor:
                db_manager_writer.update_file_status(unique_id, 'Approved')
                writer_connection.commit()
        except Exception as e:
            try:
                writer_connection.rollback()
            except Exception:
                pass  # Prevent double error if rollback fails
            raise e

        # Fetch fresh metadata after approval
        with reader_connection.cursor() as reader_cursor:
            file_metadata = db_manager_reader.get_file_name(unique_id)

        if not file_metadata:
            raise Exception(f'Metadata not found for unique_id: {unique_id}')

        # Extract file details
        user_email = file_metadata['uploaded_by']
        filename = file_metadata['file_name']
        ttl = file_metadata['ttl']
        expiry = file_metadata['expiry']
        business_justification = file_metadata.get('business_justification', '')
        recipients = file_metadata.get('recipients', 'Not specified')

        if not user_download_link:
            flash('Error generating download link.', 'error')
            return redirect(url_for('appRoute.approvals'))
        
        # Generate unique user download link
        final_user_download_link = user_download_link.replace('unique_id_placeholder', unique_id)

        # Generate a unique user password
        user_plain_password = secrets.token_urlsafe(16)
        user_password_hash = hashlib.sha256(user_plain_password.encode()).hexdigest()

        # Store the user password hash
        try:
            with writer_connection.cursor() as writer_cursor:
                db_manager_writer.store_user_download_password(unique_id, user_password_hash)
                writer_connection.commit()
        except Exception as e:
            writer_connection.rollback()
            raise e

        mail_handler = MailHandler(
                current_app.config['mail_server'],
                current_app.config['mail_port'],
                current_app.config['smtp_username'],
                current_app.config['smtp_password']
        )

        # Send approval notification to user
        mail_handler.notify_user_on_approval(
            user_email=user_email,
            filename=filename,
            ttl=ttl,
            expiry=expiry,
            business_justification=business_justification,
            recipients=recipients,
            user_download_link=final_user_download_link,
            password=user_plain_password,
        )

        # Notify recipients if specified
        if recipients:
            recipient_emails = [email.strip() for email in recipients.split(',') if email.strip()]
            if recipient_emails:
                mail_handler.send_email_to_recipients(
                    recipients=recipient_emails,
                    download_link=final_user_download_link,
                    password=user_plain_password,
                    filename=filename,
                    user_email=user_email,
                )
                logger.info(f'Notification emails sent to recipients: {recipient_emails}')
            else:
                logger.info('Recipient list was empty after parsing. Skipping recipient notification.')
        else:
            logger.info('No recipients specified for the file. Skipping recipient notification.')

        flash('File approved successfully! Notifications sent.', 'success')

    except Exception as e:
        logger.error(f'Error approving file {unique_id}: {e}')
        flash('An error occurred while approving the file. Please try again.', 'error')
    finally:
        writer_connection.close()
        reader_connection.close()

        return redirect(url_for('appRoute.approvals'))

@login_required
def reject(unique_id):
    logger.debug('Reject request received for unique_id: %s', unique_id)
    session.pop('_flashes', None)  # Clear existing flash messages
    # Get file manager instances from app.config
    db_manager_reader = current_app.config['db_manager_reader']
    db_manager_writer = current_app.config['db_manager_writer']

    '''Handle file rejection.'''
    try:
        # Check if already Approved or Rejected
        current_status = db_manager_reader.get_file_status(unique_id)
        if not current_status:
            flash('No file found with this unique ID.', 'error')
            return redirect(url_for('appRoute.approvals'))
        if current_status in ['Approved', 'Rejected']:
            flash(f'This file is already {current_status.lower()}. No further action possible.', 'error')
            return redirect(url_for('appRoute.approvals'))
        
        password = request.form.get('password', '').strip()
        logger.info(f'Reject requested for unique_id: {unique_id} with password: {password}')
        
        stored_password_hash = db_manager_reader.get_stored_manager_password(unique_id)
        logger.info(f'Stored password hash for {unique_id}: {stored_password_hash}')

        if not stored_password_hash:
            flash('No stored password found for this file.', 'error')
            return redirect(url_for('appRoute.approvals'))
        
        # -------------------------------------------------------------
        # Detect if 'password' is a 64-hex hashed value or plain text
        # -------------------------------------------------------------
        def looks_like_sha256_digest(s):
            return (
                len(s) == 64 and
                all(c in '0123456789abcdefABCDEF' for c in s)
            )
        
        if looks_like_sha256_digest(password):
            logger.info('Detected an already-hashed manager password. Using direct compare.')
            submitted_hash = password
        else:
            logger.info('Detected plaintext manager password. Re-hashing before compare.')
            submitted_hash = hashlib.sha256(password.encode()).hexdigest()
        # -------------------------------------------------------------

        # Compare the final submitted_hash with the stored hash
        if submitted_hash == stored_password_hash:
            logger.info(f'Password match successful for reject: {unique_id}')
            db_manager_writer.update_file_status(unique_id, 'Rejected')

            # Fetch file metadata
            file_metadata = db_manager_reader.get_file_name(unique_id)
            if file_metadata:
                user_email = file_metadata['uploaded_by']
                filename = file_metadata['file_name']
                ttl = file_metadata['ttl']
                expiry = file_metadata['expiry']  # Fetch expiry
                recipients = file_metadata.get('recipients', 'Not specified')  # Add fallback
                business_justification = file_metadata.get('business_justification', 'No justification provided.')

                # Log the justification
                logger.info(f'Business justification received: {business_justification}')

                # Fallback for empty justification
                if not business_justification:
                    business_justification = 'No business justification provided.'

                recipients = file_metadata.get('recipients', 'Not specified')  # Add fallback

                mail_handler = MailHandler(
                    current_app.config['mail_server'],
                    current_app.config['mail_port'],
                    current_app.config['smtp_username'],
                    current_app.config['smtp_password']
                )

                # Notify the user of rejection
                mail_handler.notify_user_on_rejection(
                    user_email=user_email,
                    filename=filename,
                    ttl=ttl,
                    expiry=expiry,
                    business_justification=business_justification,
                    recipients=recipients,
                )

            flash('File rejected successfully!', 'success')
        else:
            logger.error(f'Password mismatch for reject: {unique_id}')
            flash('Invalid rejection password.', 'error')

    except Exception as e:
        logger.error(f'Error rejecting file {unique_id}: {e}')
        flash('An error occurred while rejecting the file.', 'error')

    return redirect(url_for('appRoute.approvals'))

@login_required
@verify_turnstile
def upload():
    logger.debug('Upload request received')
    logger.debug('Incoming request headers: %s', request.headers)
    logger.debug('Incoming cookies: %s', request.cookies)

    # Print all form values for debugging
    logger.debug(f'Request method: {request.method}')
    logger.debug(f'Form data: {dict(request.form)}')
    logger.debug(f'Files data: {dict(request.files)}')
    #########

    session.pop('_flashes', None)  # Clear existing flash messages

    logger.debug('Checking file presence')
    if 'file' not in request.files or request.form.get('ttl') is None:
        flash('No file or TTL provided', 'error')
        logger.info('Missing file or TTL.')
        return redirect(url_for('appRoute.home'))

    file = request.files['file']

    logger.debug('Parsing TTL')
    try:
        ttl = int(request.form.get('ttl'))
    except ValueError:
        flash('Invalid TTL value. Please enter a valid number.', 'error')
        logger.info('Invalid TTL value.')
        return redirect(url_for('appRoute.home'))

    logger.debug('Validating TTL range')
    if not (1 <= ttl <= 7):
        flash('TTL value must be between 1 and 7 days.', 'error')
        logger.info('TTL out of range.')
        return redirect(url_for('appRoute.home'))

    preferred_username = g.user.get('preferred_username')
    logger.debug(f'preferred_username: {preferred_username}')
    
    # Get file manager instances from app.config
    db_manager_reader = current_app.config['db_manager_reader']
    db_manager_writer = current_app.config['db_manager_writer']
    
    manager_email = db_manager_reader.get_manager_email(preferred_username)
    if not manager_email:
        flash('You cannot upload files without an assigned manager in AD. Please contact the IT admin.', 'error')
        logger.warning(f'Upload attempt by {preferred_username} failed due to missing manager email.')
        return redirect(url_for('appRoute.home'))

    # Use the values strictly from config_secshare.yaml
    max_file_size = int(current_app.config['max_file_size'])
    allowed_extensions = set(current_app.config['allowed_extensions'].split(','))

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > max_file_size:
        flash(f'File must be below {max_file_size} bytes.', 'error')
        return redirect(url_for('appRoute.home'))

    if file and allowed_file(file.filename, allowed_extensions):
        # Instead of reading the entire file into memory for hashing,
        # compute a streaming SHA-256 hash.
        hash_obj = hashlib.sha256()
        chunk_size = 100 * 1024 * 1024  # 100MB per chunk
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            hash_obj.update(chunk)
        file_hash = hash_obj.hexdigest()
        
        # Reset file pointer for multipart upload
        file.seek(0)

        # Generate a unique filename by appending unique characters
        base, ext = os.path.splitext(file.filename)
        unique_filename = f'{base}_{secrets.token_hex(4)}{ext}'
        file_key = f'uploads/{unique_filename}'

        # Generate encryption keys 
        dek, encrypted_dek = FileEncryption().generate_data_encryption_key(current_app.config['aws_kms_key_id'])

        ttl_seconds = ttl * 24 * 60 * 60
        expiration_timestamp = int(time.time() + ttl_seconds)
        tags = f'ttl={expiration_timestamp}'
        
        # ------------------- Capture Request Data -------------------
        # Capture form fields before leaving the request context.
        recipients_val = request.form.get('recipients', '').strip()
        business_justification_val = request.form.get('business_justification', '').strip()
        
        # Capture S3 configuration values before leaving the request context
        s3_bucket_name = current_app.config['s3_bucket_name']
        aws_kms_key_id = current_app.config['aws_kms_key_id']
        
        # Capture FileManager instances before leaving the request context
        db_manager_reader_instance = current_app.config['db_manager_reader']
        db_manager_writer_instance = current_app.config['db_manager_writer']
        # ------------------- End Capture -------------------

        # --- Begin Keep-Alive / Background Processing Section ---
        # Create a shared progress dictionary to track processing status.
        progress = {'done': False, 'error': None, 'result': None}

        mail_handler = MailHandler(
                current_app.config['mail_server'],
                current_app.config['mail_port'],
                current_app.config['smtp_username'],
                current_app.config['smtp_password']
        )

        approve_url = current_app.config['approve_url']
        reject_url = current_app.config['reject_url']
        manager_download_url = current_app.config['manager_download_url']

        def heavy_processing(recipients, business_justification, bucket_name, kms_key_id, db_manager_reader, db_manager_writer):
            try:
                # Use multipart upload function for streaming upload and encryption
                # Pass configuration values to avoid Flask context issues in background thread
                s3_handler = S3Handler(
                    bucket_name=bucket_name,
                    kms_key_id=kms_key_id
                )
                s3_handler.multipart_upload_file(file, file_key, dek, encrypted_dek, tags)
            except (NoCredentialsError, ClientError) as e:
                progress['error'] = f'Error during file upload: {str(e)}'
                progress['done'] = True
                return

            # Now generate the unique ID using the streaming hash instead of full file content
            unique_id = db_manager_writer.generate_unique_id(file_hash, ttl, file.filename, preferred_username)
            message = 'File uploaded successfully'

            # Use the captured values instead of accessing request.form again
            if len(business_justification) > 16383:
                progress['error'] = 'Business justification is too long.'
                progress['done'] = True
                return
            
            uploaded_on = datetime.now()
            db_manager_writer.store_file_metadata(
                unique_id, unique_filename, ttl, hashlib.sha256(secrets.token_urlsafe(20).encode()).hexdigest(), 
                recipients, message, uploaded_on, business_justification, uploaded_by=preferred_username
            )
            
            # Fetch metadata from the database with retries
            max_retries = 5
            metadata = None
            for attempt in range(max_retries):
                metadata = db_manager_reader.get_file_name(unique_id)
                if metadata:
                    break
                logger.info(f'Metadata not found on attempt {attempt + 1}. Retrying...')
                time.sleep(1)  # wait 1 second before retrying
            if not metadata:
                progress['error'] = 'An error occurred while retrieving file metadata after multiple retries.'
                progress['done'] = True
                return

            expiry = metadata['expiry']

            # Fetch manager's email
            manager_email = db_manager_reader.get_manager_email(preferred_username)
            logger.debug(f'Fetched manager_email: {manager_email} for user: {preferred_username}')
            if not manager_email:
                progress['error'] = 'Manager email not found. Contact IT administrator.'
                progress['done'] = True
                return

            # Send email to the manager for approval
            approval_password = secrets.token_urlsafe(16)
            approval_password_hash = hashlib.sha256(approval_password.encode()).hexdigest()
            db_manager_writer.store_approval_password(unique_id, approval_password_hash)
            
            mail_handler.send_approval_email(
                manager_email=manager_email,
                ttl=ttl,
                expiry=expiry,
                unique_id=unique_id,
                filename=unique_filename,
                recipients=recipients,
                manager_password=approval_password,
                uploader_email=preferred_username,
                business_justification=business_justification,
                approve_url=approve_url,
                reject_url=reject_url,
                manager_download_url=manager_download_url
            )

            # Notify the user of submission
            mail_handler.notify_user_submission(
                user_email=preferred_username,
                filename=unique_filename,
                expiry=expiry,
                ttl=ttl,
                business_justification=business_justification,
                recipients=recipients,
            )

            progress['result'] = 'File uploaded successfully! Waiting for manager approval.'
            progress['done'] = True

        flash('File uploaded successfully! Waiting for manager approval.', 'success')

        # Start heavy processing in a background thread, passing the captured values.
        processing_thread = threading.Thread(target=heavy_processing, args=(recipients_val, business_justification_val, s3_bucket_name, aws_kms_key_id, db_manager_reader_instance, db_manager_writer_instance))
        processing_thread.start()

        def keep_alive_generator():
            # 1. Start by yielding the initial HTML from template
            initial_html = render_template('processing.html')
            yield initial_html

            # 2. Yield a hidden keep-alive comment every 15 seconds, instead of showing "ping".
            while not progress['done']:
                time.sleep(15)
                yield '<!-- keep alive -->\n'

            # 3. Once done, show either an error or a success message + redirect.
            if progress.get('error'):
                # Processing failed: An error occurred while retrieving file metadata.
                yield f'''
                    <div class="status-message error-message">
                        Processing failed: {progress["error"]}
                    </div>
                '''
            else:
                yield '''
                    <div class="status-message success-message">
                        File processed successfully!
                    </div>
                    <!-- Redirect after 3 seconds -->
                    <script>
                        setTimeout(function() {
                            window.location.href = "/history";
                        }, 300);
                    </script>
                '''
        # And then return the response:
        return Response(stream_with_context(keep_alive_generator()),
                mimetype='text/html')
        # --- End Keep-Alive / Background Processing Section ---

    else:
        flash('File type not allowed', 'error')
        return redirect(url_for('appRoute.home'))

def health_check():
    logger.debug('Health check request received')
    try:
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500