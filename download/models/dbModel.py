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

class DbManager:
    '''Main model class that combines FileModel functionality'''
    
    def __init__(self, host, user, password, database, port=3306, ssl=None):
        self.file_model = FileModel(host, user, password, database, port, ssl)

    def get_db_connection(self):
        '''Create a new database connection for each query.'''
        return self.file_model.get_db_connection()

    def is_file_valid(self, unique_id):
        return self.file_model.is_file_valid(unique_id)
    
    def get_file_name(self, unique_id):
        return self.file_model.get_file_name(unique_id)
    
    def get_stored_manager_password(self, unique_id):
        return self.file_model.get_stored_manager_password(unique_id)