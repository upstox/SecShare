"""
Shared test utilities for download application tests
"""
from unittest.mock import Mock
import sys

# Mock Crypto module before importing anything that uses it
sys.modules['Crypto'] = Mock()
sys.modules['Crypto.Cipher'] = Mock()
sys.modules['Crypto.Cipher.AES'] = Mock()
sys.modules['Crypto.Util.Padding'] = Mock()

# Mock other potential missing modules
sys.modules['botocore'] = Mock()
sys.modules['botocore.exceptions'] = Mock()
sys.modules['botocore.client'] = Mock()

# Create proper exception classes for mocking
class MockNoCredentialsError(Exception):
    pass

class MockClientError(Exception):
    pass

# Add them to the botocore.exceptions module
sys.modules['botocore.exceptions'].NoCredentialsError = MockNoCredentialsError
sys.modules['botocore.exceptions'].ClientError = MockClientError
