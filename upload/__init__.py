import sys
import os

# Add the parent directory to the Python path to locate 'shared'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from itsdangerous import URLSafeTimedSerializer

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
    app.config['serializer'] = URLSafeTimedSerializer(config_values['secret_key'], salt=config_values['fixed_salt'])

    @app.before_request
    def clear_cache():
        app.jinja_env.cache = {}

    @app.after_request
    def add_header(response):
        response.cache_control.no_store = True
        return response

    from upload.routes.appRoute import appRoute
    from upload.routes.apiRoute import apiRoute
    from upload.routes.authRoute import authRoute
    from upload.routes.adminRoute import adminRoute
    app.register_blueprint(appRoute, url_prefix='/')
    app.register_blueprint(apiRoute, url_prefix='/api')
    app.register_blueprint(authRoute, url_prefix='/login')
    app.register_blueprint(adminRoute, url_prefix='/appsec')

    return app
