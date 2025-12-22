"""
Test cases for adminController.py functions
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, g

# Add the parent directory to the Python path to locate modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import shared test utilities
from .test_utils import MockDbManager, MockConnection, MockCursor, MockAdminModel

from upload.controllers.adminController import (
    is_admin, home, employee_manager_details, 
    file_metadata, file_metadata_archive, update_manager_email
)


class TestIsAdmin:
    """Test cases for the is_admin helper function"""
    
    @pytest.fixture
    def app(self):
        """Create a test Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['admin_access'] = 'admin@example.com,superuser@example.com,test@example.com'
        
        with app.app_context():
            yield app
    
    def test_is_admin_valid_admin(self, app):
        """Test is_admin with valid admin email"""
        with app.app_context():
            g.user = {'preferred_username': 'admin@example.com'}
            result = is_admin()
            assert result is True
    
    def test_is_admin_valid_admin_case_insensitive(self, app):
        """Test is_admin with valid admin email (case insensitive)"""
        with app.app_context():
            g.user = {'preferred_username': 'ADMIN@EXAMPLE.COM'}
            result = is_admin()
            assert result is True
    
    def test_is_admin_valid_admin_with_spaces(self, app):
        """Test is_admin with valid admin email containing spaces"""
        with app.app_context():
            g.user = {'preferred_username': '  admin@example.com  '}
            result = is_admin()
            assert result is True
    
    def test_is_admin_invalid_user(self, app):
        """Test is_admin with non-admin email"""
        with app.app_context():
            g.user = {'preferred_username': 'user@example.com'}
            result = is_admin()
            assert result is False
    
    def test_is_admin_empty_username(self, app):
        """Test is_admin with empty username"""
        with app.app_context():
            g.user = {'preferred_username': ''}
            result = is_admin()
            assert result is False
    
    def test_is_admin_missing_username(self, app):
        """Test is_admin with missing preferred_username"""
        with app.app_context():
            g.user = {}
            result = is_admin()
            assert result is False
    
    def test_is_admin_none_username(self, app):
        """Test is_admin with None username"""
        with app.app_context():
            g.user = {'preferred_username': None}
            result = is_admin()
            assert result is False


