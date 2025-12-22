import sys
import os

# Add the parent directory to the Python path to locate 'shared'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import hashlib
from datetime import datetime, timedelta
import pymysql
import uuid
from abc import ABC, abstractmethod

from shared.utils.logger import logger

class BaseModel(ABC):
    '''Base model class for database operations'''
    
    def __init__(self, host, user, password, database, port=3306, ssl=None):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.ssl = ssl
    
    @abstractmethod
    def get_db_connection(self):
        '''Create a new database connection for each query.'''
        pass

class FileModel(BaseModel):
    '''Model class for file metadata operations'''
    
    def __init__(self, host, user, password, database, port=3306, ssl=None):
        super().__init__(host, user, password, database, port, ssl)
    
    def get_db_connection(self):
        '''Create a new database connection for each query.'''
        try:
            connection_args = {
                "host": self.host,
                "user": self.user,
                "password": self.password,
                "db": self.database,
                "port": self.port,
                "connect_timeout": 10  # Prevent long wait on failures
            }
            if self.ssl:
                connection_args['ssl'] = self.ssl  # Add SSL if applicable

            return pymysql.connect(**connection_args)  # Always create a new connection
        except pymysql.MySQLError as e:
            logger.error(f'Error connecting to the database: {e}')
            raise
    
    def update_file_status(self, unique_id, status):
        '''Update the status of a file in the database.'''
        connection = self.get_db_connection()
        try:
            with connection.cursor() as cursor:
                query = 'UPDATE file_metadata SET status = %s WHERE unique_id = %s'
                cursor.execute(query, (status, unique_id))
                connection.commit()
                logger.debug(f'File status for {unique_id} updated to {status}.')
        except pymysql.MySQLError as e:
            logger.error(f'Error updating file status: {e}')
            raise
        finally:
            connection.close()

    def calculate_file_hash(self, file_content):
        '''Calculate a SHA-256 hash of the file content.'''
        return hashlib.sha256(file_content).hexdigest()

    def generate_unique_id(self, file_hash, ttl, filename, uploader_email):
        '''Generate a unique ID based on file hash, TTL, filename, and uploader's email.'''
        timestamp = datetime.now().isoformat()  # Include precise timestamp
        unique_string = f'{uuid.uuid4().hex}{file_hash[:10]}{ttl}{filename}{uploader_email}{timestamp}'
        return hashlib.sha256(unique_string.encode()).hexdigest()

    def store_approval_password(self, unique_id, approval_password_hash):
        '''
        Store the approval password hash for the file in the database.

        Args:
            unique_id (str): The unique identifier for the file.
            approval_password_hash (str): The hash of the approval password.
        '''
        connection = self.get_db_connection()
        try:
            with connection.cursor() as cursor:
                query = '''
                    UPDATE file_metadata
                    SET manager_password = %s
                    WHERE unique_id = %s
                '''
                cursor.execute(query, (approval_password_hash, unique_id))
            connection.commit()
            logger.debug(f'Stored approval password for unique_id: {unique_id}')
        except pymysql.MySQLError as e:
            logger.error(f'Error updating approval password: {e}')
        finally:
            connection.close()

    def store_file_metadata(self, unique_id, filename, ttl, password_hash, recipients=None, message=None, uploaded_on=None, business_justification=None, uploaded_by=None):
        '''Store file metadata in the database with duplicate entry handling.'''
        expiry_date = datetime.now() + timedelta(days=ttl)  # Calculate the expiry date based on TTL
        connection = self.get_db_connection()
        try:
            with connection.cursor() as cursor:
                query = '''
                    INSERT INTO file_metadata (file_name, unique_id, ttl, password_hash, recipients, message, expiry, status, uploaded_on, business_justification, uploaded_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, "Pending", %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        file_name = VALUES(file_name),
                        ttl = VALUES(ttl),
                        password_hash = VALUES(password_hash),
                        recipients = VALUES(recipients),
                        message = VALUES(message),
                        expiry = VALUES(expiry),
                        uploaded_on = VALUES(uploaded_on),
                        business_justification = VALUES(business_justification),
                        uploaded_by = VALUES(uploaded_by),
                        status = CASE WHEN status = "Approved" THEN "Approved" ELSE "Pending" END
                '''
                logger.debug(f'Executing query for unique_id: {unique_id} with status Pending')
                cursor.execute(query, (filename, unique_id, ttl, password_hash, recipients, message, expiry_date, uploaded_on, business_justification, uploaded_by))
            connection.commit()
            logger.debug(f'Stored/Updated file metadata for unique_id: {unique_id}, uploaded_by: {uploaded_by}')
        except pymysql.MySQLError as e:
            logger.error(f'Error inserting or updating metadata for unique_id {unique_id}: {e}')
        finally:
            connection.close()

    def is_file_valid(self, unique_id):
        '''Check if the file is valid based on unique_id.'''
        logger.debug(f'Checking validity for unique_id: {unique_id}')
        connection = self.get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT expiry FROM file_metadata WHERE unique_id = %s', (unique_id,))
                file_info = cursor.fetchone()
            
            if not file_info:
                logger.debug(f'No record found for unique_id: {unique_id}')
                return False

            expiry_time = file_info[0]
            current_time = datetime.now()

            # Check if the file has expired
            if current_time > expiry_time:
                logger.debug(f'File has expired. Expiry time: {expiry_time}, Current time: {current_time}')
                return False
            
            logger.debug(f'File is valid. Expiry time: {expiry_time}, Current time: {current_time}')
            return True
        except pymysql.MySQLError as e:
            logger.error(f'Error checking file validity: {e}')
            return False
        finally:
            connection.close()

    def get_file_name(self, unique_id):
        '''Retrieve file metadata based on the unique_id.'''
        connection = self.get_db_connection()
        try:
            logger.debug(f'Querying file metadata for unique_id: {unique_id}')
            with connection.cursor() as cursor:
                query = '''
                    SELECT file_name, uploaded_by, password_hash, user_password_hash, ttl, status, recipients, expiry, business_justification
                    FROM file_metadata
                    WHERE unique_id = %s
                '''
                cursor.execute(query, (unique_id,))
                row = cursor.fetchone()
                logger.debug(f'get_file_name result for unique_id {unique_id}: {row}')

            if not row:  # If no result, return None immediately
                return None

            return {
                'file_name': row[0],
                'uploaded_by': row[1],
                'password_hash': row[2],
                'user_password_hash': row[3],  # Add user_password_hash
                'ttl': row[4],
                'status': row[5],
                'recipients': row[6],  # Include recipients
                'expiry': row[7],      # Include expiry
                'business_justification': row[8],
            }

        except pymysql.MySQLError as e:
            logger.error(f'Error fetching file name for unique_id {unique_id}: {e}')
            return None
        finally:
            connection.close()

    def get_stored_manager_password(self, unique_id):
        '''Fetch the stored manager password for a specific file.'''
        connection = self.get_db_connection()
        try:
            with connection.cursor() as cursor:
                query = 'SELECT manager_password FROM file_metadata WHERE unique_id = %s'
                cursor.execute(query, (unique_id,))
                row = cursor.fetchone()
                if row:
                    return row[0]  # Return stored password hash
            return None
        except pymysql.MySQLError as e:
            logger.error(f'Error fetching manager password: {e}')
            return None
        finally:
            connection.close()

    def store_user_download_password(self, unique_id, password_hash):
        '''Store the hashed user password for downloading.'''
        connection = self.get_db_connection()
        try:
            with connection.cursor() as cursor:
                query = '''
                    UPDATE file_metadata
                    SET user_password_hash = %s
                    WHERE unique_id = %s
                '''
                cursor.execute(query, (password_hash, unique_id))
            connection.commit()
            logger.debug(f'Stored user-specific password hash for unique_id: {unique_id}')
        except pymysql.MySQLError as e:
            logger.error(f'Error storing user download password for unique_id {unique_id}: {e}')
        finally:
            connection.close()

    def get_file_status(self, unique_id):
        '''Retrieve the status from file_metadata based on the given unique_id.'''
        connection = self.get_db_connection()
        try:
            with connection.cursor() as cursor:
                query = 'SELECT status FROM file_metadata WHERE unique_id = %s'
                cursor.execute(query, (unique_id,))
                result = cursor.fetchone()  # This will be a tuple, e.g. (status_value,)
                return result[0] if result else None
        except pymysql.MySQLError as e:
            logger.error(f'Error fetching file status: {e}')
            return None
        finally:
            connection.close()

    def get_user_uploads_paginated(self, user_email, page, per_page):
        '''
        Fetch uploads for a single user with pagination.
        
        Args:
            user_email (str): The user's email.
            page (int): The current page number.
            per_page (int): Number of records to display per page.
        
        Returns:
            (uploads_list, total_count)
            - uploads_list: List of dictionaries with upload metadata.
            - total_count: Integer count of total matching rows for this user.
        '''
        connection = self.get_db_connection()
        offset = (page - 1) * per_page

        # We'll use MySQL's FOUND_ROWS for total row count
        sql = """
            SELECT SQL_CALC_FOUND_ROWS 
                file_name, ttl, status, uploaded_on
            FROM file_metadata
            WHERE uploaded_by = %s
            ORDER BY uploaded_on DESC
            LIMIT %s OFFSET %s
        """

        try:
            with connection.cursor() as cursor:
                # 1) Fetch the paginated rows
                cursor.execute(sql, (user_email, per_page, offset))
                rows = cursor.fetchall()

                # 2) Get the total count of matching rows
                cursor.execute('SELECT FOUND_ROWS()')
                total_count = cursor.fetchone()[0]

            # 3) Convert result into list of dictionaries, like your original code
            uploads_list = []
            for row in rows:
                # row is a tuple: (file_name, ttl, status, uploaded_on)
                uploads_list.append({
                    'file_name': row[0],
                    'ttl': row[1],
                    'status': row[2],
                    'uploaded_on': row[3].strftime('%Y-%m-%d %H:%M:%S')
                })

            return uploads_list, total_count
        except pymysql.MySQLError as e:
            logger.error(f'Error fetching user uploads (paginated): {e}')
            return [], 0
        finally:
            connection.close()

    def get_pending_approvals(self, manager_email):
        '''Retrieve all files pending approval for a specific manager.'''
        connection = self.get_db_connection()
        try:
            with connection.cursor() as cursor:
                query = '''
                    SELECT fm.file_name, fm.unique_id, fm.uploaded_by, 
                        fm.recipients, fm.business_justification, fm.uploaded_on
                    FROM file_metadata fm
                    LEFT JOIN employee_manager_details em
                    ON fm.uploaded_by = em.employee_email
                    WHERE (em.manager_email = %s OR em.manager_email IS NULL) 
                    AND fm.status = 'Pending'
                    ORDER BY fm.uploaded_on DESC
                '''
                cursor.execute(query, (manager_email,))
                approvals = cursor.fetchall()
                
                approval_list = [
                    {
                        'file_name': row[0],
                        'unique_id': row[1],
                        'uploaded_by': row[2],
                        'recipients': row[3],
                        'business_justification': row[4],
                        'uploaded_on': row[5].strftime('%Y-%m-%d %H:%M:%S'),
                    }
                    for row in approvals
                ]
                return approval_list
        except pymysql.MySQLError as e:
            logger.error(f'Error fetching pending approvals: {e}')
            return []
        finally:
            connection.close()

    def get_pending_approvals_with_search(self, manager_email, search_query, page, per_page):
        '''
        Retrieve files pending approval for a specific manager with search functionality and pagination.
        
        Args:
            manager_email (str): The manager's email address
            search_query (str): The search term to filter by uploaded_by
            page (int): The current page number
            per_page (int): Number of records per page
            
        Returns:
            tuple: (approvals_list, total_count)
        '''
        connection = self.get_db_connection()
        offset = (page - 1) * per_page
        pattern = f'%{search_query}%'
        
        try:
            with connection.cursor() as cursor:
                # Main query with pagination
                query = '''
                    SELECT fm.file_name, fm.unique_id, fm.uploaded_by, 
                           fm.recipients, fm.business_justification, fm.uploaded_on
                    FROM file_metadata fm
                    LEFT JOIN employee_manager_details em
                      ON fm.uploaded_by = em.employee_email
                    WHERE (em.manager_email = %s OR em.manager_email IS NULL)
                      AND fm.status = "Pending"
                      AND fm.uploaded_by LIKE %s
                    ORDER BY fm.uploaded_on DESC
                    LIMIT %s OFFSET %s
                '''
                cursor.execute(query, (manager_email, pattern, per_page, offset))
                results = cursor.fetchall()
                
                # Count query for total records
                count_query = '''
                    SELECT COUNT(*) 
                    FROM file_metadata fm
                    LEFT JOIN employee_manager_details em
                      ON fm.uploaded_by = em.employee_email
                    WHERE (em.manager_email = %s OR em.manager_email IS NULL)
                      AND fm.status = "Pending"
                      AND fm.uploaded_by LIKE %s
                '''
                cursor.execute(count_query, (manager_email, pattern))
                total_count = cursor.fetchone()[0]
                
                # Convert results to list of dictionaries
                approvals_list = []
                for row in results:
                    approvals_list.append({
                        'file_name': row[0],
                        'unique_id': row[1],
                        'uploaded_by': row[2],
                        'recipients': row[3],
                        'business_justification': row[4],
                        'uploaded_on': row[5].strftime('%Y-%m-%d %H:%M:%S') if row[5] else None,
                    })
                
                return approvals_list, total_count
                
        except pymysql.MySQLError as e:
            logger.error(f'Error fetching pending approvals with search: {e}')
            return [], 0
        finally:
            connection.close()

