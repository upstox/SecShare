"""
Test cases for apiController.py functions
"""
import pytest
import sys
import os
import hashlib
import secrets
import threading
import time
from unittest.mock import Mock, patch, MagicMock, mock_open
from flask import Flask, g
from io import BytesIO
from datetime import datetime

# Add the parent directory to the Python path to locate modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import shared test utilities
from .test_utils import MockDbManager, MockConnection, MockCursor

from upload.controllers.apiController import (
    allowed_file, approve, reject, upload, health_check
)


class TestAllowedFile:
    """Test cases for the allowed_file helper function"""
    
    def test_allowed_file_valid_extension(self):
        """Test allowed_file with valid file extension"""
        allowed_extensions = {'pdf', 'docx', 'txt', 'jpg'}
        result = allowed_file('document.pdf', allowed_extensions)
        assert result is True
    
    def test_allowed_file_valid_extension_case_insensitive(self):
        """Test allowed_file with valid file extension (case insensitive)"""
        allowed_extensions = {'pdf', 'docx', 'txt', 'jpg'}
        result = allowed_file('document.PDF', allowed_extensions)
        assert result is True
    
    def test_allowed_file_invalid_extension(self):
        """Test allowed_file with invalid file extension"""
        allowed_extensions = {'pdf', 'docx', 'txt', 'jpg'}
        result = allowed_file('document.exe', allowed_extensions)
        assert result is False
    
    def test_allowed_file_no_extension(self):
        """Test allowed_file with no file extension"""
        allowed_extensions = {'pdf', 'docx', 'txt', 'jpg'}
        result = allowed_file('document', allowed_extensions)
        assert result is False
    
    def test_allowed_file_empty_filename(self):
        """Test allowed_file with empty filename"""
        allowed_extensions = {'pdf', 'docx', 'txt', 'jpg'}
        result = allowed_file('', allowed_extensions)
        assert result is False
    
    def test_allowed_file_none_filename(self):
        """Test allowed_file with None filename"""
        allowed_extensions = {'pdf', 'docx', 'txt', 'jpg'}
        result = allowed_file(None, allowed_extensions)
        assert result is False
    
    def test_allowed_file_multiple_dots(self):
        """Test allowed_file with multiple dots in filename"""
        allowed_extensions = {'pdf', 'docx', 'txt', 'jpg'}
        result = allowed_file('document.backup.pdf', allowed_extensions)
        assert result is True
    
    def test_allowed_file_empty_extensions(self):
        """Test allowed_file with empty allowed extensions"""
        allowed_extensions = set()
        result = allowed_file('document.pdf', allowed_extensions)
        assert result is False


