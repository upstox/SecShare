import pytest
import hashlib
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, url_for

import sys
import os

# Add the parent directory to the Python path to locate modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import shared test utilities
from .test_utils import MockNoCredentialsError, MockClientError

from download.controllers.appController import download_file, manager_download_file, user_download_file


class TestDownloadFile:
    """Test cases for the download_file function in appController"""
    
    @pytest.fixture
    def app(self):
        """Create a test Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Mock app config values
        app.config['db_manager_reader'] = Mock()
        app.config['turnstile_site_key'] = 'test-site-key'
        
        # Create and register blueprints for testing
        from flask import Blueprint
        
        app_blueprint = Blueprint('appRoute', __name__)
        
        @app_blueprint.route('/')
        def home():
            return "Home"
        
        @app_blueprint.route('/manager/<file_id>')
        def manager_download():
            return "Manager Download"
        
        @app_blueprint.route('/user/<file_id>')
        def user_download():
            return "User Download"
        
        @app_blueprint.route('/download/<unique_id>')
        def download_file_route(unique_id):
            return f"Download File {unique_id}"
        
        app.register_blueprint(app_blueprint)
        
        with app.app_context():
            yield app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client"""
        return app.test_client()
    
    @pytest.fixture
    def mock_db_manager(self, app):
        """Mock database manager"""
        return app.config['db_manager_reader']
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample file metadata for testing"""
        return {
            'file_name': 'test_document.pdf',
            'user_password_hash': 'hashed_password_123',
            'ttl': 7,
            'status': 'Approved',
            'uploaded_by': 'test@example.com',
            'recipients': 'user@example.com',
            'business_justification': 'Test file for unit testing'
        }

    def test_download_file_success(self, app, mock_db_manager, sample_metadata):
        """Test successful download_file request with valid file"""
        with app.test_request_context('/download/test_unique_id_123'):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            with patch('download.controllers.appController.render_template') as mock_render:
                mock_render.return_value = "Password Prompt Template"
                
                result = download_file('test_unique_id_123')
                
                # Assertions
                mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                mock_db_manager.is_file_valid.assert_called_with('test_unique_id_123')
                mock_render.assert_called_once_with(
                    'password_prompt.html',
                    unique_id='test_unique_id_123',
                    filename='test_document.pdf',
                    turnstile_site_key='test-site-key'
                )
                assert result == "Password Prompt Template"

    def test_download_file_not_found(self, app, mock_db_manager):
        """Test when file metadata is not found"""
        with app.test_request_context('/download/test_unique_id_123'):
            # Mock database to return None (file not found)
            mock_db_manager.get_file_name.return_value = None
            
            with patch('download.controllers.appController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                result = download_file('test_unique_id_123')
                
                # Assertions
                mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                mock_redirect.assert_called_once()
                # Should not call is_file_valid if file not found
                mock_db_manager.is_file_valid.assert_not_called()

    def test_download_file_expired(self, app, mock_db_manager, sample_metadata):
        """Test when file has expired"""
        with app.test_request_context('/download/test_unique_id_123'):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = False  # File expired
            
            with patch('download.controllers.appController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                result = download_file('test_unique_id_123')
                
                # Assertions
                mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                mock_db_manager.is_file_valid.assert_called_with('test_unique_id_123')
                mock_redirect.assert_called_once()

    def test_download_file_invalid_after_validation(self, app, mock_db_manager, sample_metadata):
        """Test when file becomes invalid after initial validation check"""
        with app.test_request_context('/download/test_unique_id_123'):
            # Mock database responses - file exists but becomes invalid
            mock_db_manager.get_file_name.return_value = sample_metadata
            # First call returns True, second call returns False
            mock_db_manager.is_file_valid.side_effect = [True, False]
            
            with patch('download.controllers.appController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                result = download_file('test_unique_id_123')
                
                # Assertions
                mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                assert mock_db_manager.is_file_valid.call_count == 2
                mock_redirect.assert_called_once()

    def test_download_file_database_error(self, app, mock_db_manager):
        """Test when database throws an exception"""
        with app.test_request_context('/download/test_unique_id_123'):
            # Mock database to raise an exception
            mock_db_manager.get_file_name.side_effect = Exception("Database connection error")
            
            with patch('download.controllers.appController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                # Should handle the exception gracefully
                with pytest.raises(Exception, match="Database connection error"):
                    download_file('test_unique_id_123')

    def test_download_file_missing_filename_in_metadata(self, app, mock_db_manager):
        """Test when metadata exists but missing file_name field"""
        with app.test_request_context('/download/test_unique_id_123'):
            # Mock metadata without file_name
            incomplete_metadata = {
                'user_password_hash': 'hashed_password_123',
                'ttl': 7,
                'status': 'Approved'
                # Missing 'file_name'
            }
            mock_db_manager.get_file_name.return_value = incomplete_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            with patch('download.controllers.appController.render_template') as mock_render:
                mock_render.return_value = "Password Prompt Template"
                
                # Should handle missing file_name gracefully
                with pytest.raises(KeyError):
                    download_file('test_unique_id_123')

    def test_download_file_logging_verification(self, app, mock_db_manager, sample_metadata):
        """Test that appropriate logging occurs"""
        with app.test_request_context('/download/test_unique_id_123'):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            with patch('download.controllers.appController.render_template') as mock_render:
                mock_render.return_value = "Password Prompt Template"
                
                with patch('download.controllers.appController.logger') as mock_logger:
                    result = download_file('test_unique_id_123')
                    
                    # Verify logging was called
                    mock_logger.debug.assert_called()

    def test_download_file_different_unique_ids(self, app, mock_db_manager, sample_metadata):
        """Test with different unique_id formats"""
        test_cases = [
            'simple_id',
            'uuid-format-123e4567-e89b-12d3-a456-426614174000',
            'hash-format-abc123def456',
            '1234567890'
        ]
        
        for unique_id in test_cases:
            with app.test_request_context(f'/download/{unique_id}'):
                # Reset mocks for each test case
                mock_db_manager.reset_mock()
                mock_db_manager.get_file_name.return_value = sample_metadata
                mock_db_manager.is_file_valid.return_value = True
                
                with patch('download.controllers.appController.render_template') as mock_render:
                    mock_render.return_value = "Password Prompt Template"
                    
                    result = download_file(unique_id)
                    
                    # Assertions for each unique_id
                    mock_db_manager.get_file_name.assert_called_once_with(unique_id)
                    mock_db_manager.is_file_valid.assert_called_with(unique_id)
                    mock_render.assert_called_once_with(
                        'password_prompt.html',
                        unique_id=unique_id,
                        filename='test_document.pdf',
                        turnstile_site_key='test-site-key'
                    )

    def test_download_file_template_rendering(self, app, mock_db_manager, sample_metadata):
        """Test that template is rendered with correct parameters"""
        with app.test_request_context('/download/test_unique_id_123'):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            with patch('download.controllers.appController.render_template') as mock_render:
                mock_render.return_value = "Password Prompt Template"
                
                result = download_file('test_unique_id_123')
                
                # Verify template rendering with correct parameters
                mock_render.assert_called_once_with(
                    'password_prompt.html',
                    unique_id='test_unique_id_123',
                    filename='test_document.pdf',
                    turnstile_site_key='test-site-key'
                )

    def test_download_file_flash_messages(self, app, mock_db_manager):
        """Test that appropriate flash messages are set"""
        with app.test_request_context('/download/test_unique_id_123'):
            # Test file not found flash message
            mock_db_manager.get_file_name.return_value = None
            
            with patch('download.controllers.appController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('download.controllers.appController.flash') as mock_flash:
                    result = download_file('test_unique_id_123')
                    
                    # Verify flash message was called
                    mock_flash.assert_called_once_with('File not found or invalid unique ID.', 'error')

    def test_download_file_expired_flash_message(self, app, mock_db_manager, sample_metadata):
        """Test flash message for expired files"""
        with app.test_request_context('/download/test_unique_id_123'):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = False  # File expired
            
            with patch('download.controllers.appController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('download.controllers.appController.flash') as mock_flash:
                    result = download_file('test_unique_id_123')
                    
                    # Verify flash message was called for expired file
                    mock_flash.assert_called_once_with('This file has expired.', 'error')


class TestManagerDownloadFile:
    """Test cases for the manager_download_file function in appController"""
    
    @pytest.fixture
    def app(self):
        """Create a test Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Mock app config values
        app.config['db_manager_reader'] = Mock()
        app.config['turnstile_site_key'] = 'test-site-key'
        app.config['turnstile_secret'] = 'test-secret'
        app.config['s3_client'] = Mock()
        app.config['kms_client'] = Mock()
        app.config['aws_s3_bucket_name'] = 'test-bucket'
        
        # Create and register blueprints for testing
        from flask import Blueprint
        
        app_blueprint = Blueprint('appRoute', __name__)
        
        @app_blueprint.route('/')
        def home():
            return "Home"
        
        @app_blueprint.route('/manager/<file_id>')
        def manager_download():
            return "Manager Download"
        
        app.register_blueprint(app_blueprint)
        
        with app.app_context():
            yield app
    
    @pytest.fixture
    def mock_db_manager(self, app):
        """Mock database manager"""
        return app.config['db_manager_reader']
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample file metadata for testing"""
        return {
            'file_name': 'manager_document.pdf',
            'user_password_hash': 'hashed_user_password_123',
            'ttl': 7,
            'status': 'Approved',
            'uploaded_by': 'manager@example.com',
            'recipients': 'user@example.com',
            'business_justification': 'Test file for manager download'
        }

    @patch('requests.post')
    def test_manager_download_file_get_request_success(self, mock_requests_post, app, mock_db_manager, sample_metadata):
        """Test successful GET request to manager download file"""
        # Mock turnstile verification (not needed for GET but included for completeness)
        mock_requests_post.return_value.json.return_value = {'success': True}
        
        with app.test_request_context('/manager/test_unique_id_123', method='GET'):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            with patch('download.controllers.appController.render_template') as mock_render:
                mock_render.return_value = "Manager Password Prompt Template"
                
                result = manager_download_file('test_unique_id_123')
                
                # Assertions
                mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                mock_db_manager.is_file_valid.assert_called_once_with('test_unique_id_123')
                mock_render.assert_called_once_with(
                    'manager_password_prompt.html',
                    unique_id='test_unique_id_123',
                    filename='manager_document.pdf',
                    turnstile_site_key='test-site-key'
                )
                assert result == "Manager Password Prompt Template"

    @patch('requests.post')
    def test_manager_download_file_post_valid_password(self, mock_requests_post, app, mock_db_manager, sample_metadata):
        """Test POST request with valid manager password"""
        # Mock turnstile verification
        mock_requests_post.return_value.json.return_value = {'success': True}
        
        with app.test_request_context('/manager/test_unique_id_123', method='POST', data={
            'password': 'manager_password_123',
            'cf-turnstile-response': 'test-turnstile-token'
        }):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            mock_db_manager.get_stored_manager_password.return_value = hashlib.sha256('manager_password_123'.encode()).hexdigest()
            
            # Mock FileDecryptor
            with patch('download.controllers.appController.FileDecryptor') as mock_decryptor_class:
                mock_decryptor = Mock()
                mock_decryptor_class.return_value = mock_decryptor
                mock_response = Mock()
                mock_decryptor.decrypt_and_download_file.return_value = mock_response
                
                result = manager_download_file('test_unique_id_123')
                
                # Assertions
                mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                mock_db_manager.is_file_valid.assert_called_once_with('test_unique_id_123')
                mock_db_manager.get_stored_manager_password.assert_called_once_with('test_unique_id_123')
                mock_decryptor.validate_bucket_name.assert_called_once()
                mock_decryptor.decrypt_and_download_file.assert_called_once_with('manager_document.pdf', 'test_unique_id_123')
                assert result == mock_response

    @patch('requests.post')
    def test_manager_download_file_post_invalid_password(self, mock_requests_post, app, mock_db_manager, sample_metadata):
        """Test POST request with invalid manager password"""
        # Mock turnstile verification
        mock_requests_post.return_value.json.return_value = {'success': True}
        
        with app.test_request_context('/manager/test_unique_id_123', method='POST', data={
            'password': 'wrong_password',
            'cf-turnstile-response': 'test-turnstile-token'
        }):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            mock_db_manager.get_stored_manager_password.return_value = hashlib.sha256('correct_password'.encode()).hexdigest()
            
            with patch('download.controllers.appController.render_template') as mock_render:
                mock_render.return_value = "Manager Password Prompt Template"
                
                with patch('download.controllers.appController.flash') as mock_flash:
                    result = manager_download_file('test_unique_id_123')
                    
                    # Assertions
                    mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                    mock_db_manager.is_file_valid.assert_called_once_with('test_unique_id_123')
                    mock_db_manager.get_stored_manager_password.assert_called_once_with('test_unique_id_123')
                    mock_flash.assert_called_once_with('Invalid password. Please try again.', 'error')
                    mock_render.assert_called_once_with(
                        'manager_password_prompt.html',
                        unique_id='test_unique_id_123',
                        filename='manager_document.pdf',
                        turnstile_site_key='test-site-key'
                    )

    @patch('requests.post')
    def test_manager_download_file_file_not_found(self, mock_requests_post, app, mock_db_manager):
        """Test when file metadata is not found"""
        # Mock turnstile verification
        mock_requests_post.return_value.json.return_value = {'success': True}
        
        with app.test_request_context('/manager/test_unique_id_123', method='GET'):
            # Mock database to return None (file not found)
            mock_db_manager.get_file_name.return_value = None
            
            with patch('download.controllers.appController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('download.controllers.appController.flash') as mock_flash:
                    result = manager_download_file('test_unique_id_123')
                    
                    # Assertions
                    mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                    mock_flash.assert_called_once_with('File not found.', 'error')
                    mock_redirect.assert_called_once()

    @patch('requests.post')
    def test_manager_download_file_file_expired(self, mock_requests_post, app, mock_db_manager, sample_metadata):
        """Test when file has expired"""
        # Mock turnstile verification
        mock_requests_post.return_value.json.return_value = {'success': True}
        
        with app.test_request_context('/manager/test_unique_id_123', method='GET'):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = False  # File expired
            
            with patch('download.controllers.appController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('download.controllers.appController.flash') as mock_flash:
                    result = manager_download_file('test_unique_id_123')
                    
                    # Assertions
                    mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                    mock_db_manager.is_file_valid.assert_called_once_with('test_unique_id_123')
                    mock_flash.assert_called_once_with('This file has expired.', 'error')
                    mock_redirect.assert_called_once()

    @patch('requests.post')
    def test_manager_download_file_aws_error(self, mock_requests_post, app, mock_db_manager, sample_metadata):
        """Test AWS error handling during file processing"""
        # Mock turnstile verification
        mock_requests_post.return_value.json.return_value = {'success': True}
        
        with app.test_request_context('/manager/test_unique_id_123', method='POST', data={
            'password': 'manager_password_123',
            'cf-turnstile-response': 'test-turnstile-token'
        }):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            mock_db_manager.get_stored_manager_password.return_value = hashlib.sha256('manager_password_123'.encode()).hexdigest()
            
            # Mock FileDecryptor to raise an exception
            with patch('download.controllers.appController.FileDecryptor') as mock_decryptor_class:
                mock_decryptor = Mock()
                mock_decryptor_class.return_value = mock_decryptor
                mock_decryptor.validate_bucket_name.side_effect = Exception("AWS connection error")
                
                with patch('download.controllers.appController.render_template') as mock_render:
                    mock_render.return_value = "Manager Password Prompt Template"
                    
                    with patch('download.controllers.appController.flash') as mock_flash:
                        result = manager_download_file('test_unique_id_123')
                        
                        # Assertions
                        mock_flash.assert_called_once_with('Error: AWS connection error', 'error')
                        mock_render.assert_called_once_with(
                            'manager_password_prompt.html',
                            unique_id='test_unique_id_123',
                            filename='manager_document.pdf',
                            turnstile_site_key='test-site-key'
                        )


class TestUserDownloadFile:
    """Test cases for the user_download_file function in appController"""
    
    @pytest.fixture
    def app(self):
        """Create a test Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Mock app config values
        app.config['db_manager_reader'] = Mock()
        app.config['turnstile_site_key'] = 'test-site-key'
        app.config['turnstile_secret'] = 'test-secret'
        app.config['s3_client'] = Mock()
        app.config['kms_client'] = Mock()
        app.config['aws_s3_bucket_name'] = 'test-bucket'
        
        # Create and register blueprints for testing
        from flask import Blueprint
        
        app_blueprint = Blueprint('appRoute', __name__)
        
        @app_blueprint.route('/')
        def home():
            return "Home"
        
        @app_blueprint.route('/user/<file_id>')
        def user_download():
            return "User Download"
        
        @app_blueprint.route('/user/<unique_id>')
        def user_download_file(unique_id):
            return f"User Download File {unique_id}"
        
        app.register_blueprint(app_blueprint)
        
        with app.app_context():
            yield app
    
    @pytest.fixture
    def mock_db_manager(self, app):
        """Mock database manager"""
        return app.config['db_manager_reader']
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample file metadata for testing"""
        password = "user_password_123"
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        return {
            'file_name': 'user_document.pdf',
            'user_password_hash': password_hash,
            'ttl': 7,
            'status': 'Approved',
            'uploaded_by': 'manager@example.com',
            'recipients': 'user@example.com',
            'business_justification': 'Test file for user download'
        }

    def test_user_download_file_get_request_success(self, app, mock_db_manager, sample_metadata):
        """Test successful GET request to user download file"""
        with app.test_request_context('/user/test_unique_id_123', method='GET'):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            with patch('download.controllers.appController.render_template') as mock_render:
                mock_render.return_value = "Password Prompt Template"
                
                result = user_download_file('test_unique_id_123')
                
                # Assertions
                mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                mock_db_manager.is_file_valid.assert_called_once_with('test_unique_id_123')
                mock_render.assert_called_once_with(
                    'password_prompt.html',
                    unique_id='test_unique_id_123',
                    filename='user_document.pdf',
                    turnstile_site_key='test-site-key'
                )
                assert result == "Password Prompt Template"

    def test_user_download_file_post_valid_password(self, app, mock_db_manager, sample_metadata):
        """Test POST request with valid user password"""
        with app.test_request_context('/user/test_unique_id_123', method='POST', data={
            'password': 'user_password_123'
        }):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            # Mock FileDecryptor
            with patch('download.controllers.appController.FileDecryptor') as mock_decryptor_class:
                mock_decryptor = Mock()
                mock_decryptor_class.return_value = mock_decryptor
                mock_response = Mock()
                mock_decryptor.decrypt_and_download_file.return_value = mock_response
                
                result = user_download_file('test_unique_id_123')
                
                # Assertions
                mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                mock_db_manager.is_file_valid.assert_called_once_with('test_unique_id_123')
                mock_decryptor.validate_bucket_name.assert_called_once()
                mock_decryptor.decrypt_and_download_file.assert_called_once_with('user_document.pdf', 'test_unique_id_123')
                assert result == mock_response

    def test_user_download_file_post_invalid_password(self, app, mock_db_manager, sample_metadata):
        """Test POST request with invalid user password"""
        with app.test_request_context('/user/test_unique_id_123', method='POST', data={
            'password': 'wrong_password'
        }):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            with patch('download.controllers.appController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('download.controllers.appController.flash') as mock_flash:
                    result = user_download_file('test_unique_id_123')
                    
                    # Assertions
                    mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                    mock_db_manager.is_file_valid.assert_called_once_with('test_unique_id_123')
                    mock_flash.assert_called_once_with('Invalid password. Please try again.', 'error')
                    mock_redirect.assert_called_once()

    def test_user_download_file_file_not_found(self, app, mock_db_manager):
        """Test when file metadata is not found"""
        with app.test_request_context('/user/test_unique_id_123', method='GET'):
            # Mock database to return None (file not found)
            mock_db_manager.get_file_name.return_value = None
            
            with patch('download.controllers.appController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('download.controllers.appController.flash') as mock_flash:
                    result = user_download_file('test_unique_id_123')
                    
                    # Assertions
                    mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                    mock_flash.assert_called_once_with('File not found.', 'error')
                    mock_redirect.assert_called_once()

    def test_user_download_file_file_expired(self, app, mock_db_manager, sample_metadata):
        """Test when file has expired"""
        with app.test_request_context('/user/test_unique_id_123', method='GET'):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = False  # File expired
            
            with patch('download.controllers.appController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                with patch('download.controllers.appController.flash') as mock_flash:
                    result = user_download_file('test_unique_id_123')
                    
                    # Assertions
                    mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                    mock_db_manager.is_file_valid.assert_called_once_with('test_unique_id_123')
                    mock_flash.assert_called_once_with('This file has expired.', 'error')
                    mock_redirect.assert_called_once()

    def test_user_download_file_aws_error(self, app, mock_db_manager, sample_metadata):
        """Test AWS error handling during file processing"""
        with app.test_request_context('/user/test_unique_id_123', method='POST', data={
            'password': 'user_password_123'
        }):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            # Mock FileDecryptor to raise an exception
            with patch('download.controllers.appController.FileDecryptor') as mock_decryptor_class:
                mock_decryptor = Mock()
                mock_decryptor_class.return_value = mock_decryptor
                mock_decryptor.validate_bucket_name.side_effect = Exception("AWS connection error")
                
                with patch('download.controllers.appController.redirect') as mock_redirect:
                    mock_redirect.return_value = Mock()
                    
                    with patch('download.controllers.appController.flash') as mock_flash:
                        result = user_download_file('test_unique_id_123')
                        
                        # Assertions
                        mock_flash.assert_called_once_with('An error occurred while processing the file. Please try again.', 'error')
                        mock_redirect.assert_called_once()

    def test_user_download_file_missing_password_hash(self, app, mock_db_manager):
        """Test when user_password_hash is missing from metadata"""
        with app.test_request_context('/user/test_unique_id_123', method='GET'):
            # Mock metadata without user_password_hash
            incomplete_metadata = {
                'file_name': 'user_document.pdf',
                'ttl': 7,
                'status': 'Approved'
                # Missing 'user_password_hash'
            }
            mock_db_manager.get_file_name.return_value = incomplete_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            with patch('download.controllers.appController.render_template') as mock_render:
                mock_render.return_value = "Password Prompt Template"
                
                result = user_download_file('test_unique_id_123')
                
                # Should handle missing user_password_hash gracefully
                mock_render.assert_called_once_with(
                    'password_prompt.html',
                    unique_id='test_unique_id_123',
                    filename='user_document.pdf',
                    turnstile_site_key='test-site-key'
                )

    def test_user_download_file_session_clearing(self, app, mock_db_manager, sample_metadata):
        """Test that session flash messages are cleared"""
        with app.test_request_context('/user/test_unique_id_123', method='GET'):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            with patch('download.controllers.appController.render_template') as mock_render:
                mock_render.return_value = "Password Prompt Template"
                
                # Use Flask's session object directly instead of patching
                from flask import session
                session['_flashes'] = [('error', 'Test flash message')]  # Set up test data
                
                result = user_download_file('test_unique_id_123')
                
                # Verify session flash messages were cleared
                assert '_flashes' not in session or len(session.get('_flashes', [])) == 0

    def test_user_download_file_logging_verification(self, app, mock_db_manager, sample_metadata):
        """Test that appropriate logging occurs"""
        with app.test_request_context('/user/test_unique_id_123', method='GET'):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            with patch('download.controllers.appController.render_template') as mock_render:
                mock_render.return_value = "Password Prompt Template"
                
                with patch('download.controllers.appController.logger') as mock_logger:
                    result = user_download_file('test_unique_id_123')
                    
                    # Verify logging was called
                    mock_logger.debug.assert_called()
