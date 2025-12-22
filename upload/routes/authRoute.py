from flask import Blueprint
from upload.controllers.authController import login, callback

authRoute = Blueprint('authRoute', __name__)

authRoute.route('/', methods=['GET', 'POST', 'OPTIONS'])(login)
authRoute.route('/callback', methods=['GET', 'POST', 'OPTIONS'])(callback)