class TestApprove:
    """Test cases for the approve function"""
    
    @pytest.fixture
    def app(self):
        """Create a test Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['user_download_link'] = 'https://example.com/download/unique_id_placeholder'
        app.config['db_manager_reader'] = MockDbManager()
        app.config['db_manager_writer'] = MockDbManager()
        app.config['mail_server'] = 'smtp.example.com'
        app.config['mail_port'] = 587
        app.config['smtp_username'] = 'test@example.com'
        app.config['smtp_password'] = 'test-password'
        
        # Create and register blueprints for testing
        from flask import Blueprint
        
        app_blueprint = Blueprint('appRoute', __name__)
        
        @app_blueprint.route('/')
        def home():
            return "Home"
        
        @app_blueprint.route('/approvals')
        def approvals():
            return "Approvals"
        
        app.register_blueprint(app_blueprint)
        
        with app.app_context():
            yield app
    
    def test_approve_success(self, app):
        """Test successful file approval"""
        with app.test_request_context('/approve/test_unique_id', method='POST', data={
            'password': 'test_password'
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock database results
            mock_db_manager_reader = app.config['db_manager_reader']
            mock_db_manager_writer = app.config['db_manager_writer']
            mock_connection = mock_db_manager_reader.connection
            mock_cursor = MockCursor()
            mock_connection.cursor = lambda: mock_cursor
            
            # Set up mock results
            mock_cursor.fetchone_result = (1,)  # File exists
            mock_db_manager_reader._file_status = 'Pending'
            mock_db_manager_reader._is_file_valid = True
            mock_db_manager_reader._stored_password = hashlib.sha256('test_password'.encode()).hexdigest()
            mock_db_manager_reader._file_metadata = {
                'uploaded_by': 'user@example.com',
                'file_name': 'test_file.pdf',
                'ttl': 7,
                'expiry': '2023-12-31',
                'business_justification': 'Test justification',
                'recipients': 'recipient@example.com'
            }
            
            with patch('upload.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.apiController.flash') as mock_flash:
                    with patch('upload.controllers.apiController.MailHandler') as mock_mail_handler:
                        mock_mail_instance = Mock()
                        mock_mail_handler.return_value = mock_mail_instance
                        
                        # Call the function directly (bypassing decorator)
                        result = approve.__wrapped__('test_unique_id')
                        
                        # Assertions
                        mock_flash.assert_called_with('File approved successfully! Notifications sent.', 'success')
                        mock_redirect.assert_called_once()
                        mock_mail_instance.notify_user_on_approval.assert_called_once()
                        mock_mail_instance.send_email_to_recipients.assert_called_once()
    
    def test_approve_invalid_password(self, app):
        """Test approval with invalid password"""
        with app.test_request_context('/approve/test_unique_id', method='POST', data={
            'password': 'wrong_password'
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock database results
            mock_db_manager_reader = app.config['db_manager_reader']
            mock_connection = mock_db_manager_reader.connection
            mock_cursor = MockCursor()
            mock_connection.cursor = lambda: mock_cursor
            
            # Set up mock results
            mock_cursor.fetchone_result = (1,)  # File exists
            mock_db_manager_reader._file_status = 'Pending'
            mock_db_manager_reader._is_file_valid = True
            mock_db_manager_reader._stored_password = hashlib.sha256('correct_password'.encode()).hexdigest()
            
            with patch('upload.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.apiController.flash') as mock_flash:
                    # Call the function directly (bypassing decorator)
                    result = approve.__wrapped__('test_unique_id')
                    
                    # Assertions
                    mock_flash.assert_called_with('Invalid approval password.', 'error')
                    # The function calls redirect twice (once in the function and once in finally block)
                    assert mock_redirect.call_count == 2
    
    def test_approve_file_not_found(self, app):
        """Test approval with file not found"""
        with app.test_request_context('/approve/test_unique_id', method='POST', data={
            'password': 'test_password'
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock database results
            mock_db_manager_reader = app.config['db_manager_reader']
            mock_db_manager_reader._file_status = None
            
            with patch('upload.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.apiController.flash') as mock_flash:
                    # Call the function directly (bypassing decorator)
                    result = approve.__wrapped__('test_unique_id')
                    
                    # Assertions
                    mock_flash.assert_called_with('No file found with this unique ID.', 'error')
                    # The function calls redirect twice (once in the function and once in finally block)
                    assert mock_redirect.call_count == 2
    
    def test_approve_file_already_approved(self, app):
        """Test approval with already approved file"""
        with app.test_request_context('/approve/test_unique_id', method='POST', data={
            'password': 'test_password'
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock database results
            mock_db_manager_reader = app.config['db_manager_reader']
            mock_db_manager_reader._file_status = 'Approved'
            
            with patch('upload.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.apiController.flash') as mock_flash:
                    # Call the function directly (bypassing decorator)
                    result = approve.__wrapped__('test_unique_id')
                    
                    # Assertions
                    mock_flash.assert_called_with('This file is already approved. No further action possible.', 'error')
                    # The function calls redirect twice (once in the function and once in finally block)
                    assert mock_redirect.call_count == 2
    
    def test_approve_file_expired(self, app):
        """Test approval with expired file"""
        with app.test_request_context('/approve/test_unique_id', method='POST', data={
            'password': 'test_password'
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock database results
            mock_db_manager_reader = app.config['db_manager_reader']
            mock_db_manager_reader._file_status = 'Pending'
            mock_db_manager_reader._is_file_valid = False  # File expired
            
            with patch('upload.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.apiController.flash') as mock_flash:
                    # Call the function directly (bypassing decorator)
                    result = approve.__wrapped__('test_unique_id')
                    
                    # Assertions
                    mock_flash.assert_called_with('This file has expired and cannot be approved.', 'error')
                    # The function calls redirect twice (once in the function and once in finally block)
                    assert mock_redirect.call_count == 2
    
    def test_approve_database_error(self, app):
        """Test approval with database error"""
        with app.test_request_context('/approve/test_unique_id', method='POST', data={
            'password': 'test_password'
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock database results
            mock_db_manager_reader = app.config['db_manager_reader']
            # Override the method to raise exception
            def mock_get_file_status(unique_id):
                raise Exception("Database error")
            mock_db_manager_reader.get_file_status = mock_get_file_status
            
            with patch('upload.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.apiController.flash') as mock_flash:
                    with patch('upload.controllers.apiController.logger') as mock_logger:
                        # Call the function directly (bypassing decorator)
                        result = approve.__wrapped__('test_unique_id')
                        
                        # Assertions
                        mock_flash.assert_called_with('An error occurred while approving the file. Please try again.', 'error')
                        mock_redirect.assert_called_once()
                        mock_logger.error.assert_called()


class TestReject:
    """Test cases for the reject function"""
    
    @pytest.fixture
    def app(self):
        """Create a test Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['db_manager_reader'] = MockDbManager()
        app.config['db_manager_writer'] = MockDbManager()
        app.config['mail_server'] = 'smtp.example.com'
        app.config['mail_port'] = 587
        app.config['smtp_username'] = 'test@example.com'
        app.config['smtp_password'] = 'test-password'
        
        # Create and register blueprints for testing
        from flask import Blueprint
        
        app_blueprint = Blueprint('appRoute', __name__)
        
        @app_blueprint.route('/approvals')
        def approvals():
            return "Approvals"
        
        app.register_blueprint(app_blueprint)
        
        with app.app_context():
            yield app
    
    def test_reject_success(self, app):
        """Test successful file rejection"""
        with app.test_request_context('/reject/test_unique_id', method='POST', data={
            'password': 'test_password'
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock database results
            mock_db_manager_reader = app.config['db_manager_reader']
            mock_db_manager_writer = app.config['db_manager_writer']
            
            # Set up mock results
            mock_db_manager_reader._file_status = 'Pending'
            mock_db_manager_reader._stored_password = hashlib.sha256('test_password'.encode()).hexdigest()
            mock_db_manager_reader._file_metadata = {
                'uploaded_by': 'user@example.com',
                'file_name': 'test_file.pdf',
                'ttl': 7,
                'expiry': '2023-12-31',
                'business_justification': 'Test justification',
                'recipients': 'recipient@example.com'
            }
            
            with patch('upload.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.apiController.flash') as mock_flash:
                    with patch('upload.controllers.apiController.MailHandler') as mock_mail_handler:
                        mock_mail_instance = Mock()
                        mock_mail_handler.return_value = mock_mail_instance
                        
                        # Call the function directly (bypassing decorator)
                        result = reject.__wrapped__('test_unique_id')
                        
                        # Assertions
                        mock_flash.assert_called_with('File rejected successfully!', 'success')
                        mock_redirect.assert_called_once()
                        mock_mail_instance.notify_user_on_rejection.assert_called_once()
    
    def test_reject_invalid_password(self, app):
        """Test rejection with invalid password"""
        with app.test_request_context('/reject/test_unique_id', method='POST', data={
            'password': 'wrong_password'
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock database results
            mock_db_manager_reader = app.config['db_manager_reader']
            mock_db_manager_reader._file_status = 'Pending'
            mock_db_manager_reader._stored_password = hashlib.sha256('correct_password'.encode()).hexdigest()
            
            with patch('upload.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.apiController.flash') as mock_flash:
                    # Call the function directly (bypassing decorator)
                    result = reject.__wrapped__('test_unique_id')
                    
                    # Assertions
                    mock_flash.assert_called_with('Invalid rejection password.', 'error')
                    mock_redirect.assert_called_once()
    
    def test_reject_file_not_found(self, app):
        """Test rejection with file not found"""
        with app.test_request_context('/reject/test_unique_id', method='POST', data={
            'password': 'test_password'
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock database results
            mock_db_manager_reader = app.config['db_manager_reader']
            mock_db_manager_reader._file_status = None
            
            with patch('upload.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.apiController.flash') as mock_flash:
                    # Call the function directly (bypassing decorator)
                    result = reject.__wrapped__('test_unique_id')
                    
                    # Assertions
                    mock_flash.assert_called_with('No file found with this unique ID.', 'error')
                    mock_redirect.assert_called_once()
    
    def test_reject_file_already_rejected(self, app):
        """Test rejection with already rejected file"""
        with app.test_request_context('/reject/test_unique_id', method='POST', data={
            'password': 'test_password'
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock database results
            mock_db_manager_reader = app.config['db_manager_reader']
            mock_db_manager_reader._file_status = 'Rejected'
            
            with patch('upload.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.apiController.flash') as mock_flash:
                    # Call the function directly (bypassing decorator)
                    result = reject.__wrapped__('test_unique_id')
                    
                    # Assertions
                    mock_flash.assert_called_with('This file is already rejected. No further action possible.', 'error')
                    mock_redirect.assert_called_once()
    
    def test_reject_database_error(self, app):
        """Test rejection with database error"""
        with app.test_request_context('/reject/test_unique_id', method='POST', data={
            'password': 'test_password'
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock database results
            mock_db_manager_reader = app.config['db_manager_reader']
            # Override the method to raise exception
            def mock_get_file_status(unique_id):
                raise Exception("Database error")
            mock_db_manager_reader.get_file_status = mock_get_file_status
            
            with patch('upload.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.apiController.flash') as mock_flash:
                    with patch('upload.controllers.apiController.logger') as mock_logger:
                        # Call the function directly (bypassing decorator)
                        result = reject.__wrapped__('test_unique_id')
                        
                        # Assertions
                        mock_flash.assert_called_with('An error occurred while rejecting the file.', 'error')
                        mock_redirect.assert_called_once()
                        mock_logger.error.assert_called()


class TestUpload:
    """Test cases for the upload function"""
    
    @pytest.fixture
    def app(self):
        """Create a test Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['max_file_size'] = 10485760  # 10MB
        app.config['allowed_extensions'] = 'pdf,docx,txt,jpg,png'
        app.config['db_manager_reader'] = MockDbManager()
        app.config['db_manager_writer'] = MockDbManager()
        app.config['s3_bucket_name'] = 'test-bucket'
        app.config['aws_kms_key_id'] = 'test-kms-key'
        app.config['mail_server'] = 'smtp.example.com'
        app.config['mail_port'] = 587
        app.config['smtp_username'] = 'test@example.com'
        app.config['smtp_password'] = 'test-password'
        app.config['approve_url'] = 'https://example.com/approve'
        app.config['reject_url'] = 'https://example.com/reject'
        app.config['manager_download_url'] = 'https://example.com/manager-download'
        
        # Create and register blueprints for testing
        from flask import Blueprint
        
        app_blueprint = Blueprint('appRoute', __name__)
        
        @app_blueprint.route('/')
        def home():
            return "Home"
        
        app.register_blueprint(app_blueprint)
        
        with app.app_context():
            yield app
    
    def test_upload_no_file(self, app):
        """Test upload with no file provided"""
        with app.test_request_context('/upload', method='POST', data={
            'ttl': '7'
        }):
            g.user = {'preferred_username': 'user@example.com'}
            
            # Mock request.files to be empty
            with patch('upload.controllers.apiController.request') as mock_request:
                mock_request.files = {}
                mock_request.form = {'ttl': '7'}
                mock_request.method = 'POST'
                
                with patch('upload.controllers.apiController.redirect') as mock_redirect:
                    mock_redirect.return_value = Mock()
                    
                    with patch('upload.controllers.apiController.flash') as mock_flash:
                        # Call the function directly (bypassing both decorators)
                        result = upload.__wrapped__.__wrapped__()
                        
                        # Assertions
                        mock_flash.assert_called_with('No file or TTL provided', 'error')
                        mock_redirect.assert_called_once()
    
    def test_upload_invalid_ttl(self, app):
        """Test upload with invalid TTL"""
        test_file = BytesIO(b'Test file content')
        test_file.filename = 'test_file.pdf'
        
        with app.test_request_context('/upload', method='POST', data={
            'ttl': 'invalid'
        }):
            g.user = {'preferred_username': 'user@example.com'}
            
            # Mock request properly
            with patch('upload.controllers.apiController.request') as mock_request:
                mock_request.files = {'file': test_file}
                mock_request.form = {'ttl': 'invalid'}
                mock_request.method = 'POST'
                
                with patch('upload.controllers.apiController.redirect') as mock_redirect:
                    mock_redirect.return_value = Mock()
                    
                    with patch('upload.controllers.apiController.flash') as mock_flash:
                        # Call the function directly (bypassing both decorators)
                        result = upload.__wrapped__.__wrapped__()
                        
                        # Assertions
                        mock_flash.assert_called_with('Invalid TTL value. Please enter a valid number.', 'error')
                        mock_redirect.assert_called_once()
    
    def test_upload_ttl_out_of_range(self, app):
        """Test upload with TTL out of range"""
        test_file = BytesIO(b'Test file content')
        test_file.filename = 'test_file.pdf'
        
        with app.test_request_context('/upload', method='POST', data={
            'ttl': '10'
        }):
            g.user = {'preferred_username': 'user@example.com'}
            
            # Mock request properly
            with patch('upload.controllers.apiController.request') as mock_request:
                mock_request.files = {'file': test_file}
                mock_request.form = {'ttl': '10'}
                mock_request.method = 'POST'
                
                with patch('upload.controllers.apiController.redirect') as mock_redirect:
                    mock_redirect.return_value = Mock()
                    
                    with patch('upload.controllers.apiController.flash') as mock_flash:
                        # Call the function directly (bypassing both decorators)
                        result = upload.__wrapped__.__wrapped__()
                        
                        # Assertions
                        mock_flash.assert_called_with('TTL value must be between 1 and 7 days.', 'error')
                        mock_redirect.assert_called_once()
    
    def test_upload_file_too_large(self, app):
        """Test upload with file too large"""
        # Create a large mock file
        test_file = BytesIO(b'x' * 20000000)  # 20MB file
        test_file.filename = 'test_file.pdf'
        
        with app.test_request_context('/upload', method='POST', data={
            'ttl': '7'
        }):
            g.user = {'preferred_username': 'user@example.com'}
            
            # Mock request properly
            with patch('upload.controllers.apiController.request') as mock_request:
                mock_request.files = {'file': test_file}
                mock_request.form = {'ttl': '7'}
                mock_request.method = 'POST'
                
                with patch('upload.controllers.apiController.redirect') as mock_redirect:
                    mock_redirect.return_value = Mock()
                    
                    with patch('upload.controllers.apiController.flash') as mock_flash:
                        # Call the function directly (bypassing both decorators)
                        result = upload.__wrapped__.__wrapped__()
                        
                        # Assertions
                        mock_flash.assert_called_with('File must be below 10485760 bytes.', 'error')
                        mock_redirect.assert_called_once()
    
    def test_upload_invalid_file_type(self, app):
        """Test upload with invalid file type"""
        test_file = BytesIO(b'Test file content')
        test_file.filename = 'test_file.exe'
        
        with app.test_request_context('/upload', method='POST', data={
            'ttl': '7'
        }):
            g.user = {'preferred_username': 'user@example.com'}
            
            # Mock request properly
            with patch('upload.controllers.apiController.request') as mock_request:
                mock_request.files = {'file': test_file}
                mock_request.form = {'ttl': '7'}
                mock_request.method = 'POST'
                
                with patch('upload.controllers.apiController.redirect') as mock_redirect:
                    mock_redirect.return_value = Mock()
                    
                    with patch('upload.controllers.apiController.flash') as mock_flash:
                        # Call the function directly (bypassing both decorators)
                        result = upload.__wrapped__.__wrapped__()
                        
                        # Assertions
                        mock_flash.assert_called_with('File type not allowed', 'error')
                        mock_redirect.assert_called_once()
    
    def test_upload_no_manager_email(self, app):
        """Test upload with no manager email found"""
        test_file = BytesIO(b'Test file content')
        test_file.filename = 'test_file.pdf'
        
        with app.test_request_context('/upload', method='POST', data={
            'ttl': '7'
        }):
            g.user = {'preferred_username': 'user@example.com'}
            
            # Mock database results
            mock_db_manager_reader = app.config['db_manager_reader']
            mock_db_manager_reader._manager_email = None
            
            # Mock request properly
            with patch('upload.controllers.apiController.request') as mock_request:
                mock_request.files = {'file': test_file}
                mock_request.form = {'ttl': '7'}
                mock_request.method = 'POST'
                
                with patch('upload.controllers.apiController.redirect') as mock_redirect:
                    mock_redirect.return_value = Mock()
                    
                    with patch('upload.controllers.apiController.flash') as mock_flash:
                        # Call the function directly (bypassing both decorators)
                        result = upload.__wrapped__.__wrapped__()
                        
                        # Assertions
                        mock_flash.assert_called_with('You cannot upload files without an assigned manager in AD. Please contact the IT admin.', 'error')
                        mock_redirect.assert_called_once()


class TestHealthCheck:
    """Test cases for the health_check function"""
    
    @pytest.fixture
    def app(self):
        """Create a test Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        with app.app_context():
            yield app
    
    def test_health_check_success(self, app):
        """Test successful health check"""
        with app.app_context():
            result = health_check()
            
            # Assertions
            assert result[1] == 200  # Status code
            assert 'healthy' in result[0].get_json()['status']
    
    def test_health_check_with_exception(self, app):
        """Test health check with exception"""
        with app.app_context():
            # Mock jsonify to raise exception on first call, return normal response on second
            with patch('upload.controllers.apiController.jsonify') as mock_jsonify:
                # First call (in try block) raises exception, second call (in except block) returns mock
                mock_response = Mock()
                mock_response.get_json.return_value = {'status': 'unhealthy', 'error': 'Test error'}
                mock_jsonify.side_effect = [Exception("Test error"), mock_response]
                
                result = health_check()
                
                # Assertions
                assert result[1] == 500  # Status code
                assert 'unhealthy' in result[0].get_json()['status']
                assert 'Test error' in result[0].get_json()['error']


class TestPasswordHashing:
    """Test cases for password hashing logic in approve and reject functions"""
    
    @pytest.fixture
    def app(self):
        """Create a test Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['user_download_link'] = 'https://example.com/download/unique_id_placeholder'
        app.config['db_manager_reader'] = MockDbManager()
        app.config['db_manager_writer'] = MockDbManager()
        app.config['mail_server'] = 'smtp.example.com'
        app.config['mail_port'] = 587
        app.config['smtp_username'] = 'test@example.com'
        app.config['smtp_password'] = 'test-password'
        
        # Create and register blueprints for testing
        from flask import Blueprint
        
        app_blueprint = Blueprint('appRoute', __name__)
        
        @app_blueprint.route('/approvals')
        def approvals():
            return "Approvals"
        
        app.register_blueprint(app_blueprint)
        
        with app.app_context():
            yield app
    
    def test_approve_with_hashed_password(self, app):
        """Test approval with already hashed password"""
        hashed_password = hashlib.sha256('test_password'.encode()).hexdigest()
        
        with app.test_request_context('/approve/test_unique_id', method='POST', data={
            'password': hashed_password
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock database results
            mock_db_manager_reader = app.config['db_manager_reader']
            mock_db_manager_writer = app.config['db_manager_writer']
            mock_connection = mock_db_manager_reader.connection
            mock_cursor = MockCursor()
            mock_connection.cursor = lambda: mock_cursor
            
            # Set up mock results
            mock_cursor.fetchone_result = (1,)  # File exists
            mock_db_manager_reader._file_status = 'Pending'
            mock_db_manager_reader._is_file_valid = True
            mock_db_manager_reader._stored_password = hashed_password
            mock_db_manager_reader._file_metadata = {
                'uploaded_by': 'user@example.com',
                'file_name': 'test_file.pdf',
                'ttl': 7,
                'expiry': '2023-12-31',
                'business_justification': 'Test justification',
                'recipients': 'recipient@example.com'
            }
            
            with patch('upload.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.apiController.flash') as mock_flash:
                    with patch('upload.controllers.apiController.MailHandler') as mock_mail_handler:
                        mock_mail_instance = Mock()
                        mock_mail_handler.return_value = mock_mail_instance
                        
                        # Call the function directly (bypassing decorator)
                        result = approve.__wrapped__('test_unique_id')
                        
                        # Assertions
                        mock_flash.assert_called_with('File approved successfully! Notifications sent.', 'success')
                        mock_redirect.assert_called_once()
    
    def test_reject_with_hashed_password(self, app):
        """Test rejection with already hashed password"""
        hashed_password = hashlib.sha256('test_password'.encode()).hexdigest()
        
        with app.test_request_context('/reject/test_unique_id', method='POST', data={
            'password': hashed_password
        }):
            g.user = {'preferred_username': 'admin@example.com'}
            
            # Mock database results
            mock_db_manager_reader = app.config['db_manager_reader']
            mock_db_manager_writer = app.config['db_manager_writer']
            mock_db_manager_reader._file_status = 'Pending'
            mock_db_manager_reader._stored_password = hashed_password
            mock_db_manager_reader._file_metadata = {
                'uploaded_by': 'user@example.com',
                'file_name': 'test_file.pdf',
                'ttl': 7,
                'expiry': '2023-12-31',
                'business_justification': 'Test justification',
                'recipients': 'recipient@example.com'
            }
            
            with patch('upload.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('upload.controllers.apiController.flash') as mock_flash:
                    with patch('upload.controllers.apiController.MailHandler') as mock_mail_handler:
                        mock_mail_instance = Mock()
                        mock_mail_handler.return_value = mock_mail_instance
                        
                        # Call the function directly (bypassing decorator)
                        result = reject.__wrapped__('test_unique_id')
                        
                        # Assertions
                        mock_flash.assert_called_with('File rejected successfully!', 'success')
                        mock_redirect.assert_called_once()