class EmployeeModel(BaseModel):
    '''Model class for employee and manager operations'''
    
    def __init__(self, host, user, password, database, port=3306, ssl=None):
        super().__init__(host, user, password, database, port, ssl)
    
    def get_db_connection(self):
        '''Create a new database connection for each query.'''
        try:
            connection_args = {
                'host': self.host,
                'user': self.user,
                'password': self.password,
                'db': self.database,
                'port': self.port,
                'connect_timeout': 10  # Prevent long wait on failures
            }
            if self.ssl:
                connection_args['ssl'] = self.ssl  # Add SSL if applicable

            return pymysql.connect(**connection_args)  # Always create a new connection
        except pymysql.MySQLError as e:
            logger.error(f'Error connecting to the database: {e}')
            raise

    def get_manager_email(self, employee_email):
        '''Retrieve the manager's email for the given employee's email.'''
        connection = self.get_db_connection()
        try:
            with connection.cursor() as cursor:
                query = '''
                    SELECT manager_email
                    FROM employee_manager_details
                    WHERE employee_email = %s
                '''
                cursor.execute(query, (employee_email,))
                row = cursor.fetchone()

            if row:
                if row[0] == 'Not Found':
                    return None
                return row[0]
            return None
        except pymysql.MySQLError as e:
            logger.error(f'Error retrieving manager email: {e}')
            return None
        finally:
            connection.close()

    def is_manager(self, email):
        '''Check if the given email belongs to a manager.'''
        connection = self.get_db_connection()
        try:
            with connection.cursor() as cursor:
                query = 'SELECT COUNT(*) FROM employee_manager_details WHERE manager_email = %s'
                cursor.execute(query, (email,))
                row = cursor.fetchone()
                return row[0] > 0  # Returns True if the email exists in the manager column
        except pymysql.MySQLError as e:
            logger.error(f'Error checking if {email} is a manager: {e}')
            return False
        finally:
            connection.close()