class TestAdminFunctions:
    """Test admin functions by bypassing decorators"""
    
    @pytest.fixture
    def app(self):
        """Create a test Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['admin_access'] = 'admin@example.com'
        app.config['db_manager_reader'] = MockDbManager()
        app.config['db_manager_writer'] = MockDbManager()
        
        # Create and register blueprints for testing
        from flask import Blueprint
        
        app_blueprint = Blueprint('appRoute', __name__)
        
        @app_blueprint.route('/')
        def home():
            return "Home"
        
        admin_blueprint = Blueprint('adminRoute', __name__)
        
        @admin_blueprint.route('/admin')
        def home():
            return "Admin Home"
        
        @admin_blueprint.route('/admin/update-manager-email')
        def update_manager_email():
            return "Update Manager Email"
        
        app.register_blueprint(app_blueprint)
        app.register_blueprint(admin_blueprint)
        
        with app.app_context():
            yield app
    
    def test_home_function_authorized_admin(self, app):
        """Test home function logic with authorized admin user"""
        with app.test_request_context('/admin'):
            g.user = {'preferred_username': 'admin@example.com'}
            
            with patch('upload.controllers.adminController.render_template') as mock_render:
                mock_render.return_value = "Admin Home Template"
                
                with patch('upload.controllers.adminController.logger') as mock_logger:
                    # Call the function directly (bypassing decorator)
                    result = home.__wrapped__()  # Access the original function
                    
                    # Assertions
                    mock_logger.info.assert_called_once_with('Admin home accessed by %s', 'admin@example.com')
                    mock_render.assert_called_once_with('/admin/home.html')
                    assert result == "Admin Home Template"
    
    def test_home_function_unauthorized_user(self, app):
        """Test home function logic with unauthorized user"""
        with app.test_request_context('/admin'):
            g.user = {'preferred_username': 'user@example.com'}
            
            with patch('upload.controllers.adminController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.adminController.flash') as mock_flash:
                    with patch('upload.controllers.adminController.logger') as mock_logger:
                        # Call the function directly (bypassing decorator)
                        result = home.__wrapped__()
                        
                        # Assertions
                        mock_logger.warning.assert_called_once_with('Unauthorized admin access attempt by %s', 'user@example.com')
                        mock_flash.assert_called_once_with('You are not authorized to access the admin page.', 'error')
                        mock_redirect.assert_called_once()
    
    def test_employee_manager_details_authorized_no_search(self, app):
        """Test employee_manager_details function logic with authorized user, no search query"""
        with app.test_request_context('/admin/employee-manager-details'):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock AdminModel
            with patch('upload.controllers.adminController.AdminModel') as mock_admin_model_class:
                mock_admin_model = MockAdminModel(
                    app.config['db_manager_reader'],
                    app.config['db_manager_writer']
                )
                mock_admin_model_class.return_value = mock_admin_model
                
                with patch('upload.controllers.adminController.render_template') as mock_render:
                    mock_render.return_value = "Employee Manager Details Template"
                    
                    # Call the function directly (bypassing decorator)
                    result = employee_manager_details.__wrapped__()
                    
                    # Assertions
                    mock_admin_model_class.assert_called_once()
                    mock_render.assert_called_once_with(
                        'admin/table.html',
                        title='Employee Manager Details',
                        results=mock_admin_model._employee_data['results'],
                        columns=mock_admin_model._employee_data['columns'],
                        page=1,
                        total_pages=mock_admin_model._employee_data['total_pages'],
                        search='',
                        search_placeholder='Search employees...'
                    )
                    assert result == "Employee Manager Details Template"
    
    def test_employee_manager_details_unauthorized(self, app):
        """Test employee_manager_details function logic with unauthorized user"""
        with app.test_request_context('/admin/employee-manager-details'):
            g.user = {'preferred_username': 'user@example.com'}
            
            with patch('upload.controllers.adminController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.adminController.flash') as mock_flash:
                    with patch('upload.controllers.adminController.logger') as mock_logger:
                        # Call the function directly (bypassing decorator)
                        result = employee_manager_details.__wrapped__()
                        
                        # Assertions
                        mock_logger.warning.assert_called_once_with('Unauthorized access to employee_manager_details by %s', 'user@example.com')
                        mock_flash.assert_called_once_with('Unauthorized access.', 'error')
                        mock_redirect.assert_called_once()
    
    def test_file_metadata_authorized_no_search(self, app):
        """Test file_metadata function logic with authorized user, no search query"""
        with app.test_request_context('/admin/file-metadata'):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock AdminModel
            with patch('upload.controllers.adminController.AdminModel') as mock_admin_model_class:
                mock_admin_model = MockAdminModel(
                    app.config['db_manager_reader'],
                    app.config['db_manager_writer']
                )
                mock_admin_model_class.return_value = mock_admin_model
                
                with patch('upload.controllers.adminController.render_template') as mock_render:
                    mock_render.return_value = "File Metadata Template"
                    
                    # Call the function directly (bypassing decorator)
                    result = file_metadata.__wrapped__()
                    
                    # Assertions
                    mock_admin_model_class.assert_called_once()
                    mock_render.assert_called_once_with(
                        'admin/table.html',
                        title='File Metadata',
                        results=mock_admin_model._file_metadata_data['results'],
                        columns=mock_admin_model._file_metadata_data['columns'],
                        page=1,
                        total_pages=mock_admin_model._file_metadata_data['total_pages'],
                        search='',
                        search_placeholder='Search file name...'
                    )
                    assert result == "File Metadata Template"
    
    def test_file_metadata_archive_authorized_no_search(self, app):
        """Test file_metadata_archive function logic with authorized user, no search query"""
        with app.test_request_context('/admin/file-metadata-archive'):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock AdminModel
            with patch('upload.controllers.adminController.AdminModel') as mock_admin_model_class:
                mock_admin_model = MockAdminModel(
                    app.config['db_manager_reader'],
                    app.config['db_manager_writer']
                )
                mock_admin_model_class.return_value = mock_admin_model
                
                with patch('upload.controllers.adminController.render_template') as mock_render:
                    mock_render.return_value = "File Metadata Archive Template"
                    
                    # Call the function directly (bypassing decorator)
                    result = file_metadata_archive.__wrapped__()
                    
                    # Assertions
                    mock_admin_model_class.assert_called_once()
                    mock_render.assert_called_once_with(
                        'admin/table.html',
                        title='File Metadata Archive',
                        results=mock_admin_model._file_metadata_archive_data['results'],
                        columns=mock_admin_model._file_metadata_archive_data['columns'],
                        page=1,
                        total_pages=mock_admin_model._file_metadata_archive_data['total_pages'],
                        search='',
                        search_placeholder='Search file name...'
                    )
                    assert result == "File Metadata Archive Template"
    
    def test_update_manager_email_get_request(self, app):
        """Test update_manager_email function logic GET request"""
        with app.test_request_context('/admin/update-manager-email', method='GET'):
            g.user = {'preferred_username': 'admin@example.com'}
            
            with patch('upload.controllers.adminController.render_template') as mock_render:
                mock_render.return_value = "Update Manager Email Template"
                
                # Call the function directly (bypassing decorator)
                result = update_manager_email.__wrapped__()
                
                # Assertions
                mock_render.assert_called_once_with('admin/update_manager_email.html')
                assert result == "Update Manager Email Template"
    
    def test_update_manager_email_post_success(self, app):
        """Test update_manager_email function logic POST request with successful update"""
        with app.test_request_context('/admin/update-manager-email', method='POST', data={
            'employee_email': 'employee@example.com',
            'new_manager_email': 'newmanager@example.com'
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock AdminModel
            with patch('upload.controllers.adminController.AdminModel') as mock_admin_model_class:
                mock_admin_model = MockAdminModel(
                    app.config['db_manager_reader'],
                    app.config['db_manager_writer']
                )
                mock_admin_model_class.return_value = mock_admin_model
                
                with patch('upload.controllers.adminController.redirect') as mock_redirect:
                    mock_redirect.return_value = Mock()
                    
                    with patch('upload.controllers.adminController.flash') as mock_flash:
                        # Call the function directly (bypassing decorator)
                        result = update_manager_email.__wrapped__()
                        
                        # Assertions
                        mock_admin_model_class.assert_called_once()
                        mock_flash.assert_called_once_with('Manager email updated successfully.', 'success')
                        mock_redirect.assert_called_once()
    
    def test_update_manager_email_post_missing_fields(self, app):
        """Test update_manager_email function logic POST request with missing fields"""
        with app.test_request_context('/admin/update-manager-email', method='POST', data={
            'employee_email': 'employee@example.com'
            # Missing new_manager_email
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            with patch('upload.controllers.adminController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.adminController.flash') as mock_flash:
                    # Call the function directly (bypassing decorator)
                    result = update_manager_email.__wrapped__()
                    
                    # Assertions
                    mock_flash.assert_called_once_with('Both employee email and new manager email must be provided.', 'error')
                    mock_redirect.assert_called_once()
    
    def test_update_manager_email_post_invalid_email_format(self, app):
        """Test update_manager_email function logic POST request with invalid email format"""
        with app.test_request_context('/admin/update-manager-email', method='POST', data={
            'employee_email': 'employee@example.com',
            'new_manager_email': 'invalid-email-format'
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            with patch('upload.controllers.adminController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.adminController.flash') as mock_flash:
                    # Call the function directly (bypassing decorator)
                    result = update_manager_email.__wrapped__()
                    
                    # Assertions
                    mock_flash.assert_called_once_with('Invalid new manager email format.', 'error')
                    mock_redirect.assert_called_once()
    
    def test_update_manager_email_post_employee_not_found(self, app):
        """Test update_manager_email function logic POST request with employee not found"""
        with app.test_request_context('/admin/update-manager-email', method='POST', data={
            'employee_email': 'nonexistent@example.com',
            'new_manager_email': 'manager@example.com'
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock AdminModel with employee not found result
            with patch('upload.controllers.adminController.AdminModel') as mock_admin_model_class:
                mock_admin_model = MockAdminModel(
                    app.config['db_manager_reader'],
                    app.config['db_manager_writer']
                )
                mock_admin_model._update_result = {
                    'success': False, 
                    'message': 'Employee not found.', 
                    'error_type': 'not_found'
                }
                mock_admin_model_class.return_value = mock_admin_model
                
                with patch('upload.controllers.adminController.redirect') as mock_redirect:
                    mock_redirect.return_value = Mock()
                    
                    with patch('upload.controllers.adminController.flash') as mock_flash:
                        # Call the function directly (bypassing decorator)
                        result = update_manager_email.__wrapped__()
                        
                        # Assertions
                        mock_admin_model_class.assert_called_once()
                        mock_flash.assert_called_once_with('Employee not found.', 'error')
                        mock_redirect.assert_called_once()
    
    def test_update_manager_email_post_database_error(self, app):
        """Test update_manager_email function logic POST request with database error"""
        with app.test_request_context('/admin/update-manager-email', method='POST', data={
            'employee_email': 'employee@example.com',
            'new_manager_email': 'manager@example.com'
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock AdminModel with database error result
            with patch('upload.controllers.adminController.AdminModel') as mock_admin_model_class:
                mock_admin_model = MockAdminModel(
                    app.config['db_manager_reader'],
                    app.config['db_manager_writer']
                )
                mock_admin_model._update_result = {
                    'success': False, 
                    'message': 'Error updating manager email: Database connection error', 
                    'error_type': 'database_error'
                }
                mock_admin_model_class.return_value = mock_admin_model
                
                with patch('upload.controllers.adminController.redirect') as mock_redirect:
                    mock_redirect.return_value = Mock()
                    
                    with patch('upload.controllers.adminController.flash') as mock_flash:
                        # Call the function directly (bypassing decorator)
                        result = update_manager_email.__wrapped__()
                        
                        # Assertions
                        mock_admin_model_class.assert_called_once()
                        mock_flash.assert_called_once_with('Error updating manager email: Database connection error', 'error')
                        mock_redirect.assert_called_once()