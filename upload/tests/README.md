# Upload Application Tests

This directory contains comprehensive test cases for the upload application's `adminController.py` functions.

## Test Coverage

### Functions Tested

1. **`is_admin()`** - Helper function to check admin access
2. **`home()`** - Admin home page with authorization check
3. **`employee_manager_details()`** - View employee-manager relationships with pagination and search
4. **`file_metadata()`** - View file metadata with pagination and search
5. **`file_metadata_archive()`** - View archived file metadata with pagination and search
6. **`update_manager_email()`** - Update manager email for employees

### Test Scenarios Covered

#### Authorization Tests
- ✅ Valid admin access
- ✅ Unauthorized access attempts
- ✅ Case-insensitive email matching
- ✅ Email validation with spaces

#### Database Operations
- ✅ Successful database queries
- ✅ Search functionality with LIKE patterns
- ✅ Pagination handling
- ✅ Invalid page parameter handling
- ✅ Database connection errors
- ✅ Transaction rollback on errors

#### Form Validation
- ✅ Valid email format validation
- ✅ Missing required fields
- ✅ Invalid email format rejection
- ✅ Employee existence verification

#### Error Handling
- ✅ Database connection failures
- ✅ SQL execution errors
- ✅ Transaction management
- ✅ Proper error logging

## Running Tests

### Prerequisites

1. **Python 3.7+** installed
2. **Virtual environment** (recommended)

### Setup

```bash
# Navigate to upload/tests directory
cd upload/tests

# Create virtual environment (optional but recommended)
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run Tests

```bash
# Run all tests
python3 run_tests.py

# Or run directly with pytest
python3 -m pytest test_admin_controller.py -v

# Run specific test class
python3 -m pytest test_admin_controller.py::TestIsAdmin -v

# Run specific test method
python3 -m pytest test_admin_controller.py::TestIsAdmin::test_is_admin_valid_admin -v
```

## Test Structure

### Test Classes

- **`TestIsAdmin`** - Tests for admin authorization helper function
- **`TestHome`** - Tests for admin home page function
- **`TestEmployeeManagerDetails`** - Tests for employee-manager details view
- **`TestFileMetadata`** - Tests for file metadata view
- **`TestFileMetadataArchive`** - Tests for archived file metadata view
- **`TestUpdateManagerEmail`** - Tests for manager email update functionality

### Mock Objects

The tests use comprehensive mocking to isolate the functions under test:

- **Database connections and cursors**
- **Flask request context**
- **User authentication (g.user)**
- **Template rendering**
- **Flash messages**
- **URL redirects**
- **Logging**

## Test Data

### Sample Data Used

- **Admin emails**: `admin@example.com`, `superuser@example.com`
- **Employee emails**: `employee@example.com`, `user@example.com`
- **Manager emails**: `manager@example.com`, `newmanager@example.com`
- **File names**: `document.pdf`, `file.docx`, `archived_file.pdf`

### Database Mock Results

- **Employee records**: Email pairs with manager assignments
- **File metadata**: File names, upload dates, user emails
- **Search results**: Filtered data based on search queries
- **Pagination**: Page counts and result sets

## Dependencies

### Required Packages

- **pytest** - Testing framework
- **pytest-mock** - Mocking utilities
- **flask** - Web framework
- **boto3** - AWS SDK
- **pyyaml** - YAML configuration
- **pymysql** - MySQL database connector
- **pycryptodome** - Cryptographic functions
- **requests** - HTTP library

### Test Utilities

- **MockDbManager** - Database connection mocking
- **MockConnection** - Database connection simulation
- **MockCursor** - Database cursor simulation
- **Mock exception classes** - AWS and database error simulation

## Best Practices

### Test Isolation
- Each test is independent and can run in any order
- Proper setup and teardown of mock objects
- No external dependencies (database, network, files)

### Comprehensive Coverage
- Happy path scenarios
- Error conditions
- Edge cases
- Input validation
- Authorization checks

### Maintainable Tests
- Clear test names describing the scenario
- Proper use of fixtures for common setup
- Consistent assertion patterns
- Good documentation and comments

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the project root is in Python path
2. **Missing Dependencies**: Install requirements.txt packages
3. **Mock Failures**: Check mock object setup and expectations
4. **Flask Context**: Ensure proper test request context setup

### Debug Mode

```bash
# Run with verbose output
python3 -m pytest test_admin_controller.py -v -s

# Run with detailed traceback
python3 -m pytest test_admin_controller.py --tb=long

# Run specific test with debugging
python3 -m pytest test_admin_controller.py::TestIsAdmin::test_is_admin_valid_admin -v -s
```

## Contributing

When adding new tests:

1. Follow the existing naming conventions
2. Use appropriate fixtures for setup
3. Mock external dependencies
4. Test both success and failure scenarios
5. Add proper documentation
6. Ensure tests are isolated and repeatable
