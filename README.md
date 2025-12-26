# SecShare

**Your files, your control — password-protected, audited, and secure.**

---

## Table of Contents

- [Why We Needed Something Better](#why-we-needed-something-better)
- [What Inspired It: The Cost of Getting It Wrong](#what-inspired-it-the-cost-of-getting-it-wrong)
- [So, What Is SecShare?](#so-what-is-secshare)
- [Why We Built It](#why-we-built-it)
- [The Impact at Upstox](#the-impact-at-upstox)
- [How It Works](#how-it-works)
- [Architecture Overview](#architecture-overview)
- [Key Features](#key-features)
- [Screenshots](#screenshots)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Code-Level Highlights](#code-level-highlights)
- [Background Jobs & Cron Tasks](#background-jobs--cron-tasks)
- [Security](#security)
- [Project Structure](#project-structure)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

---

## Why We Needed Something Better

At Upstox, like most companies, we rely on multiple teams — from marketing to operations — to work with external vendors. And very often, that means sharing files: reports, invoices, ad creatives, customer lists, compliance documents.

**Now here's the problem:**

Third-party platforms like Dropbox or Google Drive are convenient — but they aren't secure enough for handling PII or business-sensitive data.

As a result, we put in place a strict security policy: **no usage of unsanctioned file-sharing tools**. Dropbox, Drive, and others are blocked across our network. But that brought a new problem — **how do teams securely send files externally when email limits them to 25MB?**

This left everyone stuck: they had files to send, but no secure channel to send them through.

**And that's why we built SecShare.**

**Security isn't about blocking business — it's about enabling it, the right way.** SecShare was our answer to that need.

---

## What Inspired It: The Cost of Getting It Wrong

Our decision to block third-party sharing tools wasn't just about policy — it was about preventing real risks.

Over the years, multiple high-profile incidents have shown what can go wrong when file sharing isn't done securely:

- **Dropbox Breach (2012–2016)**: Nearly 70 million user records leaked after employee credentials were reused, partly due to insecure file handling.
- **Accellion File Transfer Hack (2021)**: Dozens of institutions — including Shell and universities — were affected after a legacy file-sharing platform was exploited.
- **Misconfigured Google Drive Links**: Multiple global incidents have seen sensitive HR files, legal documents, and even passport scans exposed due to open sharing permissions.

**These were wake-up calls.** Files were leaving companies without encryption, without audit trails, without approval.

We knew we had to solve it at the source — not just block usage.

---

## So, What Is SecShare?

SecShare is an internal file-sharing tool we built at Upstox to allow employees to securely share files with external parties — while maintaining full control over:

- **Who can upload** — Azure AD B2C SSO authentication
- **Why it's being shared** — Business justification required
- **Who's approving it** — Manager approval workflow
- **How long it stays accessible** — Configurable TTL (1-7 days)
- **Who downloaded it, and when** — Complete audit trail

**In short: it enforces accountability at every step of the process — without getting in the way of business.**

---

## Why We Built It

As an organization that values data privacy, we wanted a solution that met both security and operational needs. That meant:

- Every file uploaded is tied to a business justification.
- Every shared file goes through manager approval.
- Every action leaves behind a verifiable audit trail for compliance and accountability.
- All of this is achieved cost-effectively, without relying on third-party enterprise tools that are expensive and complicated.

What started as a necessity within the AppSec team quickly became an invaluable tool for the entire company. Today, SecShare is not just a project — **it's a core part of our daily operations.**

---

## The Impact at Upstox

Today, SecShare is **the only approved way to share files at Upstox**. All other mechanisms (e.g., Dropbox, Google Drive, email attachments) are blocked for security reasons. Here's the impact:

- **Single secure file-sharing channel** for internal and external sharing
- **Full audit trail** for compliance with regulations and internal policies
- **Annual savings of $100-150k** compared to third-party commercial tools, while maintaining control over the infrastructure

What started as a security necessity has grown into a vital part of the company's operations.

---

## How It Works

### At a Glance

1. **Upload**: Employees log in via SSO, upload a file, specify TTL (expiry time), enter a business justification, and select recipient emails (All protected by Cloudflare Turnstile).

2. **Manager Approval**: The system identifies the employee's manager, and sends them an approval email with a password-protected preview.

3. **Approval/Reject**: Managers approve or reject from the email or via portal.

4. **Link Sharing**: If approved, a secure password-protected link is sent to the recipient. If rejected, the file is never shared.

5. **Auto Expiry & Archival**: Links expire after TTL. Files are automatically moved to Deep Archive after 15 days, and metadata is archived too.

All of this happens with minimal effort from employees — but full security under the hood.

### Detailed Workflow

```
┌─────────────┐
│   Employee  │
│  (Internal) │
└──────┬──────┘
       │
       │ 1. SSO Login (Azure AD B2C)
       ▼
┌─────────────────────┐
│  Upload Application │
│   (Port 5000)       │
│  Private Network    │
└──────┬──────────────┘
       │
       │ 2. Upload File
       │    - Cloudflare Turnstile verification
       │    - Rate limiting
       │    - File validation
       │
       │ 3. Encrypt File
       │    - AES-CTR streaming encryption
       │    - KMS Data Encryption Key (DEK)
       │    - Nonce stored in S3 metadata
       │
       │ 4. Upload to S3
       │    - Multipart upload
       │    - Server-side KMS encryption
       │    - Metadata stored
       │
       │ 5. Store Metadata (MySQL)
       │    - Unique ID generation
       │    - TTL calculation
       │    - Status: pending
       ▼
┌─────────────────────┐
│   AWS S3 + KMS      │
│   MySQL RDS         │
└──────┬──────────────┘
       │
       │ 6. Identify Manager
       │    - Query employee_manager_details table
       │
       │ 7. Send Approval Email
       │    - Manager password generated
       │    - Approval/reject links
       │    - File preview option
       ▼
┌─────────────────────┐
│     Manager         │
└──────┬──────────────┘
       │
       │ 8. Review & Decide
       │    - Approve: Generate user passwords
       │    - Reject: Notify uploader
       ▼
┌─────────────────────┐
│  Upload Application │
└──────┬──────────────┘
       │
       │ 9. On Approval:
       │    - Generate download passwords
       │    - Update status: approved
       │    - Send download links to recipients
       ▼
┌─────────────────────┐
│ Download Application│
│   (Port 5001)       │
│  Public Subdomain   │
└──────┬──────────────┘
       │
       │ 10. Recipient clicks link
       │
       │ 11. Password Verification
       │     - Cloudflare Turnstile
       │     - Hash comparison
       │     - TTL validation
       │
       │ 12. Decrypt & Stream File
       │     - Retrieve DEK from S3 metadata
       │     - Decrypt DEK with KMS
       │     - AES-CTR streaming decryption
       │     - Stream to browser
       ▼
┌─────────────┐
│  End User   │
│ (External)  │
└─────────────┘
```

---

## Architecture Overview

Here's how the components fit together:

![Architecture Diagram](os_assets/Screenshot%202025-12-10%20at%206.21.59 PM.png)

### Component Highlights

#### **SSO Login (SAML)**
- Azure AD B2C authentication via MSAL
- Matches Azure AD SAML login for employees
- Secure session management with URLSafeTimedSerializer

#### **Private Portal (UploadApp)**
- **Port**: 5000 (configurable via `INTERNAL_HTTP_PORT`)
- **Access**: Internal network, Azure AD B2C protected
- **Features**:
  - Cloudflare Turnstile bot protection
  - Rate limiting (Flask-Limiter)
  - File upload with AES-CTR streaming encryption
  - Manager approval workflow
  - Admin interface (`/appsec` routes)
  - Upload history with pagination
  - Employee-manager mapping

#### **Public Portal (DownloadApp)**
- **Port**: 5001 (configurable via `EXTERNAL_HTTP_PORT`)
- **Access**: Public subdomain, password-protected downloads
- **Features**:
  - Cloudflare Turnstile verification on password submit
  - Rate limiting
  - Password verification
  - AES-CTR streaming decryption
  - TTL validation
  - Direct file streaming to browser

#### **AWS S3 (KMS-encrypted)**
- **Encryption**: AES-CTR streaming upload + KMS envelope encryption
- **Storage Class**: Standard → Deep Archive (after 15 days)
- **Metadata**: Nonce and encrypted DEK stored in object metadata
- **Multipart Upload**: Supports large files (up to 3GB configurable)

#### **MySQL RDS**
- **Read/Write Separation**: Separate reader and writer endpoints
- **Tables**:
  - `file_metadata`: Live file metadata, TTL, approvals, justification
  - `file_metadata_archive`: Archived metadata with deep_archive_status
  - `employee_manager_details`: Employee-manager mapping (synced from Azure AD)
- **Duplicate Handling**: `ON DUPLICATE KEY UPDATE` for efficient upserts

#### **Email Service**
- **SMTP**: TLS-encrypted email delivery
- **Notifications**:
  - Approval emails to managers
  - Download links to recipients
  - Rejection notifications to uploaders
  - Status updates

#### **Cron Jobs**
- **Archive Job** (`move_to_archive.py`): Moves expired files to S3 Deep Archive, archives metadata
- **Employee Sync** (`get_details.py`): Syncs employee-manager mapping from Azure AD Graph API

#### **Admin Portal**
- **Routes**: `/appsec/*` (limited access)
- **Features**:
  - View live file metadata
  - View archived file metadata
  - Manage employee-manager details
  - Update manager emails for urgent uploads
  - Audit and debug capabilities

#### **Cloudflare Turnstile**
- Protects uploads & public downloads from abuse
- Bot protection and rate limiting
- Site key and secret stored in AWS Secrets Manager

### Technology Stack

- **Backend**: Python 3.10+, Flask 3.1.0
- **Authentication**: Azure AD B2C (MSAL)
- **Storage**: AWS S3 with KMS encryption
- **Database**: MySQL (RDS) with read/write separation
- **Encryption**: PyCryptodome (AES-256-CTR)
- **Email**: SMTP with TLS
- **Bot Protection**: Cloudflare Turnstile
- **Rate Limiting**: Flask-Limiter
- **Archiving**: AWS Glacier Deep Archive

---

## Key Features

### Security & Usability

- ✅ **3GB Uploads**: Configurable via S3-stored config file (`config_upshare.yaml`)
- ✅ **Password Protection**: Both managers and recipients get unique, hashed passwords
- ✅ **TTL Enforcement**: Links and passwords auto-expire after the set duration (1-7 days)
- ✅ **Audit Logging**: Who shared what, with whom, when, and why — all traceable
- ✅ **Manager Approval Flow**: No sharing happens without explicit approval
- ✅ **CAPTCHA + Rate Limiting**: Prevents abuse of both upload and download endpoints
- ✅ **S3 + KMS Encryption**: Files are encrypted with customer-managed keys (CMK)
- ✅ **Metadata Archival**: MySQL metadata is moved to archive table after 15 days
- ✅ **Deep Archive**: Files are moved to cost-effective S3 Deep Archive after TTL
- ✅ **Admin Portal**: See employee-manager mapping, view live + archived file metadata, override manager emails for urgent uploads (limited access only)

### Technical Features

- ✅ **AES-CTR Streaming Encryption**: Efficient streaming encryption for large files
- ✅ **KMS Envelope Encryption**: Data Encryption Keys (DEK) encrypted with KMS CMK
- ✅ **Multipart Upload**: Supports large files with streaming encryption
- ✅ **Read/Write Database Separation**: Optimized database access patterns
- ✅ **Azure AD Integration**: Automatic employee-manager mapping sync
- ✅ **Comprehensive Error Handling**: Graceful error handling and user feedback
- ✅ **Logging**: Comprehensive logging for debugging and audit trails

---

## Screenshots

### Upload Portal

#### Home Page - File Upload Interface
![Upload Home](os_assets/Screenshot%202025-12-04%20at%2010.17.33 AM.png)

![Upload Home](os_assets/Screenshot%202025-12-10%20at%205.14.42 PM.png)

#### Processing Status
![Processing](os_assets/Screenshot%202025-12-04%20at%2010.19.41 AM.png)

#### Upload History
![Upload History](os_assets/Screenshot%202025-12-04%20at%2010.19.58 AM.png)

#### Manager Approvals Dashboard
![Approvals Dashboard](os_assets/Screenshot%202025-12-10%20at%205.16.38 PM.png)

#### Manager Password Interface
![Password Prompt](os_assets/Screenshot%202025-12-04%20at%2010.21.28 AM.png)

#### User Download Interface
![Download Interface](os_assets/Screenshot%202025-12-04%20at%2010.21.56 AM.png)

### Additional Views

#### Recipient Email Update
![Recipient Email Update](os_assets/Screenshot%202025-12-10%20at%205.19.36 PM.png)

#### Admin Interface
![Admin Interface](os_assets/Screenshot%202025-12-17%20at%2010.39.05 AM.png)
---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- AWS Account with appropriate IAM permissions:
  - S3 read/write access
  - KMS key usage permissions
  - Secrets Manager read access
- Azure AD B2C tenant configured
- MySQL database (RDS recommended) with read/write separation
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
   
   Upload `config_upshare.yaml` to your S3 bucket. The bucket name should be:
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
         writer_host: your-writer-host.rds.amazonaws.com
         reader_host: your-reader-host.rds.amazonaws.com
         writer_user: secshare_writer
         reader_user: secshare_reader
         database: secshare_db
         port: 3306
     azure:
       client_id: your-azure-client-id
       tenant_id: your-azure-tenant-id
     secrets:
       secret_name: arn:aws:secretsmanager:region:account:secret:name
       region_name: ap-south-1
     mail:
       mail_server: smtp.example.com
       mail_port: 587
     turnstile:
       site_key: your-turnstile-site-key
     file:
       max_size: 3221225472  # 3GB in bytes
       allowed_extensions: ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'zip', 'rar']
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

8. **Set up database schema**

   Create the following tables in your MySQL database:
   
   ```sql
   CREATE TABLE file_metadata (
       unique_id VARCHAR(255) PRIMARY KEY,
       file_name VARCHAR(500) NOT NULL,
       ttl INT NOT NULL,
       password_hash VARCHAR(255),
       manager_password VARCHAR(255),
       recipients TEXT,
       business_justification TEXT,
       message TEXT,
       expiry DATETIME NOT NULL,
       status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
       uploaded_on DATETIME DEFAULT CURRENT_TIMESTAMP,
       uploaded_by VARCHAR(255),
       user_password_hash VARCHAR(255),
       INDEX idx_expiry (expiry),
       INDEX idx_status (status),
       INDEX idx_uploaded_by (uploaded_by)
   );

   CREATE TABLE employee_manager_details (
       employee_email VARCHAR(255) PRIMARY KEY,
       employee_name VARCHAR(255),
       employee_designation VARCHAR(255),
       manager_email VARCHAR(255),
       manager_name VARCHAR(255),
       manager_designation VARCHAR(255),
       department VARCHAR(255),
       INDEX idx_manager_email (manager_email)
   );

   CREATE TABLE file_metadata_archive (
       unique_id VARCHAR(255) PRIMARY KEY,
       file_name VARCHAR(500) NOT NULL,
       ttl INT NOT NULL,
       password_hash VARCHAR(255),
       manager_password VARCHAR(255),
       recipients TEXT,
       business_justification TEXT,
       message TEXT,
       expiry DATETIME NOT NULL,
       status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
       uploaded_on DATETIME DEFAULT CURRENT_TIMESTAMP,
       uploaded_by VARCHAR(255),
       user_password_hash VARCHAR(255),
       deep_archive_status ENUM('yes', 'no') DEFAULT 'no',
       INDEX idx_deep_archive_status (deep_archive_status),
       INDEX idx_expiry (expiry)
   );
   ```

9. **Run the application**
   ```bash
   python main.py
   ```

   This will start both applications:
   - Upload app: http://localhost:5000
   - Download app: http://localhost:5001

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NODE_ENV` | Environment (uat/prod) | `uat` |
| `INTERNAL_HTTP_PORT` | Upload app port | `5000` |
| `EXTERNAL_HTTP_PORT` | Download app port | `5001` |

### Configuration File (S3)

The application uses a YAML configuration file (`config_upshare.yaml`) stored in an S3 bucket and secrets from AWS Secrets Manager. The configuration includes:

- **Environment-specific settings** (UAT/PROD)
- **Database connection parameters**: Writer/reader hosts, users, database name, port
- **S3 bucket names and KMS key IDs**
- **Azure AD B2C settings**: Client ID, tenant ID
- **Mail server configuration**: SMTP server, port
- **File size limits and allowed extensions**: Max size (default 3GB), allowed extensions
- **Admin access user list**

### Database Schema Details

#### `file_metadata` Table

**Purpose**: Stores file upload information and status.

**Columns and Descriptions**:
- `unique_id`: Unique identifier (generated from file hash, TTL, filename, uploader)
- `file_name`: Original filename (normalized)
- `ttl`: Time-to-live in days (1-7)
- `password_hash`: Hashed user download password (bcrypt)
- `manager_password`: Hashed manager approval password (bcrypt)
- `recipients`: Comma-separated recipient emails
- `business_justification`: Required upload justification
- `message`: Optional user message
- `expiry`: Calculated expiration timestamp (uploaded_on + TTL)
- `status`: File status (pending/approved/rejected)
- `uploaded_on`: Upload timestamp
- `uploaded_by`: Uploader email (from Azure AD)
- `user_password_hash`: Additional user password hash

#### `employee_manager_details` Table

**Purpose**: Maps employees to their managers (synced from Azure AD).

**Columns and Descriptions**:
- `employee_email`: Employee email address (PRIMARY KEY)
- `employee_name`: Employee display name
- `employee_designation`: Employee job title
- `manager_email`: Manager email address
- `manager_name`: Manager display name
- `manager_designation`: Manager job title
- `department`: Department name

**Note**: Uses `ON DUPLICATE KEY UPDATE` for efficient syncs.

#### `file_metadata_archive` Table

**Purpose**: Stores archived file metadata.

**Columns and Descriptions**:
- All fields from `file_metadata` table
- `deep_archive_status`: Glacier Deep Archive status (yes/no)

**Note**: Files are moved to this table after 15 days or TTL expiration.

---

## Code-Level Highlights

### S3 Integration

Files are uploaded to AWS S3 with the following security measures:

- **AES-CTR Streaming Encryption**: Files are encrypted using AES in CTR mode with a randomly generated nonce (8 bytes)
- **KMS Envelope Encryption**: 
  - Data Encryption Key (DEK) is generated using AWS KMS (`generate_data_key`)
  - DEK is encrypted with KMS Customer Managed Key (CMK)
  - Encrypted DEK is stored in S3 object metadata as `x-amz-key`
- **Multipart Upload**: Large files are uploaded in 5MB chunks with streaming encryption
- **Metadata Storage**: Nonce is stored in S3 object metadata as `nonce` (hex-encoded)
- **Server-Side Encryption**: Additional KMS encryption at S3 level (`ServerSideEncryption='aws:kms'`)

**Code Location**: `upload/libs/s3Handler.py`

```python
# Generate nonce for CTR mode
nonce = get_random_bytes(8)
cipher = AES.new(dek, AES.MODE_CTR, nonce=nonce)

# Store nonce and encrypted DEK in metadata
metadata = {'x-amz-key': encrypted_dek, 'nonce': nonce.hex()}
```

### MySQL Database Operations

File metadata is tracked in MySQL with the following features:

- **Read/Write Separation**: Separate reader and writer connections for performance
- **Duplicate Handling**: `ON DUPLICATE KEY UPDATE` for efficient upserts in employee-manager table
- **Unique ID Generation**: Generated from file hash, TTL, filename, and uploader email
- **TTL Validation**: Expiry calculated as `uploaded_on + TTL days`
- **Status Management**: Tracks pending → approved/rejected workflow

**Code Location**: `upload/models/dbModel.py`, `download/models/dbModel.py`

### Manager Approval Workflow

The system implements a secure approval workflow:

1. **Manager Identification**: Queries `employee_manager_details` table based on uploader email
2. **Password Generation**: Generates unique manager password (hashed with bcrypt)
3. **Email Notification**: Sends approval email with:
   - Approval link: `/api/approve/<unique_id>`
   - Reject link: `/api/reject/<unique_id>`
   - Manager preview link: `/manager/<unique_id>`
4. **On Approval**: 
   - Generates user download passwords (one per recipient)
   - Updates status to 'approved'
   - Sends download links to recipients
5. **On Rejection**:
   - Updates status to 'rejected'
   - Notifies uploader via email

**Code Location**: `upload/controllers/apiController.py`

### Cost Efficiency

Files are moved to S3 Deep Archive after 15 days to minimize storage costs:

- **Archive Job**: `jobs/move_to_archive.py` runs periodically (cron)
- **Process**:
  1. Queries `file_metadata_archive` for files with `deep_archive_status = 'no'`
  2. Checks S3 storage class (avoids duplicate transitions)
  3. Transitions to `DEEP_ARCHIVE` storage class
  4. Updates `deep_archive_status = 'yes'` in database
- **Metadata Archival**: Metadata moved to `file_metadata_archive` table after 15 days
- **Database Optimization**: Keeps primary `file_metadata` table lean

**Code Location**: `jobs/move_to_archive.py`

### Encryption Implementation

- **Upload**: AES-CTR mode with streaming encryption (`upload/libs/s3Handler.py`)
- **Download**: AES-CTR mode with streaming decryption (`download/libs/fileDecryptor.py`)
- **Key Management**: AWS KMS for DEK encryption/decryption
- **Nonce Handling**: 8-byte nonce stored in S3 metadata, retrieved during decryption

---

## Background Jobs & Cron Tasks

### Archive Job (`move_to_archive.py`)

**Purpose**: Moves expired files to S3 Deep Archive and archives metadata.

**Schedule**: Run daily (recommended: 2 AM).

**Crontab Entry**:
```bash
# Add to crontab
0 2 * * * /usr/bin/python3 /path/to/jobs/move_to_archive.py
```

**What it does**:
1. Fetches all files from `file_metadata_archive` with `deep_archive_status = 'no'`
2. Checks if files exist in S3 and are not already in Deep Archive
3. Transitions files to `DEEP_ARCHIVE` storage class
4. Updates `deep_archive_status = 'yes'` in database
5. Logs all operations for audit

**Configuration**: Uses same config as main application (S3 bucket, KMS key, database).

### Employee-Manager Sync Job (`get_details.py`)

**Purpose**: Syncs employee-manager mapping from Azure AD Graph API.

**Schedule**: Run weekly (recommended: Sunday 2 AM).

**Crontab Entry**:
```bash
# Add to crontab
0 2 * * 0 /usr/bin/python3 /path/to/jobs/get_details.py
```

**What it does**:
1. Authenticates with Azure AD using client credentials
2. Fetches all users from Microsoft Graph API
3. For each user, fetches manager details
4. Inserts/updates `employee_manager_details` table using `ON DUPLICATE KEY UPDATE`
5. Handles pagination for large organizations

**Configuration**: Requires Azure AD app registration with Graph API permissions.

---

## Security

### Encryption

- **File Encryption**: AES-256-CTR mode with streaming encryption
- **Key Management**: AWS KMS Customer Managed Keys (CMK) for envelope encryption
- **Key Storage**: Encrypted Data Encryption Keys (DEK) stored in S3 object metadata
- **Transport Security**: HTTPS/TLS for all communications
- **Nonce Management**: Random 8-byte nonce per file, stored securely in S3 metadata

### Authentication & Authorization

- **Internal Access**: Azure AD B2C SSO with MSAL (Microsoft Authentication Library)
- **Session Management**: URLSafeTimedSerializer for secure, signed cookies
- **Manager Verification**: Database-backed manager role verification
- **Admin Access**: Configurable admin user list in S3 config
- **Password Hashing**: bcrypt with salt for all passwords

### Protection Mechanisms

- **Bot Protection**: Cloudflare Turnstile integration on upload and download
- **Rate Limiting**: Flask-Limiter with configurable limits per endpoint
- **Input Validation**: Comprehensive sanitization and validation
- **SQL Injection Prevention**: Parameterized queries throughout
- **XSS Protection**: Input sanitization and secure Jinja2 templates
- **CSRF Protection**: Secure cookie settings (HttpOnly, Secure, SameSite)
- **TTL Enforcement**: Automatic expiration of links and passwords

### Compliance & Audit

- **Audit Logging**: Comprehensive logging of all operations (who, what, when, why)
- **File Expiration**: Automatic TTL enforcement with database queries
- **Archive Management**: Automated archiving to Glacier Deep Archive
- **Metadata Tracking**: Complete audit trail in database
- **Business Justification**: Required for all uploads (compliance requirement)

---

## Project Structure

```
secshare/
├── upload/                          # Internal upload application
│   ├── __init__.py                  # Flask app factory
│   ├── run.py                       # Application entry point
│   ├── config.py                    # Configuration loader (S3 + Secrets Manager)
│   ├── controllers/                 # Request handlers
│   │   ├── appController.py        # Main app routes (home, history, approvals)
│   │   ├── apiController.py        # API endpoints (upload, approve, reject)
│   │   ├── authController.py       # Authentication (Azure AD B2C)
│   │   └── adminController.py      # Admin routes (/appsec/*)
│   ├── models/                      # Data models
│   │   └── dbModel.py              # Database operations (FileModel, EmployeeModel, DbManager)
│   ├── libs/                        # Business logic
│   │   ├── fileEncryption.py       # File encryption (KMS DEK generation)
│   │   ├── s3Handler.py            # S3 operations (multipart upload, AES-CTR)
│   │   ├── mailHandler.py          # Email notifications (SMTP)
│   │   ├── cookieHandler.py        # Cookie management
│   │   └── secretsManager.py       # AWS Secrets Manager
│   ├── routes/                      # Route blueprints
│   │   ├── appRoute.py            # App routes blueprint
│   │   ├── apiRoute.py            # API routes blueprint
│   │   ├── authRoute.py           # Auth routes blueprint
│   │   └── adminRoute.py           # Admin routes blueprint
│   ├── templates/                   # HTML templates
│   │   ├── home.html              # Upload interface
│   │   ├── history.html           # Upload history
│   │   ├── approvals.html         # Manager approvals dashboard
│   │   ├── processing.html       # Processing status
│   │   └── admin/                 # Admin templates
│   │       ├── home.html
│   │       ├── table.html
│   │       └── update_manager_email.html
│   └── tests/                       # Unit tests
│       ├── test_api_controller.py
│       ├── test_app_controller.py
│       └── test_utils.py
│
├── download/                        # External download application
│   ├── __init__.py                  # Flask app factory
│   ├── run.py                       # Application entry point
│   ├── config.py                    # Configuration loader
│   ├── controllers/                 # Request handlers
│   │   ├── appController.py        # Main app routes (download pages)
│   │   └── apiController.py        # API endpoints (password verification)
│   ├── models/                      # Data models
│   │   └── dbModel.py              # Database operations
│   ├── libs/                        # Business logic
│   │   └── fileDecryptor.py        # File decryption (AES-CTR streaming)
│   ├── routes/                      # Route blueprints
│   │   ├── appRoute.py            # App routes blueprint
│   │   └── apiRoute.py            # API routes blueprint
│   ├── templates/                   # HTML templates
│   │   ├── download_home.html
│   │   ├── password_prompt.html
│   │   ├── manager_password_prompt.html
│   │   ├── download_and_redirect.html
│   │   └── error.html
│   └── tests/                       # Unit tests
│       ├── test_api_controller.py
│       └── test_app_controller.py
│
├── shared/                          # Shared utilities
│   ├── libs/
│   │   └── secretsManager.py       # Shared secrets manager
│   ├── utils/
│   │   ├── logger.py               # Logging configuration
│   │   └── decorators.py           # Common decorators (login_required)
│   └── static/
│       └── favicon.png
│
├── jobs/                            # Background jobs
│   ├── move_to_archive.py          # Archive job (S3 → Deep Archive)
│   └── get_details.py              # Employee-manager sync (Azure AD → MySQL)
│
├── docker/                          # Docker configuration
│   └── Dockerfile
│
├── os_assets/                       # Screenshots and diagrams
│   └── *.png
│
├── main.py                          # Application launcher (starts both apps)
├── requirements.txt                 # Python dependencies
├── README                           # This file
└── pom.xml                          # Maven configuration (if applicable)
```

---

## Deployment

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
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
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
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

2. **Set up process manager** (systemd recommended)
   
   Create `/etc/systemd/system/secshare.service`:
   ```ini
   [Unit]
   Description=SecShare File Sharing Application
   After=network.target

   [Service]
   Type=simple
   User=secshare
   WorkingDirectory=/opt/secshare
   Environment="NODE_ENV=prod"
   Environment="INTERNAL_HTTP_PORT=5000"
   Environment="EXTERNAL_HTTP_PORT=5001"
   ExecStart=/usr/bin/python3 /opt/secshare/main.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

   Enable and start:
```bash
   sudo systemctl enable secshare
   sudo systemctl start secshare
   ```

3. **Configure SSL certificates** (Let's Encrypt recommended)
4. **Set up monitoring and logging** (CloudWatch, Datadog, etc.)
5. **Configure automated backups** (RDS automated backups, S3 versioning)

### Background Jobs Setup

Set up cron jobs for archive and sync tasks:

```bash
# Edit crontab
crontab -e

# Add these lines:
# Archive job - runs daily at 2 AM
0 2 * * * /usr/bin/python3 /opt/secshare/jobs/move_to_archive.py >> /var/log/secshare/archive.log 2>&1

# Employee-manager sync - runs weekly on Sunday at 2 AM
0 2 * * 0 /usr/bin/python3 /opt/secshare/jobs/get_details.py >> /var/log/secshare/sync.log 2>&1
```

---

## Contributing

We believe in the power of open source to drive innovation and help others solve similar problems. SecShare is available under the Apache 2.0 license. Here's how you can get involved:

### Ways to Contribute

- **Deploy it**: Use it as-is or customize it for your team or company
- **Extend it**: Build new features such as:
  - Integration with other tools (Slack, Teams, etc.)
  - Advanced admin controls
  - Multi-cloud support (Azure Blob, GCS)
  - Enhanced reporting and analytics
- **Improve it**: Fix bugs, update documentation, or contribute new ideas to the project

### Contribution Process

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
- Update documentation for new features

---

## Contributors

- [Arun Govindasamy](https://github.com/govindasamyarun)
- [Indrajith S B](https://github.com/Indrajith-S)
- [Yogendra Swaroop Srivastava](https://github.com/yogi1426)

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for secure file sharing**

*Your files, your control — password-protected, audited, and secure.*

**Explore and contribute to SecShare on GitHub. Your contributions will help make this tool better and more secure for teams worldwide.**
