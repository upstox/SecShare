import pytest
import hashlib
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, url_for
from werkzeug.datastructures import MultiDict

import sys
import os

# Add the parent directory to the Python path to locate modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import shared test utilities
from .test_utils import MockNoCredentialsError, MockClientError

from download.controllers.apiController import verify_password


class TestVerifyPassword:
    """Test cases for the verify_password function in apiController"""
    
    @pytest.fixture
    def app(self):
        """Create a test Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Mock app config values
        app.config['db_manager_reader'] = Mock()
        app.config['s3_client'] = Mock()
        app.config['kms_client'] = Mock()
        app.config['aws_s3_bucket_name'] = 'test-bucket'
        app.config['turnstile_secret'] = 'test-secret'
        
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
        def download_file(unique_id):
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
        password = "test_password_123"
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        return {
            'file_name': 'test_file.pdf',
            'user_password_hash': password_hash,
            'ttl': 7,
            'status': 'Approved',
            'uploaded_by': 'test@example.com',
            'recipients': 'user@example.com',
            'business_justification': 'Test file for unit testing'
        }
    
    @pytest.fixture
    def valid_form_data(self):
        """Valid form data for testing"""
        return {
            'unique_id': 'test_unique_id_123',
            'filename': 'test_file.pdf',
            'password': 'test_password_123',
            'cf-turnstile-response': 'test-turnstile-token'
        }

    @patch('requests.post')
    def test_verify_password_success(self, mock_requests_post, app, mock_db_manager, sample_metadata, valid_form_data):
        """Test successful password verification and file download"""
        # Mock turnstile verification
        mock_requests_post.return_value.json.return_value = {'success': True}
        
        with app.test_request_context('/api/verify-password', method='POST', data=valid_form_data):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            # Mock FileDecryptor
            with patch('download.controllers.apiController.FileDecryptor') as mock_decryptor_class:
                mock_decryptor = Mock()
                mock_decryptor_class.return_value = mock_decryptor
                mock_decryptor.validate_bucket_name.return_value = True
                
                # Mock successful file download response
                mock_response = Mock()
                mock_response.status_code = 200
                mock_decryptor.decrypt_and_download_file.return_value = mock_response
                
                # Call the function
                result = verify_password()
                
                # Assertions
                mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                mock_db_manager.is_file_valid.assert_called_once_with('test_unique_id_123')
                mock_decryptor.validate_bucket_name.assert_called_once()
                mock_decryptor.decrypt_and_download_file.assert_called_once_with('test_file.pdf', 'test_unique_id_123')
                
                # Should return the mock response
                assert result == mock_response

    @patch('requests.post')
    def test_verify_password_file_not_found(self, mock_requests_post, app, mock_db_manager, valid_form_data):
        """Test when file metadata is not found"""
        # Mock turnstile verification
        mock_requests_post.return_value.json.return_value = {'success': True}
        
        with app.test_request_context('/api/verify-password', method='POST', data=valid_form_data):
            # Mock database to return None (file not found)
            mock_db_manager.get_file_name.return_value = None
            
            with patch('download.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                result = verify_password()
                
                # Assertions
                mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                mock_redirect.assert_called_once()
                # Should not call is_file_valid if file not found
                mock_db_manager.is_file_valid.assert_not_called()

    @patch('requests.post')
    def test_verify_password_file_expired(self, mock_requests_post, app, mock_db_manager, sample_metadata, valid_form_data):
        """Test when file has expired"""
        # Mock turnstile verification
        mock_requests_post.return_value.json.return_value = {'success': True}
        
        with app.test_request_context('/api/verify-password', method='POST', data=valid_form_data):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = False  # File expired
            
            with patch('download.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                result = verify_password()
                
                # Assertions
                mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                mock_db_manager.is_file_valid.assert_called_once_with('test_unique_id_123')
                mock_redirect.assert_called_once()

    @patch('requests.post')
    def test_verify_password_pending_approval(self, mock_requests_post, app, mock_db_manager, valid_form_data):
        """Test when file is pending manager approval"""
        with app.test_request_context('/api/verify-password', method='POST', data=valid_form_data):
            # Create metadata with pending status
            pending_metadata = {
                'file_name': 'test_file.pdf',
                'user_password_hash': hashlib.sha256('test_password_123'.encode()).hexdigest(),
                'ttl': 7,
                'status': 'Pending',  # Pending approval
                'uploaded_by': 'test@example.com'
            }
            
            mock_db_manager.get_file_name.return_value = pending_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            with patch('download.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                result = verify_password()
                
                # Assertions
                mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                mock_db_manager.is_file_valid.assert_called_once_with('test_unique_id_123')
                mock_redirect.assert_called_once()

    @patch('requests.post')
    def test_verify_password_invalid_password(self, mock_requests_post, app, mock_db_manager, sample_metadata):
        """Test when password is incorrect"""
        # Mock turnstile verification
        mock_requests_post.return_value.json.return_value = {'success': True}
        
        # Create form data with wrong password
        invalid_form_data = {
            'unique_id': 'test_unique_id_123',
            'filename': 'test_file.pdf',
            'password': 'wrong_password',  # Wrong password
            'cf-turnstile-response': 'test-turnstile-token'
        }
        
        with app.test_request_context('/api/verify-password', method='POST', data=invalid_form_data):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            with patch('download.controllers.apiController.redirect') as mock_redirect:
                mock_redirect.return_value = Mock()
                
                result = verify_password()
                
                # Assertions
                mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                mock_db_manager.is_file_valid.assert_called_once_with('test_unique_id_123')
                mock_redirect.assert_called_once()

    @patch('requests.post')
    def test_verify_password_aws_error(self, mock_requests_post, app, mock_db_manager, sample_metadata, valid_form_data):
        """Test when AWS S3/KMS operations fail"""
        with app.test_request_context('/api/verify-password', method='POST', data=valid_form_data):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            # Mock FileDecryptor to raise AWS error
            with patch('download.controllers.apiController.FileDecryptor') as mock_decryptor_class:
                mock_decryptor = Mock()
                mock_decryptor_class.return_value = mock_decryptor
                mock_decryptor.validate_bucket_name.return_value = True
                
                # Mock AWS error
                from botocore.exceptions import NoCredentialsError
                mock_decryptor.decrypt_and_download_file.side_effect = NoCredentialsError()
                
                with patch('download.controllers.apiController.redirect') as mock_redirect:
                    mock_redirect.return_value = Mock()
                    
                    result = verify_password()
                    
                    # Assertions
                    mock_db_manager.get_file_name.assert_called_once_with('test_unique_id_123')
                    mock_db_manager.is_file_valid.assert_called_once_with('test_unique_id_123')
                    mock_decryptor.validate_bucket_name.assert_called_once()
                    mock_decryptor.decrypt_and_download_file.assert_called_once_with('test_file.pdf', 'test_unique_id_123')
                    mock_redirect.assert_called_once()

    @patch('requests.post')
    def test_verify_password_missing_form_data(self, mock_requests_post, app, mock_db_manager):
        """Test when required form data is missing"""
        # Mock turnstile verification
        mock_requests_post.return_value.json.return_value = {'success': True}
        
        # Test with missing unique_id (but include turnstile token to pass decorator)
        with app.test_request_context('/api/verify-password', method='POST', data={
            'password': 'test',
            'cf-turnstile-response': 'test-turnstile-token'
        }):
            with pytest.raises(KeyError):
                verify_password()

    @patch('requests.post')
    def test_verify_password_different_status_cases(self, mock_requests_post, app, mock_db_manager, valid_form_data):
        """Test various status cases (case insensitive)"""
        test_cases = [
            ('approved', True),   # Should work
            ('APPROVED', True),   # Should work (uppercase)
            ('Approved', True),   # Should work (mixed case)
            ('pending', False),   # Should fail
            ('rejected', False),  # Should fail
            ('', False),          # Should fail (empty status)
        ]
        
        for status, should_succeed in test_cases:
            with app.test_request_context('/api/verify-password', method='POST', data=valid_form_data):
                # Create metadata with specific status
                test_metadata = {
                    'file_name': 'test_file.pdf',
                    'user_password_hash': hashlib.sha256('test_password_123'.encode()).hexdigest(),
                    'ttl': 7,
                    'status': status,
                    'uploaded_by': 'test@example.com'
                }
                
                mock_db_manager.get_file_name.return_value = test_metadata
                mock_db_manager.is_file_valid.return_value = True
                
                if should_succeed:
                    # Mock successful download
                    with patch('download.controllers.apiController.FileDecryptor') as mock_decryptor_class:
                        mock_decryptor = Mock()
                        mock_decryptor_class.return_value = mock_decryptor
                        mock_decryptor.validate_bucket_name.return_value = True
                        mock_response = Mock()
                        mock_decryptor.decrypt_and_download_file.return_value = mock_response
                        
                        result = verify_password()
                        assert result == mock_response
                else:
                    # Should redirect due to status check
                    with patch('download.controllers.apiController.redirect') as mock_redirect:
                        mock_redirect.return_value = Mock()
                        result = verify_password()
                        mock_redirect.assert_called_once()

    @patch('requests.post')
    def test_verify_password_bucket_validation_error(self, mock_requests_post, app, mock_db_manager, sample_metadata, valid_form_data):
        """Test when bucket name validation fails"""
        with app.test_request_context('/api/verify-password', method='POST', data=valid_form_data):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            # Mock FileDecryptor with invalid bucket
            with patch('download.controllers.apiController.FileDecryptor') as mock_decryptor_class:
                mock_decryptor = Mock()
                mock_decryptor_class.return_value = mock_decryptor
                mock_decryptor.validate_bucket_name.side_effect = MockNoCredentialsError("Invalid bucket name")
                
                with patch('download.controllers.apiController.redirect') as mock_redirect:
                    mock_redirect.return_value = Mock()
                    
                    result = verify_password()
                    
                    # Should handle the error and redirect
                    mock_redirect.assert_called_once()

    @patch('requests.post')
    def test_verify_password_logging_verification(self, mock_requests_post, app, mock_db_manager, sample_metadata, valid_form_data):
        """Test that appropriate logging occurs"""
        with app.test_request_context('/api/verify-password', method='POST', data=valid_form_data):
            # Mock database responses
            mock_db_manager.get_file_name.return_value = sample_metadata
            mock_db_manager.is_file_valid.return_value = True
            
            # Mock FileDecryptor
            with patch('download.controllers.apiController.FileDecryptor') as mock_decryptor_class:
                mock_decryptor = Mock()
                mock_decryptor_class.return_value = mock_decryptor
                mock_decryptor.validate_bucket_name.return_value = True
                mock_response = Mock()
                mock_decryptor.decrypt_and_download_file.return_value = mock_response
                
                # Mock logger to verify logging calls
                with patch('download.controllers.apiController.logger') as mock_logger:
                    result = verify_password()
                    
                    # Verify that appropriate logging occurred
                    mock_logger.debug.assert_called()
                    # Should log successful password match
                    assert any('Password matched' in str(call) for call in mock_logger.debug.call_args_list)


if __name__ == '__main__':
    pytest.main([__file__])
