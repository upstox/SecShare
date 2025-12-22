# SecShare

<div align="center">

**A secure, enterprise-grade file sharing solution for internal-to-external file transfers with manager approval workflow**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.0-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Screenshots](#screenshots)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Usage](#usage)
- [Security](#security)
- [Project Structure](#project-structure)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

SecShare is a secure file sharing application designed for organizations that need to share sensitive files with external parties while maintaining strict security controls. The application implements a dual-application architecture with an internal upload portal and an external download portal, ensuring complete separation of concerns and enhanced security.

### Key Capabilities

- **Secure File Upload**: Files are encrypted using AES-256 encryption with AWS KMS key management
- **Manager Approval Workflow**: All file shares require manager approval before external access is granted
- **Password-Protected Downloads**: Multi-layer password protection for both managers and end users
- **Enterprise Authentication**: Azure AD B2C integration for seamless SSO
- **Automated Archiving**: Files are automatically archived to AWS Glacier Deep Archive after expiration
- **Comprehensive Audit Trail**: Complete logging and tracking of all file operations

## ✨ Features

### Core Functionality

- ✅ **AES-256 Encryption**: All files encrypted at rest using AES with AWS KMS Data Encryption Keys
- ✅ **Manager Approval Workflow**: Two-step approval process with email notifications
- ✅ **Password Protection**: Separate passwords for manager preview and user downloads
- ✅ **Time-Limited Access**: Configurable TTL (1-7 days) with automatic expiration
- ✅ **Azure AD B2C Integration**: Enterprise-grade authentication and authorization
- ✅ **AWS S3 Storage**: Scalable cloud storage with server-side encryption
- ✅ **MySQL Database**: Reliable metadata storage with read/write separation
- ✅ **Email Notifications**: Automated email alerts for approvals, rejections, and downloads

### Security Features

- 🔒 **Cloudflare Turnstile**: Bot protection and abuse prevention
- 🔒 **Rate Limiting**: Flask-Limiter integration to prevent abuse
- 🔒 **Secure Session Management**: URLSafeTimedSerializer for signed cookies
- 🔒 **Input Validation**: Comprehensive sanitization and validation
- 🔒 **Secure Cookie Settings**: HttpOnly, Secure, and SameSite attributes
- 🔒 **HTTPS Enforcement**: All communications encrypted in transit

### Administrative Features

- 👥 **Admin Dashboard**: Comprehensive admin interface for user and file management
- 📊 **Upload History**: Paginated history view for all user uploads
- 🔍 **Search Functionality**: Advanced search across approvals and history
- 📈 **File Metadata Management**: Complete audit trail and metadata tracking
- 🗄️ **Archive Management**: Automated archiving with status tracking

## 🏗️ Architecture

SecShare follows a **dual-application MVC architecture** pattern, separating internal and external access for enhanced security:

### Architecture Diagram

![Architecture Diagram](os_assets/Screenshot%202025-12-10%20at%206.21.59%20PM.png)

### Component Overview

#### 1. **Upload Application** (Internal Portal)
- **Purpose**: Internal-facing application for authenticated employees
- **Port**: 5000 (configurable via `INTERNAL_HTTP_PORT`)
- **Access**: Private network, Azure AD B2C protected
- **Responsibilities**:
  - File upload and encryption
- Manager approval workflow
  - Admin interface
  - Upload history management
  - Employee-manager mapping

#### 2. **Download Application** (External Portal)
- **Purpose**: Public-facing application for external file downloads
- **Port**: 5001 (configurable via `EXTERNAL_HTTP_PORT`)
- **Access**: Public subdomain, password-protected downloads
- **Responsibilities**:
  - Password verification
  - File decryption and streaming
  - Download link management
  - TTL validation

### Data Flow

```
┌─────────────┐
│   User      │
│  (Internal) │
└──────┬──────┘
       │
       │ 1. Authenticate (Azure AD B2C)
       ▼
┌─────────────────────┐
│  Upload Application │
│   (Port 5000)       │
└──────┬──────────────┘
       │
       │ 2. Encrypt File (AES-256 + KMS)
       │ 3. Upload to S3
       │ 4. Store Metadata (MySQL)
       ▼
┌─────────────────────┐
│   AWS S3 + KMS      │
│   MySQL Database    │
└──────┬──────────────┘
       │
       │ 5. Send Approval Email
       ▼
┌─────────────────────┐
│     Manager         │
└──────┬──────────────┘
       │
       │ 6. Approve/Reject
       ▼
┌─────────────────────┐
│  Upload Application │
└──────┬──────────────┘
       │
       │ 7. Generate Download Links
       │ 8. Send User Notification
       ▼
┌─────────────────────┐
│ Download Application│
│   (Port 5001)       │
└──────┬──────────────┘
       │
       │ 9. Password Verification
       │ 10. Decrypt & Stream File
       ▼
┌─────────────┐
│  End User   │
│ (External)  │
└─────────────┘
```

### Technology Stack

- **Backend**: Python 3.10+, Flask 3.1.0
- **Authentication**: Azure AD B2C (MSAL)
- **Storage**: AWS S3 with KMS encryption
- **Database**: MySQL (RDS) with read/write separation
- **Encryption**: PyCryptodome (AES-256-CBC)
- **Email**: SMTP with TLS
- **Bot Protection**: Cloudflare Turnstile
- **Rate Limiting**: Flask-Limiter
- **Archiving**: AWS Glacier Deep Archive

## 📸 Screenshots

### Upload Portal

#### Home Page - File Upload Interface
![Upload Home](os_assets/Screenshot%202025-12-04%20at%2010.17.33%20AM.png)

#### Upload History
![Upload History](os_assets/Screenshot%202025-12-04%20at%2010.19.33%20AM.png)

#### Manager Approvals Dashboard
![Approvals Dashboard](os_assets/Screenshot%202025-12-04%20at%2010.19.41%20AM.png)

#### Approval Details View
![Approval Details](os_assets/Screenshot%202025-12-04%20at%2010.19.58%20AM.png)

#### Admin Interface
![Admin Interface](os_assets/Screenshot%202025-12-04%20at%2010.20.20%20AM.png)

### Download Portal

#### Password Prompt
![Password Prompt](os_assets/Screenshot%202025-12-04%20at%2010.21.28%20AM.png)

#### Download Interface
![Download Interface](os_assets/Screenshot%202025-12-04%20at%2010.21.56%20AM.png)

### Additional Views

#### Processing Status
![Processing](os_assets/Screenshot%202025-12-10%20at%205.14.42%20PM.png)

#### Manager Email Update
![Manager Email Update](os_assets/Screenshot%202025-12-10%20at%205.16.38%20PM.png)

#### File Metadata View
![File Metadata](os_assets/Screenshot%202025-12-10%20at%205.19.36%20PM.png)

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- AWS Account with appropriate IAM permissions
- Azure AD B2C tenant configured
- MySQL database (RDS recommended)
- SMTP server for email notifications
- Cloudflare Turnstile account (optional but recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/secshare.git
   cd secshare
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure AWS credentials**
   ```bash
   aws configure
   # Or set environment variables:
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=ap-south-1
   ```

5. **Set environment variables**
   ```bash
   export NODE_ENV=uat  # or 'prod' for production
   export INTERNAL_HTTP_PORT=5000
   export EXTERNAL_HTTP_PORT=5001
   ```

6. **Create configuration file in S3**
   
   Upload `config_secshare.yaml` to your S3 bucket. The bucket name should be:
   - `company-uat-secshare-appsec` for UAT
   - `company-secshare-appsec` for Production

   Example configuration structure:
   ```yaml
   uat:
     s3:
       bucket_name: your-uat-bucket
       region: ap-south-1
     db:
       mysql:
         writer_host: your-writer-host
         reader_host: your-reader-host
         writer_user: your-writer-user
         reader_user: your-reader-user
         database: secshare_db
         port: 3306
     azure:
       client_id: your-azure-client-id
       tenant_id: your-azure-tenant-id
     secrets:
       secret_name: your-secrets-arn
       region_name: ap-south-1
     mail:
       mail_server: smtp.example.com
       mail_port: 587
     turnstile:
       site_key: your-turnstile-site-key
     file:
       max_size: 104857600  # 100MB in bytes
       allowed_extensions: ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt']
     admin_access:
       users: ['admin@example.com']
   ```

7. **Configure AWS Secrets Manager**

   Create a secret in AWS Secrets Manager with the following keys:
   - `api.external.db.mysql.writer_password`
   - `api.external.db.mysql.reader_password`
   - `api.external.azure.client_secret`
   - `api.external.salt_secret`
   - `api.external.secret_key`
   - `api.external.smtp.smtp_username`
   - `api.external.smtp.smtp_password`
   - `api.external.turnstile_secret`
   - `api.external.s3.kms_key_secret`

8. **Run the application**
   ```bash
   python main.py
   ```

   This will start both applications:
   - Upload app: http://localhost:5000
   - Download app: http://localhost:5001

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NODE_ENV` | Environment (uat/prod) | `uat` |
| `INTERNAL_HTTP_PORT` | Upload app port | `5000` |
| `EXTERNAL_HTTP_PORT` | Download app port | `5001` |

### Configuration File (S3)

The application loads configuration from `config_secshare.yaml` stored in S3. The configuration includes:

- **S3 Settings**: Bucket name, region, KMS key ID
- **Database Settings**: Host, user, database name, port
- **Azure AD B2C**: Client ID, tenant ID
- **Email Settings**: SMTP server, port
- **File Settings**: Max size, allowed extensions
- **Security**: Turnstile site key, admin user list
- **Secrets Manager**: ARN and region for secrets

### Database Schema

#### `file_metadata` Table
Stores file upload information and status:
- `unique_id`: Unique identifier for the file
- `file_name`: Original filename
- `ttl`: Time-to-live in days
- `password_hash`: Hashed user download password
- `manager_password`: Hashed manager approval password
- `recipients`: Comma-separated recipient emails
- `business_justification`: Upload justification
- `message`: User message
- `expiry`: Expiration timestamp
- `status`: File status (pending/approved/rejected)
- `uploaded_on`: Upload timestamp
- `uploaded_by`: Uploader email
- `user_password_hash`: Additional user password hash

#### `employee_manager_details` Table
Maps employees to their managers:
- `employee_email`: Employee email address
- `manager_email`: Manager email address
- `employee_name`: Employee name
- `manager_name`: Manager name
- `department`: Department name
- `employee_designation`: Employee role
- `manager_designation`: Manager role

#### `file_metadata_archive` Table
Archived file metadata:
- All fields from `file_metadata`
- `deep_archive_status`: Glacier archive status

## 📖 Usage

### For End Users

1. **Login**: Access the upload portal and authenticate with Azure AD B2C
2. **Upload File**: 
   - Select file (max size and extensions enforced)
   - Enter recipient email addresses
   - Set TTL (1-7 days)
   - Provide business justification
   - Optional: Add a message
   - Complete Cloudflare Turnstile verification
   - Submit

3. **Wait for Approval**: Manager receives email notification
4. **Receive Download Link**: Once approved, recipients receive email with download link
5. **Download File**: 
   - Click download link
   - Enter password (sent separately)
   - File downloads automatically

### For Managers

1. **Receive Approval Request**: Email notification with approval/reject links
2. **Review Request**: Click link to view file details
3. **Approve or Reject**: 
   - **Approve**: System generates download passwords and sends to recipients
   - **Reject**: Uploader receives rejection notification
4. **Preview File** (optional): Managers can preview files using manager password

### For Administrators

1. **Access Admin Portal**: Navigate to `/appsec` routes (requires admin access)
2. **View File Metadata**: `/appsec/file_metadata` - View all file uploads
3. **View Archive**: `/appsec/file_metadata_archive` - View archived files
4. **Manage Employees**: `/appsec/employee_manager_details` - Manage employee-manager mappings
5. **Update Manager Email**: `/appsec/update_manager_email` - Update manager email addresses

## 🔐 Security

### Encryption

- **File Encryption**: AES-256-CBC encryption with randomly generated IV
- **Key Management**: AWS KMS for Data Encryption Key (DEK) management
- **Key Storage**: Encrypted DEK stored in S3 object metadata
- **Transport Security**: HTTPS/TLS for all communications

### Authentication & Authorization

- **Internal Access**: Azure AD B2C SSO with MSAL
- **Session Management**: URLSafeTimedSerializer for secure, signed cookies
- **Manager Verification**: Database-backed manager role verification
- **Admin Access**: Configurable admin user list

### Protection Mechanisms

- **Bot Protection**: Cloudflare Turnstile integration
- **Rate Limiting**: Flask-Limiter with configurable limits
- **Input Validation**: Comprehensive sanitization and validation
- **SQL Injection Prevention**: Parameterized queries
- **XSS Protection**: Input sanitization and secure templates
- **CSRF Protection**: Secure cookie settings

### Compliance & Audit

- **Audit Logging**: Comprehensive logging of all operations
- **File Expiration**: Automatic TTL enforcement
- **Archive Management**: Automated archiving to Glacier Deep Archive
- **Metadata Tracking**: Complete audit trail in database

## 📁 Project Structure

```
secshare/
├── upload/                          # Internal upload application
│   ├── __init__.py                  # Flask app factory
│   ├── run.py                       # Application entry point
│   ├── config.py                    # Configuration loader
│   ├── controllers/                 # Request handlers
│   │   ├── appController.py        # Main app routes
│   │   ├── apiController.py        # API endpoints
│   │   ├── authController.py       # Authentication
│   │   └── adminController.py      # Admin routes
│   ├── models/                      # Data models
│   │   └── dbModel.py              # Database operations
│   ├── libs/                        # Business logic
│   │   ├── fileEncryption.py       # File encryption
│   │   ├── s3Handler.py            # S3 operations
│   │   ├── mailHandler.py          # Email notifications
│   │   ├── cookieHandler.py        # Cookie management
│   │   └── secretsManager.py       # AWS Secrets Manager
│   ├── routes/                      # Route blueprints
│   │   ├── appRoute.py
│   │   ├── apiRoute.py
│   │   ├── authRoute.py
│   │   └── adminRoute.py
│   ├── templates/                   # HTML templates
│   │   ├── home.html
│   │   ├── history.html
│   │   ├── approvals.html
│   │   ├── processing.html
│   │   └── admin/
│   └── tests/                       # Unit tests
│
├── download/                        # External download application
│   ├── __init__.py                  # Flask app factory
│   ├── run.py                       # Application entry point
│   ├── config.py                    # Configuration loader
│   ├── controllers/                 # Request handlers
│   │   ├── appController.py        # Main app routes
│   │   └── apiController.py        # API endpoints
│   ├── models/                      # Data models
│   │   └── dbModel.py              # Database operations
│   ├── libs/                        # Business logic
│   │   └── fileDecryptor.py        # File decryption
│   ├── routes/                      # Route blueprints
│   │   ├── appRoute.py
│   │   └── apiRoute.py
│   ├── templates/                   # HTML templates
│   │   ├── download_home.html
│   │   ├── password_prompt.html
│   │   ├── manager_password_prompt.html
│   │   ├── download_and_redirect.html
│   │   └── error.html
│   └── tests/                       # Unit tests
│
├── shared/                          # Shared utilities
│   ├── libs/
│   │   └── secretsManager.py       # Shared secrets manager
│   ├── utils/
│   │   ├── logger.py               # Logging configuration
│   │   └── decorators.py           # Common decorators
│   └── static/
│       └── favicon.png
│
├── jobs/                            # Background jobs
│   ├── move_to_archive.py          # Archive job
│   └── get_details.py              # Utility jobs
│
├── docker/                          # Docker configuration
│   └── Dockerfile
│
├── os_assets/                       # Screenshots and diagrams
│   └── *.png
│
├── main.py                          # Application launcher
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
└── pom.xml                          # Maven configuration (if applicable)
```

## 🐳 Deployment

### Docker Deployment

1. **Build the Docker image**
   ```bash
   docker build -t secshare:latest -f docker/Dockerfile .
   ```

2. **Run the container**
   ```bash
   docker run -d \
     -p 5000:5000 \
     -p 5001:5001 \
     -e NODE_ENV=prod \
     -e INTERNAL_HTTP_PORT=5000 \
     -e EXTERNAL_HTTP_PORT=5001 \
     -e AWS_ACCESS_KEY_ID=your_key \
     -e AWS_SECRET_ACCESS_KEY=your_secret \
     --name secshare \
     secshare:latest
   ```

### Production Deployment

1. **Set up reverse proxy** (Nginx recommended)
   ```nginx
   # Upload app (internal)
   server {
       listen 443 ssl;
       server_name secshare.company.app;
       
       location / {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   
   # Download app (external)
   server {
       listen 443 ssl;
       server_name secshare.company.com;
       
       location / {
           proxy_pass http://localhost:5001;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

2. **Set up process manager** (systemd or supervisor)
3. **Configure SSL certificates**
4. **Set up monitoring and logging**
5. **Configure automated backups**

### Background Jobs

The archive job should be scheduled to run periodically:

```bash
# Add to crontab
0 2 * * * /usr/bin/python3 /path/to/jobs/move_to_archive.py
```

## 🧪 Testing

Run the test suite:

```bash
# Upload app tests
cd upload/tests
pytest

# Download app tests
cd download/tests
pytest
```

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Add tests** for new functionality
5. **Ensure all tests pass** (`pytest`)
6. **Commit your changes** (`git commit -m 'Add amazing feature'`)
7. **Push to the branch** (`git push origin feature/amazing-feature`)
8. **Open a Pull Request**

### Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Add docstrings to all functions and classes
- Keep functions focused and small
- Write meaningful commit messages

## 📝 License

This project is proprietary and confidential. All rights reserved.

---

<div align="center">

**Built with ❤️ for secure file sharing**

For questions or support, please open an issue or contact the maintainers.

</div>