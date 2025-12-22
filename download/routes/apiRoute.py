from flask import Blueprint
from download.controllers.apiController import verify_password, health_check

apiRoute = Blueprint('apiRoute', __name__)

apiRoute.route('/verify/password', methods=['POST'])(verify_password)