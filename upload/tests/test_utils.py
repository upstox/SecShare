"""
Shared test utilities for upload tests
"""
import sys
import os

# Mock exception classes for testing
class MockNoCredentialsError(Exception):
    """Mock AWS NoCredentialsError for testing"""
    pass

class MockClientError(Exception):
    """Mock AWS ClientError for testing"""
    pass

# Mock database connection and cursor
class MockCursor:
    def __init__(self):
        self.execute_calls = []
        self.fetchone_result = None
        self.fetchall_result = []
        self.description = [('column1',), ('column2',)]
    
    def execute(self, query, params=None):
        self.execute_calls.append((query, params))
    
    def fetchone(self):
        return self.fetchone_result
    
    def fetchall(self):
        return self.fetchall_result
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class MockConnection:
    def __init__(self):
        self.cursor_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0
        self.close_calls = 0
    
    def cursor(self):
        self.cursor_calls += 1
        return MockCursor()
    
    def commit(self):
        self.commit_calls += 1
    
    def rollback(self):
        self.rollback_calls += 1
    
    def close(self):
        self.close_calls += 1

class MockDbManager:
    def __init__(self):
        self.connection = MockConnection()
        # Mock return values for API controller methods
        self._file_status = 'Pending'
        self._manager_email = 'manager@example.com'
        self._stored_password = None
        self._file_metadata = None
        self._is_file_valid = True
    
    def get_db_connection(self):
        return self.connection
    
    # Methods used by API controller
    def get_file_status(self, unique_id):
        return self._file_status
    
    def get_manager_email(self, username):
        return self._manager_email
    
    def get_stored_manager_password(self, unique_id):
        return self._stored_password
    
    def get_file_name(self, unique_id):
        return self._file_metadata
    
    def is_file_valid(self, unique_id):
        return self._is_file_valid
    
    def update_file_status(self, unique_id, status):
        self._file_status = status
    
    def store_user_download_password(self, unique_id, password_hash):
        pass
    
    def generate_unique_id(self, file_hash, ttl, filename, username):
        return 'test_unique_id'
    
    def store_file_metadata(self, unique_id, filename, ttl, password_hash, recipients, message, uploaded_on, business_justification, uploaded_by):
        pass
    
    def store_approval_password(self, unique_id, password_hash):
        pass


class MockAdminModel:
    """Mock AdminModel for testing"""
    
    def __init__(self, db_manager_reader, db_manager_writer):
        self.db_manager_reader = db_manager_reader
        self.db_manager_writer = db_manager_writer
        # Mock return values
        self._employee_data = {
            'results': [('employee1@example.com', 'manager1@example.com')],
            'columns': ['employee_email', 'manager_email'],
            'total_count': 1,
            'total_pages': 1
        }
        self._file_metadata_data = {
            'results': [('file1.pdf', '2023-01-01', 'user1@example.com')],
            'columns': ['file_name', 'uploaded_on', 'uploaded_by'],
            'total_count': 1,
            'total_pages': 1
        }
        self._file_metadata_archive_data = {
            'results': [('archived_file1.pdf', '2022-12-01', 'user1@example.com')],
            'columns': ['file_name', 'uploaded_on', 'uploaded_by'],
            'total_count': 1,
            'total_pages': 1
        }
        self._employee_exists = True
        self._update_result = {'success': True, 'message': 'Manager email updated successfully.', 'error_type': None}
    
    def get_employee_manager_details_with_search(self, search_query='', page=1, per_page=20):
        return self._employee_data
    
    def get_file_metadata_with_search(self, search_query='', page=1, per_page=20):
        return self._file_metadata_data
    
    def get_file_metadata_archive_with_search(self, search_query='', page=1, per_page=20):
        return self._file_metadata_archive_data
    
    def check_employee_exists(self, employee_email):
        return self._employee_exists
    
    def update_manager_email(self, employee_email, new_manager_email, admin_user):
        return self._update_result
