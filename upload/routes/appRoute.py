from flask import Blueprint
from upload.controllers.appController import home, history, approvals, health_check

appRoute = Blueprint('appRoute', __name__)

appRoute.route('/', methods=['GET'])(home)
appRoute.route('/history', methods=['GET'])(history)
appRoute.route('/approvals', methods=['GET'])(approvals)
appRoute.route('/health-check', methods=['GET'])(health_check)