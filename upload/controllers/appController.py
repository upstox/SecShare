from flask import redirect, request, session, url_for, flash, g, current_app, jsonify, render_template
import os, hashlib, time

from shared.utils.logger import logger
from shared.utils.decorators import login_required

@login_required
def home():
    logger.debug('Home request received')
    return render_template(
        'home.html',
        turnstile_site_key = current_app.config['turnstile_site_key']
    )

@login_required
def history():
    logger.debug('History request received')
    user_email = g.user.get('preferred_username')
    logger.debug(f'user_email: {user_email}')
    if not user_email:
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('authRoute.login'))

    # Default to page 1 if no page param
    page = int(request.args.get('page', 1))
    per_page = 20  # Show 20 rows per page

    # Get file manager reader from app.config
    db_manager_reader = current_app.config['db_manager_reader']
    
    # Fetch a 'slice' of uploads from the database
    uploads, total_count = db_manager_reader.get_user_uploads_paginated(user_email, page, per_page)

    # Calculate total pages
    total_pages = (total_count + per_page - 1) // per_page

    return render_template(
        'history.html',
        uploads=uploads,
        page=page,
        total_pages=total_pages
    )

@login_required
def approvals():
    logger.debug('Approvals request received')
    preferred_email = g.user.get('preferred_username')

    # Get file manager reader from app.config
    db_manager_reader = current_app.config['db_manager_reader']

    if not preferred_email:
        flash('You must be logged in to view approvals.', 'error')
        return redirect(url_for('authRoute.login'))

    # Check if the user is actually a manager
    if not db_manager_reader.is_manager(preferred_email):
        flash('''You're not authorized to view this page.''', 'error')
        return redirect(url_for('appRoute.home'))

    # Get search query from URL parameters (using search)
    search_query = request.args.get('search', '').strip()

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    per_page = 20
    offset = (page - 1) * per_page

    if search_query:
        pending_approvals, total_approvals = db_manager_reader.get_pending_approvals_with_search(
            preferred_email, search_query, page, per_page
        )
    else:
        pending_approvals = db_manager_reader.get_pending_approvals(preferred_email)
        total_approvals = len(pending_approvals)
        pending_approvals = pending_approvals[offset:offset+per_page]

    valid_approvals = []
    logger.info(f'Pending approvals list for manager {preferred_email}: {pending_approvals}')

    for approval in pending_approvals:
        manager_password = db_manager_reader.get_stored_manager_password(approval["unique_id"])
        if manager_password:  # Only include approvals with valid passwords
            approval['manager_password'] = manager_password
            valid_approvals.append(approval)
        else:
            logger.warning(f'No manager password for file: {approval["unique_id"]}')

    total_pages = (total_approvals + per_page - 1) // per_page
    logger.info(f'Final valid approvals (vs code) list for {preferred_email}: {valid_approvals}')

    return render_template('approvals.html',
                           approvals=valid_approvals,
                           page=page,
                           total_pages=total_pages)

def health_check():
    logger.debug('Health check request received')
    try:
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500