from functools import wraps
from flask import request, redirect, url_for, g, current_app, flash
from .logger import logger
import requests

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        logger.debug('Login required decorator called')
        serializer = current_app.config['serializer']
        value_signed = request.cookies.get('user')
        if not value_signed:
            return redirect(url_for('authRoute.login'))
        g.user = serializer.loads(value_signed)
        return f(*args, **kwargs)
    return wrapper

def verify_turnstile(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.debug('Verify turnstile decorator called')
        
        # Only check Turnstile for POST requests
        if request.method != 'POST':
            logger.info('Not a POST request, skipping Turnstile verification')
            return f(*args, **kwargs)

        # If no token provided, error out. 
        current_token = request.form.get('cf-turnstile-response')
        if not current_token:
            error_msg = 'Turnstile verification failed: no token provided.'
            flash(error_msg, 'error')
            return redirect(request.referrer or url_for('appRoute.home'))

        # Verify Trunstile token 
        remote_ip = request.remote_addr
        verify_response = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={'secret': current_app.config['turnstile_secret'], 'response': current_token, 'remoteip': remote_ip}
        ).json()

        logger.debug(f'Turnstile verify response: {verify_response}')
        if not verify_response.get('success'):
            flash('Turnstile verification failed.', 'error')
            return redirect(request.referrer or url_for('appRoute.home'))
        return f(*args, **kwargs)
    return decorated_function