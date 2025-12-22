import sys
import os

# Add the parent directory to the Python path to locate 'shared'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from shared.utils.logger import logger
#

class MailHandler:
    def __init__(self, mail_server, mail_port, smtp_username, smtp_password):
        logger.debug('Initializing MailHandler')
        self.server = mail_server
        self.port = mail_port
        self.username = smtp_username
        self.password = smtp_password

    def send_email(self, _sender, _recipients, _cc, _subject, _message):
        '''Send an email using the configured SMTP server.'''
        try:
            # Set up the server and login
            logger.debug('Sending email')
            with smtplib.SMTP_SSL(self.server, self.port) as server:
                server.login(self.username, self.password)
                
                for recipient in _recipients:
                    logger.debug('Sending email to %s', recipient)
                    message = MIMEMultipart("alternative")
                    message['From'] = _sender
                    message['To'] = recipient
                    message['Subject'] = _subject

                    # Send email
                    server.sendmail(_sender, recipient, _message.as_string())
                    logger.debug('Email sent to %s', recipient)
        except Exception as e:
            print(f'Error sending email: {e}')
            raise e

    def send_email_to_recipients(self, recipients=None, download_link=None, password=None, filename=None, user_email=None):
        '''
        Sends an email to multiple recipients with the download link and password.
        
        Args:
            recipients (list): List of recipient email addresses.
            download_link (str): The link to download the file.
            password (str): The password for accessing the file.
            filename (str): The name of the file.
        '''
        if not recipients:
            logger.warning('No recipients provided for email.')
            return  # Exit early if no recipients are provided

        subject = f'SecShare - {filename} shared by {user_email}'
        message_body = f'''
        <html>
            <body style="font-family: Arial, sans-serif; color: #fff; padding: 20px;">
                <div style="max-width: 600px; margin: auto; padding: 40px; border-radius: 20px; background-color: #1e1e1e; box-shadow: 0px 15px 40px rgba(0, 0, 0, 0.6); text-align: center;">
                    <h2 style="color: #50c7f9; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 10px rgba(80, 199, 249, 0.8);">
                        Secure File Access
                    </h2>
                    <p style="font-size: 16px; color: #ddd; margin-top: 20px;">
                        The file <strong style="color: #50c7f9;">{filename}</strong> shared by <a href="mailto:{recipients}" style="color: #50c7f9; text-decoration: none;">{user_email}</a> is ready for download:
                    </p>
                    <div style="margin: 20px 0;">
                        <a href="{download_link}" style="font-size: 18px; color: #fff; background-color: #50c7f9; padding: 12px 24px; border-radius: 6px; text-decoration: none; display: inline-block; box-shadow: 0 5px 10px rgba(80, 199, 249, 0.5);">
                            Download File
                        </a>
                    </div>
                    <p style="font-size: 16px; color: #ddd;">
                        Use this password to access the file: 
                        <strong style="color: #50c7f9;">{password}</strong>
                    </p>
                </div>
            </body>
        </html>
        '''
        for email in recipients:
            logger.debug('Sending email to %s', email)
            message = MIMEMultipart("alternative")
            message['Subject'] = subject
            message['From'] = 'SecShare <secshare@company.com>'
            message['To'] = email
            message.attach(MIMEText(message_body, "html"))

            try:
                output = self.send_email(
                    _sender='secshare@company.com',
                    _recipients=[email],
                    _cc=[],  # Add CC if needed
                    _subject=subject,
                    _message=message
                )
                logger.info(f'Email sent successfully to {email}.')
            except Exception as e:
                logger.error(f'Error sending email to {email}: {e}')

    def send_approval_email(self, manager_email, unique_id, ttl, expiry, recipients, business_justification, manager_password, uploader_email, filename, approve_url, reject_url, manager_download_url):
        '''
        Sends an email to the manager requesting approval for the uploaded file.

        Args:
            manager_email (str): Manager's email address.
            unique_id (str): Unique identifier for the file.
            ttl (int): Time-to-live for the file (in days).
            recipients (str): Recipients the employee wants to send the file to.
            business_justification (str): Business justification provided by the uploader.
            manager_password (str): Unique password for the manager.
            uploader_email (str): Email of the uploader.
        '''
        logger.info('Preparing to send approval email...')

        # Generate approval and rejection links
        final_approve_url = approve_url.replace('unique_id_placeholder', unique_id)
        final_reject_url = reject_url.replace('unique_id_placeholder', unique_id)
        final_manager_download_url = manager_download_url.replace('unique_id_placeholder', unique_id)

        subject = 'SecShare - Approval Request for Uploaded File'
        message_body = f'''
        <html>
            <body style="
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #1f1c2c, #302b63, #0f0c29) !important;
                color: #fff !important;
                padding: 30px;
                text-align: center;
                border-radius: 20px;
                box-shadow: 0 15px 40px rgba(0, 0, 0, 0.7);
                max-width: 600px;
                margin: auto;
            ">
                <h2 style="
                    color: #50c7f9 !important;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                    text-shadow: 0 0 10px rgba(80, 199, 249, 0.8);
                    margin-bottom: 20px;
                ">
                    Approval Request
                </h2>
                <p style="font-size: 16px; margin: 20px 0; color: #ddd !important;">
                    The following file has been uploaded by 
                    <strong>
                        <a href="mailto:{uploader_email}" style="color: #50c7f9 !important; text-decoration: none !important;">
                            {uploader_email}
                        </a>
                    </strong>
                    and requires your review:
                </p>

                <div style="
                    background-color: #2c2c2c !important;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px auto;
                    color: #fff !important;
                    text-align: left !important;
                ">
                    <p>
                        <strong style="color: #ffffff !important;">Filename:</strong>
                        <span style="color: #ffffff !important;">{filename}</span>
                    </p>
                    <p>
                        <strong style="color: #ffffff !important;">Expiry:</strong>
                        <span style="color: #ffffff !important;">{expiry}</span>
                    </p>
                    <p>
                        <strong style="color: #ffffff !important;">TTL:</strong>
                        <span style="color: #ffffff !important;">{ttl} days</span>
                    </p>
                    <p>
                        <strong style="color: #ffffff !important;">Recipients:</strong>
                        <a href="mailto:{recipients}" style="color: #ffffff !important; text-decoration: none !important;">
                            {recipients}
                        </a>
                    </p>
                    <p>
                        <strong style="color: #ffffff !important;">Business Justification:</strong>
                        <span style="color: #ffffff !important;">{business_justification}</span>
                    </p>
                    <p style="color: #aaa !important; font-size: 12px;">
                        🔗 <strong>Download Link:</strong>
                        <a href="{final_manager_download_url}" style="color: #50c7f9 !important; text-decoration: none !important;">
                            {final_manager_download_url}
                        </a>
                    </p>
                    <p>
                        <strong>Password:</strong>
                        <span style="color: #50c7f9 !important; font-weight: bold !important;">
                            {manager_password}
                        </span>
                    </p>
                </div>

                <div style="margin: 20px 0;">
                    <form action="{final_approve_url}" method="POST" style="display:inline;">
                        <input type="hidden" name="password" value="{manager_password}">
                        <button type="submit" style="
                            padding: 14px 28px;
                            background: #28a745 !important;
                            color: white !important;
                            border: none !important;
                            border-radius: 12px;
                            font-weight: bold;
                            font-size: 16px;
                            cursor: pointer;
                        ">
                            Approve
                        </button>
                    </form>
                    <form action="{final_reject_url}" method="POST" style="display:inline;">
                        <input type="hidden" name="password" value="{manager_password}">
                        <button type="submit" style="
                            padding: 14px 28px;
                            background: #dc3545 !important;
                            color: white !important;
                            border: none !important;
                            border-radius: 12px;
                            font-weight: bold;
                            font-size: 16px;
                            cursor: pointer;
                        ">
                            Reject
                        </button>
                    </form>
                </div>

                <footer style="margin-top: 20px; font-size: 12px; color: #aaa !important;">
                    ⚠️ Please ensure to review the file responsibly.
                </footer>
            </body>
        </html>
        '''

        message = MIMEMultipart("alternative")
        message['Subject'] = subject
        message['From'] = 'SecShare <secshare@company.com>'
        message['To'] = manager_email
        message.attach(MIMEText(message_body, "html"))

        try:
            logger.debug('Attempting to send approval email...')
            self.send_email(
                _sender='secshare@company.com',
                _recipients=[manager_email],
                _cc=[],
                _subject=subject,
                _message=message
            )
            logger.debug('Approval email sent successfully.')
        except Exception as e:
            logger.error(f"Error sending approval email to {manager_email}: {e}")
            raise

    def notify_user_submission(self, user_email, filename, expiry, ttl, business_justification, recipients):
        '''
        Notify the user about the submission of their file for approval.
        Args:
            user_email (str): Uploader's email.
            filename (str): Name of the uploaded file.
            ttl (int): Time-to-live for the file.
            business_justification (str): Business justification provided by the uploader.
            recipients (str): Recipients entered by the uploader.
        '''
        subject = 'SecShare - Your File Has Been Sent for Approval'
        body = f'''
        <html>
            <body style="
                font-family: Arial, sans-serif !important;
                background: linear-gradient(135deg, #1f1c2c, #302b63, #0f0c29) !important;
                color: #fff !important;
                padding: 30px !important;
                text-align: center !important;
                border-radius: 20px !important;
                box-shadow: 0 15px 40px rgba(0, 0, 0, 0.7) !important;
                max-width: 600px !important;
                margin: auto !important;
            ">
                <h2 style="
                    color: #50c7f9 !important;
                    text-transform: uppercase !important;
                    letter-spacing: 2px !important;
                    text-shadow: 0 0 10px rgba(80, 199, 249, 0.8) !important;
                    margin-bottom: 20px !important;
                ">
                    File Submission Notification
                </h2>
                <p style="
                    font-size: 16px !important;
                    margin: 20px 0 !important;
                    color: #fff !important;
                ">
                    Your file has been sent to your manager for approval.
                </p>
                
                <div style="
                    background-color: #2c2c2c !important;
                    padding: 20px !important;
                    border-radius: 10px !important;
                    margin: 20px auto !important;
                    color: #fff !important;
                    text-align: left !important;
                ">
                    <p>
                        <strong style="color: #ffffff !important;">Filename:</strong>
                        <span style="color: #ffffff !important;">{filename}</span>
                    </p>
                    <p>
                        <strong style="color: #ffffff !important;">Expiry:</strong>
                        <span style="color: #ffffff !important;">{expiry}</span>
                    </p>
                    <p>
                        <strong style="color: #ffffff !important;">TTL:</strong>
                        <span style="color: #ffffff !important;">{ttl} days</span>
                    </p>
                    <p>
                        <strong style="color: #ffffff !important;">Recipients:</strong>
                        <a href="mailto:{recipients}" style="color: #ffffff !important; text-decoration: none !important;">
                            {recipients}
                        </a>
                    </p>
                    <p>
                        <strong style="color: #ffffff !important;">Business Justification:</strong>
                        <span style="color: #ffffff !important;">{business_justification}</span>
                    </p>
                </div>

                <p style="
                    font-size: 14px !important;
                    margin: 20px 0 !important;
                    color: #fff !important;
                ">
                    You'll be notified once your manager approves or rejects the file.
                </p>
                
                <footer style="
                    margin-top: 20px !important;
                    font-size: 12px !important;
                    color: #aaa !important;
                ">
                    Thank you for using our file-sharing tool!
                </footer>
            </body>
        </html>
        '''
        message = MIMEMultipart("alternative")
        message['Subject'] = subject
        message['From'] = 'SecShare <secshare@company.com>'
        message['To'] = user_email
        message.attach(MIMEText(body, "html"))

        try:
            self.send_email(
                _sender='secshare@company.com',
                _recipients=[user_email],
                _cc=[],
                _subject=subject,
                _message=message
            )
            logger.debug(f'Notification email sent to user: {user_email}')
        except Exception as e:
            logger.error(f"Error sending notification email to user {user_email}: {e}")

    def notify_user_on_approval(self, user_email, filename, expiry, ttl, business_justification, recipients, user_download_link, password):
        '''
        Notify the user when their file is approved by the manager.
        Args:
            user_email (str): Uploader's email.
            filename (str): Name of the uploaded file.
            expiry (datetime): Expiration date of the file.
            ttl (int): Time-to-live for the file.
            business_justification (str): Business justification provided by the uploader.
            recipients (str): Recipients entered by the uploader.
            user_download_link (str): Download link for the user.
            password (str): Password for the file.
        '''
        subject = 'SecShare - Your File Has Been Approved'
        body = f'''
        <html>
            <body style="font-family: Arial, sans-serif !important; background: linear-gradient(135deg, #1f1c2c, #302b63, #0f0c29) !important; color: #fff !important; padding: 30px !important; text-align: center !important; border-radius: 20px !important; box-shadow: 0 15px 40px rgba(0, 0, 0, 0.7) !important; max-width: 600px !important; margin: auto !important;">
                <h2 style="color: #50c7f9 !important; text-transform: uppercase !important; letter-spacing: 2px !important; text-shadow: 0 0 10px rgba(80, 199, 249, 0.8) !important; margin-bottom: 20px !important;">
                    File Approval Notification
                </h2>
                <p style="font-size: 16px !important; margin: 20px 0 !important; color: #fff !important;">
                    Your file has been approved by your manager.
                </p>
                
                <div style="background-color: #2c2c2c !important; padding: 20px !important; border-radius: 10px !important; margin: 20px auto !important; color: #fff !important; text-align: left !important;">
                    <p><strong style="color: #ffffff !important;">Filename:</strong> <span style="color: #ffffff !important;">{filename}</span></p>
                    <p><strong style="color: #ffffff !important;">Expiry:</strong> <span style="color: #ffffff !important;">{expiry}</span></p>
                    <p><strong style="color: #ffffff !important;">TTL:</strong> <span style="color: #ffffff !important;">{ttl} days</span></p>
                    <p><strong style="color: #ffffff !important;">Recipients:</strong> <a href="mailto:{recipients}" style="color: #ffffff !important; text-decoration: none !important;">{recipients}</a></p>
                    <p><strong style="color: #ffffff !important;">Business Justification:</strong> <span style="color: #ffffff !important;">{business_justification}</span></p>
                    <p><strong>Your download link:</strong> <a href="{user_download_link}" style="color: #50c7f9 !important; text-decoration: none !important;">{user_download_link}</a></p>
                    <p><strong>Password:</strong> <span style="color: #50c7f9 !important;">{password}</span></p>
                </div>
                
                <footer style="margin-top: 20px !important; font-size: 12px !important; color: #aaa !important;">
                    Thank you for using our file-sharing tool!
                </footer>
            </body>
        </html>
        '''
        message = MIMEMultipart("alternative")
        message['Subject'] = subject
        message['From'] = 'SecShare <secshare@company.com>'
        message['To'] = user_email
        message.attach(MIMEText(body, "html"))

        try:
            self.send_email(
                _sender='secshare@company.com',
                _recipients=[user_email],
                _cc=[],
                _subject=subject,
                _message=message
            )
            logger.debug(f'Approval notification sent to user: {user_email}')
        except Exception as e:
            logger.error(f"Error sending approval notification email to user {user_email}: {e}")

    def notify_user_on_rejection(self, user_email, filename, expiry, ttl, business_justification, recipients):
        '''
        Notify the user via email when their file is rejected.

        Args:
            user_email (str): The user's email address.
            filename (str): The name of the file.
            expiry (datetime): Expiration date of the file.
            ttl (int): The time-to-live for the file.
            business_justification (str): Business justification provided by the uploader.
            recipients (str): Recipients the uploader entered.
        '''
        subject = 'SecShare - Your File Upload Has Been Rejected'
        body = f'''
        <html>
            <body style="font-family: Arial, sans-serif !important; background: linear-gradient(135deg, #1f1c2c, #302b63, #0f0c29) !important; color: #fff !important; padding: 30px !important; text-align: center !important; border-radius: 20px !important; box-shadow: 0 15px 40px rgba(0, 0, 0, 0.7) !important; max-width: 600px !important; margin: auto !important;">
                <h2 style="color: #ff6f61 !important; text-transform: uppercase !important; letter-spacing: 2px !important; text-shadow: 0 0 10px rgba(255, 111, 97, 0.8) !important; margin-bottom: 20px !important;">File Rejected</h2>
                <p style="font-size: 16px !important; margin: 20px 0 !important; color: #fff !important;">
                    Unfortunately, your uploaded file has been rejected by the manager.
                </p>
                
                <div style="background-color: #2c2c2c !important; padding: 20px !important; border-radius: 10px !important; margin: 20px auto !important; color: #fff !important; text-align: left !important;">
                    <p><strong style="color: #ffffff !important;">Filename:</strong> <span style="color: #ffffff !important;">{filename}</span></p>
                    <p><strong style="color: #ffffff !important;">Expiry:</strong> <span style="color: #ffffff !important;">{expiry}</span></p>
                    <p><strong style="color: #ffffff !important;">TTL:</strong> <span style="color: #ffffff !important;">{ttl} days</span></p>
                    <p><strong style="color: #ffffff !important;">Recipients:</strong> <a href="mailto:{recipients}" style="color: #ffffff !important; text-decoration: none !important;">{recipients}</a></p>
                    <p><strong style="color: #ffffff !important;">Business Justification:</strong> <span style="color: #ffffff !important;">{business_justification}</span></p>
                </div>

                <p style="font-size: 14px !important; margin: 20px 0 !important; color: #fff !important;">
                    ⚠️ Please contact your manager for more details.
                </p>
                
                <footer style="margin-top: 20px !important; font-size: 12px !important; color: #aaa !important;">
                    Thank you for using the file-sharing tool.
                </footer>
            </body>
        </html>
        '''

        message = MIMEMultipart("alternative")
        message['Subject'] = subject
        message['From'] = 'SecShare <secshare@company.com>'
        message['To'] = user_email
        message.attach(MIMEText(body, "html"))

        try:
            logger.debug('Attempting to send rejection email...')
            self.send_email(
                _sender='secshare@company.com',
                _recipients=[user_email],
                _cc=[],
                _subject=subject,
                _message=message
            )
            logger.debug('Rejection email sent successfully.')
        except Exception as e:
            logger.error(f"Error sending rejection email to {user_email}: {e}")
            raise