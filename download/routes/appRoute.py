from flask import Blueprint
from download.controllers.appController import home, favicon, download_file, manager_download_file, user_download_file, health_check

appRoute = Blueprint('appRoute', __name__)

appRoute.route('/', methods=['GET'])(home)
appRoute.route('/favicon.ico', methods=['GET'])(favicon)
appRoute.route('/<unique_id>', methods=['GET'])(download_file)
appRoute.route('/manager/<unique_id>', methods=['GET', 'POST'])(manager_download_file)
appRoute.route('/user/<unique_id>', methods=['GET', 'POST'])(user_download_file)
appRoute.route('/health-check', methods=['GET'])(health_check)