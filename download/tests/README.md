# Download API Controller Tests

This directory contains comprehensive test cases for the download API controller, specifically for the `verify_password` function.

## Test Coverage

The test suite covers the following scenarios:

### ✅ **Success Cases**
- **Successful password verification and file download**
- **Valid file with correct password and approved status**

### ❌ **Error Cases**
- **File not found** - When metadata doesn't exist
- **File expired** - When file has passed its TTL
- **Pending approval** - When file status is not "Approved"
- **Invalid password** - When password doesn't match stored hash
- **AWS errors** - When S3/KMS operations fail
- **Missing form data** - When required fields are missing
- **Bucket validation errors** - When S3 bucket configuration is invalid

### 🔍 **Edge Cases**
- **Case insensitive status checking** - Tests "approved", "APPROVED", "Approved"
- **Various status values** - Tests pending, rejected, empty status
- **Logging verification** - Ensures appropriate logging occurs

## Test Structure

```
download/tests/
├── __init__.py                 # Test package initialization
├── test_api_controller.py      # Main test file
├── requirements-test.txt       # Test dependencies
├── pytest.ini                 # Pytest configuration
├── run_tests.py               # Test runner script
└── README.md                  # This file
```

## Setup

### 1. Install Test Dependencies

#### Option A: Minimal dependencies (recommended for quick testing)
```bash
pip install -r download/tests/requirements-minimal.txt
```

**Note:** The minimal requirements now include `pycryptodome` to resolve the `Crypto` module import issue.

#### Option B: Full dependencies (if you have all project dependencies installed)
```bash
pip install -r download/tests/requirements-test.txt
```

### 2. Run Tests

#### Option 1: Using the test runner script (recommended)
```bash
cd /path/to/secshare-file-sharing-tool
python download/tests/run_tests.py
```

#### Option 2: Using pytest directly with simple tests
```bash
cd /path/to/secshare-file-sharing-tool
python -m pytest download/tests/test_api_controller_simple.py -v
```

#### Option 3: Using pytest directly with full tests (requires all dependencies)
```bash
cd /path/to/secshare-file-sharing-tool
python -m pytest download/tests/test_api_controller.py -v
```

## Test Files

### `test_api_controller_simple.py` (Recommended)
- **Simplified test approach** that avoids complex import dependencies
- **Mocks all external modules** to prevent import errors
- **Focuses on core logic testing** without requiring full project setup
- **Works with minimal dependencies** (just pytest and pytest-mock)

### `test_api_controller.py` (Full Tests)
- **Comprehensive test suite** with full integration testing
- **Requires all project dependencies** to be installed
- **Tests actual imports and module interactions**
- **More realistic testing environment** but harder to set up

## Test Fixtures

The test suite uses several fixtures to provide consistent test data:

- **`app`** - Flask test application with mocked configuration
- **`client`** - Test client for making requests
- **`mock_db_manager`** - Mocked database manager
- **`sample_metadata`** - Sample file metadata with valid password hash
- **`valid_form_data`** - Valid form data for testing

## Mocking Strategy

The tests use comprehensive mocking to isolate the function under test:

- **Database operations** - Mocked `db_manager_reader`
- **AWS services** - Mocked S3 and KMS clients
- **File decryption** - Mocked `FileDecryptor` class
- **Flask redirects** - Mocked redirect responses
- **Logging** - Mocked logger for verification

## Example Test Output

```
download/tests/test_api_controller.py::TestVerifyPassword::test_verify_password_success PASSED
download/tests/test_api_controller.py::TestVerifyPassword::test_verify_password_file_not_found PASSED
download/tests/test_api_controller.py::TestVerifyPassword::test_verify_password_file_expired PASSED
download/tests/test_api_controller.py::TestVerifyPassword::test_verify_password_pending_approval PASSED
download/tests/test_api_controller.py::TestVerifyPassword::test_verify_password_invalid_password PASSED
download/tests/test_api_controller.py::TestVerifyPassword::test_verify_password_aws_error PASSED
download/tests/test_api_controller.py::TestVerifyPassword::test_verify_password_missing_form_data PASSED
download/tests/test_api_controller.py::TestVerifyPassword::test_verify_password_different_status_cases PASSED
download/tests/test_api_controller.py::TestVerifyPassword::test_verify_password_bucket_validation_error PASSED
download/tests/test_api_controller.py::TestVerifyPassword::test_verify_password_logging_verification PASSED

========================= 10 passed in 0.15s =========================
```

## Adding New Tests

To add new test cases:

1. Add a new test method to the `TestVerifyPassword` class
2. Use the existing fixtures or create new ones as needed
3. Follow the naming convention: `test_verify_password_<scenario>`
4. Include proper assertions and mocking
5. Update this README if adding new test categories

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Run Download API Tests
  run: |
    pip install -r download/tests/requirements-test.txt
    python download/tests/run_tests.py
```
