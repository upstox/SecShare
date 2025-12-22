from flask import Blueprint
from upload.controllers.apiController import upload, approve, reject, health_check

apiRoute = Blueprint('apiRoute', __name__)

apiRoute.route('/upload', methods=['POST'])(upload)
apiRoute.route('/approve/<unique_id>', methods=['POST'])(approve)
apiRoute.route('/reject/<unique_id>', methods=['POST'])(reject)
apiRoute.route('/health-check', methods=['GET'])(health_check)