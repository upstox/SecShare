import sys
import os

# Add the parent directory to the Python path to locate 'shared'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template
from itsdangerous import URLSafeTimedSerializer
import boto3
from botocore.client import Config
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from .config import load_config
from .models.dbModel import DbManager
from shared.utils.logger import logger

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Load config values to app config 
    config_values = load_config()
    logger.debug(f'Loaded config keys: {list(config_values.keys())}')
    
    # Set configuration values individually to ensure they're properly loaded
    for key, value in config_values.items():
        app.config[key] = value
    
    logger.debug(f'App config keys after setting: {list(app.config.keys())}')

    # Extract individual values for easier access
    db_writer_host = config_values['db_writer_host']
    db_writer_user = config_values['db_writer_user']
    db_reader_host = config_values['db_reader_host']
    db_reader_user = config_values['db_reader_user']
    db_name = config_values['db_name']
    db_port = config_values['db_port']
    db_writer_password = config_values['db_writer_password']
    db_reader_password = config_values['db_reader_password']
    
    app.config['db_manager_writer'] = DbManager(
        host = db_writer_host,
        user = db_writer_user,
        password = db_writer_password,
        database = db_name,
        port = db_port,
        ssl = {'ssl-mode': 'DISABLED'}
    )
    
    app.config['db_manager_reader'] = DbManager(
        host = db_reader_host,
        user = db_reader_user,
        password = db_reader_password,
        database = db_name,
        port = db_port,
        ssl = {'ssl-mode': 'DISABLED'}
    )

    app.config['SECRET_KEY'] = config_values['secret_key']
    app.config['DEBUG'] = True
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['RATELIMIT_HEADERS_ENABLED'] = True
    
    # AWS Configuration
    aws_region = config_values.get('aws_region')
    aws_s3_bucket_name = config_values.get('s3_bucket_name')
    aws_kms_key_id = config_values.get('aws_kms_key_id')
    
    logger.info(f'--- AWS Config Debug:')
    logger.info(f'--- aws_region: {aws_region} (type: {type(aws_region)})')
    logger.info(f'--- aws_s3_bucket_name: {aws_s3_bucket_name} (type: {type(aws_s3_bucket_name)})')
    logger.info(f'--- aws_kms_key_id: {aws_kms_key_id} (type: {type(aws_kms_key_id)})')
    
    app.config['aws_s3_bucket_name'] = aws_s3_bucket_name
    app.config['aws_region'] = aws_region
    app.config['aws_kms_key_id'] = aws_kms_key_id
    
    # Initialize AWS clients
    app.config['s3_client'] = boto3.client('s3', region_name=aws_region, config=Config(signature_version='s3v4'))
    app.config['kms_client'] = boto3.client('kms', region_name=aws_region)

    def decrypt_file_content(encrypted_content, dek, iv):
        """Decrypt file content using DEK."""
        cipher = AES.new(dek, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(encrypted_content), AES.block_size)

    @app.after_request
    def add_header(response):
        response.headers['Cache-Control'] = 'no-store'
        return response
    # Error handler for 404 (Page Not Found)
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', message="Page not found. Please check the URL and try again."), 404

    # Error handler for 403 (Forbidden)
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('error.html', message="Access forbidden. You don't have permission to view this page."), 403

    # Error handler for 500 (Internal Server Error)
    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('error.html', message="Something went wrong. Please reload the page."), 500

    @app.errorhandler(429)
    def ratelimit_error(e):
        logger.warning(f"Rate limit exceeded: {request.remote_addr} - {request.path}")
        return render_template('error.html', message="Too many requests. Slow down."), 429

    # Catch-all handler for other unhandled HTTP errors
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        return render_template('error.html', message="An unexpected error occurred. Please try again later."), 500

    @app.after_request
    def add_header(response):
        response.headers['Cache-Control'] = 'no-store'
        return response

    from download.routes.appRoute import appRoute
    from download.routes.apiRoute import apiRoute
    app.register_blueprint(appRoute, url_prefix='/')
    app.register_blueprint(apiRoute, url_prefix='/api')

    return app
