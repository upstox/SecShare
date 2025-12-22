from flask import redirect, request, url_for, flash, current_app, make_response
from msal import ConfidentialClientApplication
from upload.libs.cookieHandler import CookieHandler

from shared.utils.logger import logger

# Scope 
SCOPE = ['User.Read']

def login():
    logger.debug('Login request received')
    # Get Azure configuration from app config
    client_id = current_app.config['azure_client_id']
    tenant_id = current_app.config['azure_tenant_id']
    client_secret = current_app.config['azure_client_secret']
    redirect_uri = f'{current_app.config["upload_base_url"]}/login/callback'
    authority = f'https://login.microsoftonline.com/{tenant_id}'
    
    client = ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority
    )
    auth_url = client.get_authorization_request_url(
        scopes=SCOPE,
        redirect_uri=redirect_uri
    )
    return redirect(auth_url)

def callback():
    logger.debug('Callback request received')
    # Verify 
    code = request.args.get('code')
    if not code:
        flash('No authorization code provided.', 'error')
        return redirect(url_for('authRoute.login'))

    # Get Azure configuration from app config
    client_id = current_app.config['azure_client_id']
    tenant_id = current_app.config['azure_tenant_id']
    client_secret = current_app.config['azure_client_secret']
    redirect_uri = f'{current_app.config["upload_base_url"]}/login/callback'
    authority = f'https://login.microsoftonline.com/{tenant_id}'

    client_app = ConfidentialClientApplication(
        client_id, 
        authority=authority, 
        client_credential=client_secret
    )
    result = client_app.acquire_token_by_authorization_code(
        code=code,
        scopes=SCOPE,
        redirect_uri=redirect_uri
    )
    if 'error' in result:
        flash(f'Login failed: {result.get("error_description")}', 'error')
        return redirect(url_for('authRoute.login'))

    # Extract user info
    id_token_claims = result.get('id_token_claims')
    if not id_token_claims:
        flash('Failed to retrieve user info.', 'error')
        return redirect(url_for('authRoute.login'))

    preferred_username = id_token_claims.get('preferred_username')
    
    # Set 'user' cookie 
    response = make_response(redirect(url_for('appRoute.home')))
    CookieHandler().set_cookie(response, 'user', {'preferred_username': preferred_username})
    return response