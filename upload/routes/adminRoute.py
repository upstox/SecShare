from flask import Blueprint
from upload.controllers.adminController import home, employee_manager_details, file_metadata, file_metadata_archive, update_manager_email

adminRoute = Blueprint('adminRoute', __name__)

adminRoute.route('/', methods=['GET'])(home)
adminRoute.route('/employee_manager_details', methods=['GET'])(employee_manager_details)
adminRoute.route('/file_metadata', methods=['GET'])(file_metadata)
adminRoute.route('/file_metadata_archive', methods=['GET'])(file_metadata_archive)
adminRoute.route('/update_manager_email', methods=['GET', 'POST'])(update_manager_email)