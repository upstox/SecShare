"""
Admin model for database operations related to admin functionality
"""
import sys
import os

# Add the parent directory to the Python path to locate modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shared.utils.logger import logger


class AdminModel:
    """Model class for admin-related database operations"""
    
    def __init__(self, db_manager_reader, db_manager_writer):
        """
        Initialize AdminModel with database managers
        
        Args:
            db_manager_reader: Database manager for read operations
            db_manager_writer: Database manager for write operations
        """
        self.db_manager_reader = db_manager_reader
        self.db_manager_writer = db_manager_writer
    
    def get_employee_manager_details_with_search(self, search_query='', page=1, per_page=20):
        """
        Get employee manager details with optional search and pagination
        
        Args:
            search_query (str): Search term for employee email
            page (int): Page number for pagination
            per_page (int): Number of records per page
            
        Returns:
            dict: Contains results, columns, total_count, total_pages
        """
        offset = (page - 1) * per_page
        
        conn = self.db_manager_reader.get_db_connection()
        try:
            with conn.cursor() as cursor:
                if search_query:
                    pattern = f'%{search_query}%'
                    cursor.execute('SELECT COUNT(*) FROM employee_manager_details WHERE employee_email LIKE %s', (pattern,))
                    total_count = cursor.fetchone()[0]
                    cursor.execute(
                        'SELECT * FROM employee_manager_details WHERE employee_email LIKE %s ORDER BY employee_email LIMIT %s OFFSET %s',
                        (pattern, per_page, offset)
                    )
                else:
                    cursor.execute('SELECT COUNT(*) FROM employee_manager_details')
                    total_count = cursor.fetchone()[0]
                    cursor.execute(
                        'SELECT * FROM employee_manager_details ORDER BY employee_email LIMIT %s OFFSET %s',
                        (per_page, offset)
                    )
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
        finally:
            conn.close()
        
        total_pages = (total_count + per_page - 1) // per_page
        
        return {
            'results': results,
            'columns': columns,
            'total_count': total_count,
            'total_pages': total_pages
        }
    
    def get_file_metadata_with_search(self, search_query='', page=1, per_page=20):
        """
        Get file metadata with optional search and pagination
        
        Args:
            search_query (str): Search term for file name
            page (int): Page number for pagination
            per_page (int): Number of records per page
            
        Returns:
            dict: Contains results, columns, total_count, total_pages
        """
        offset = (page - 1) * per_page
        
        conn = self.db_manager_reader.get_db_connection()
        try:
            with conn.cursor() as cursor:
                if search_query:
                    pattern = f'%{search_query}%'
                    cursor.execute('SELECT COUNT(*) FROM file_metadata WHERE file_name LIKE %s', (pattern,))
                    total_count = cursor.fetchone()[0]
                    cursor.execute(
                        'SELECT * FROM file_metadata WHERE file_name LIKE %s ORDER BY uploaded_on DESC LIMIT %s OFFSET %s',
                        (pattern, per_page, offset)
                    )
                else:
                    cursor.execute('SELECT COUNT(*) FROM file_metadata')
                    total_count = cursor.fetchone()[0]
                    cursor.execute(
                        'SELECT * FROM file_metadata ORDER BY uploaded_on DESC LIMIT %s OFFSET %s',
                        (per_page, offset)
                    )
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
        finally:
            conn.close()
        
        total_pages = (total_count + per_page - 1) // per_page
        
        return {
            'results': results,
            'columns': columns,
            'total_count': total_count,
            'total_pages': total_pages
        }
    
    def get_file_metadata_archive_with_search(self, search_query='', page=1, per_page=20):
        """
        Get file metadata archive with optional search and pagination
        
        Args:
            search_query (str): Search term for file name
            page (int): Page number for pagination
            per_page (int): Number of records per page
            
        Returns:
            dict: Contains results, columns, total_count, total_pages
        """
        offset = (page - 1) * per_page
        
        conn = self.db_manager_reader.get_db_connection()
        try:
            with conn.cursor() as cursor:
                if search_query:
                    pattern = f'%{search_query}%'
                    cursor.execute('SELECT COUNT(*) FROM file_metadata_archive WHERE file_name LIKE %s', (pattern,))
                    total_count = cursor.fetchone()[0]
                    cursor.execute(
                        'SELECT * FROM file_metadata_archive WHERE file_name LIKE %s ORDER BY uploaded_on DESC LIMIT %s OFFSET %s',
                        (pattern, per_page, offset)
                    )
                else:
                    cursor.execute('SELECT COUNT(*) FROM file_metadata_archive')
                    total_count = cursor.fetchone()[0]
                    cursor.execute(
                        'SELECT * FROM file_metadata_archive ORDER BY uploaded_on DESC LIMIT %s OFFSET %s',
                        (per_page, offset)
                    )
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
        finally:
            conn.close()
        
        total_pages = (total_count + per_page - 1) // per_page
        
        return {
            'results': results,
            'columns': columns,
            'total_count': total_count,
            'total_pages': total_pages
        }
    
    def check_employee_exists(self, employee_email):
        """
        Check if an employee exists in the database
        
        Args:
            employee_email (str): Employee email to check
            
        Returns:
            bool: True if employee exists, False otherwise
        """
        conn = self.db_manager_reader.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1 FROM employee_manager_details WHERE employee_email = %s', (employee_email,))
                return cursor.fetchone() is not None
        finally:
            conn.close()
    
    def update_manager_email(self, employee_email, new_manager_email, admin_user):
        """
        Update manager email for a given employee
        
        Args:
            employee_email (str): Employee email
            new_manager_email (str): New manager email
            admin_user (str): Admin user performing the update
            
        Returns:
            dict: Result with success status and message
        """
        conn = self.db_manager_writer.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Check if the employee exists
                cursor.execute('SELECT 1 FROM employee_manager_details WHERE employee_email = %s', (employee_email,))
                if not cursor.fetchone():
                    return {
                        'success': False,
                        'message': 'Employee not found.',
                        'error_type': 'not_found'
                    }
                
                # Update the manager email
                query = 'UPDATE employee_manager_details SET manager_email = %s WHERE employee_email = %s'
                cursor.execute(query, (new_manager_email, employee_email))
            conn.commit()
            
            logger.info('Manager email for %s updated to %s by admin %s', 
                       employee_email, new_manager_email, admin_user)
            
            return {
                'success': True,
                'message': 'Manager email updated successfully.',
                'error_type': None
            }
            
        except Exception as e:
            conn.rollback()
            logger.error('Error updating manager email for %s: %s', employee_email, e)
            return {
                'success': False,
                'message': f'Error updating manager email: {e}',
                'error_type': 'database_error'
            }
        finally:
            conn.close()