class DbManager:
    '''Main model class that combines FileModel and EmployeeModel functionality'''
    
    def __init__(self, host, user, password, database, port=3306, ssl=None):
        self.file_model = FileModel(host, user, password, database, port, ssl)
        self.employee_model = EmployeeModel(host, user, password, database, port, ssl)
    
    def get_db_connection(self):
        '''Create a new database connection for each query.'''
        return self.file_model.get_db_connection()
    
    # File-related methods - delegate to file_model
    def update_file_status(self, unique_id, status):
        return self.file_model.update_file_status(unique_id, status)
    
    def calculate_file_hash(self, file_content):
        return self.file_model.calculate_file_hash(file_content)
    
    def generate_unique_id(self, file_hash, ttl, filename, uploader_email):
        return self.file_model.generate_unique_id(file_hash, ttl, filename, uploader_email)
    
    def store_approval_password(self, unique_id, approval_password_hash):
        return self.file_model.store_approval_password(unique_id, approval_password_hash)
    
    def store_file_metadata(self, unique_id, filename, ttl, password_hash, recipients=None, message=None, uploaded_on=None, business_justification=None, uploaded_by=None):
        return self.file_model.store_file_metadata(unique_id, filename, ttl, password_hash, recipients, message, uploaded_on, business_justification, uploaded_by)
    
    def is_file_valid(self, unique_id):
        return self.file_model.is_file_valid(unique_id)
    
    def get_file_name(self, unique_id):
        return self.file_model.get_file_name(unique_id)
    
    def get_stored_manager_password(self, unique_id):
        return self.file_model.get_stored_manager_password(unique_id)
    
    def store_user_download_password(self, unique_id, password_hash):
        return self.file_model.store_user_download_password(unique_id, password_hash)
    
    def get_file_status(self, unique_id):
        return self.file_model.get_file_status(unique_id)
    
    def get_user_uploads_paginated(self, user_email, page, per_page):
        return self.file_model.get_user_uploads_paginated(user_email, page, per_page)
    
    def get_pending_approvals(self, manager_email):
        return self.file_model.get_pending_approvals(manager_email)
    
    def get_pending_approvals_with_search(self, manager_email, search_query, page, per_page):
        return self.file_model.get_pending_approvals_with_search(manager_email, search_query, page, per_page)
    
    # Employee-related methods - delegate to employee_model
    def get_manager_email(self, employee_email):
        return self.employee_model.get_manager_email(employee_email)
    
    def is_manager(self, email):
        return self.employee_model.is_manager(email)