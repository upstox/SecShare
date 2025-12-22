import sys
import os

# Add the parent directory to the Python path to locate 'shared'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shared.utils.logger import logger
from flask import request, Response, current_app

class CookieHandler:
    def __init__(self):
        # Get the serializer from the app config
        self.serializer = current_app.config['serializer']

    def set_cookie(self, response: Response, key: str, value: str, max_age: int = 3600):
        """Set a secure, HTTP-only cookie."""
        # Serialize the value
        value_signed = self.serializer.dumps(value)
        response.set_cookie(
            key,
            value_signed,
            httponly=True,
            secure=True,
            samesite='None',  # Use 'None' to allow cross-site usage
            max_age=max_age,
            path='/'  # Ensure the cookie is sent on all paths
        )
        logger.debug('Cookie set for user. Domain: %s', response.headers.get('Set-Cookie'))

    def get_cookie(self, key: str):
        """Retrieve and decode a cookie from the request."""
        # Get the value from the request
        value_signed = request.cookies.get(key)
        if not value_signed:
            return None
        # Deserialize the value
        try:
            return self.serializer.loads(value_signed, max_age=3600)
        except Exception as e:
            logger.debug('Cookie decode error: %s', e)
            return None