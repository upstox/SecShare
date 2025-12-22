from flask import render_template, request, redirect, url_for, flash, g, current_app
from upload.models.adminModel import AdminModel

from shared.utils.decorators import login_required
from shared.utils.logger import logger
import re

@login_required
def home():
    if not is_admin():
        logger.warning('Unauthorized admin access attempt by %s', g.user.get('preferred_username'))
        flash('You are not authorized to access the admin page.', 'error')
        return redirect(url_for('appRoute.home'))
    logger.info('Admin home accessed by %s', g.user.get('preferred_username'))
    return render_template('/admin/home.html')  # Create a simple template with links to the following pages.

def is_admin():
    '''Helper: check if the current user is allowed to access admin pages.'''
    username = g.user.get('preferred_username', '')
    if username is None:
        username = ''
    current_user = username.strip().lower()
    allowed = [email.strip().lower() for email in current_app.config['admin_access'].split(',')]
    return current_user in allowed

@login_required
def employee_manager_details():
    if not is_admin():
        logger.warning('Unauthorized access to employee_manager_details by %s', g.user.get('preferred_username'))
        flash('Unauthorized access.', 'error')
        return redirect(url_for('appRoute.home'))
    
    # Get search query from URL parameters
    search_query = request.args.get('search', '').strip()

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    per_page = 20

    # Use AdminModel for database operations
    admin_model = AdminModel(
        current_app.config['db_manager_reader'],
        current_app.config['db_manager_writer']
    )
    
    data = admin_model.get_employee_manager_details_with_search(search_query, page, per_page)
    
    return render_template(
        'admin/table.html', 
        title='Employee Manager Details', 
        results=data['results'],
        columns=data['columns'],
        page=page,
        total_pages=data['total_pages'],
        search=search_query,  # Pass search term to the template
        search_placeholder='Search employees...'
    )

# 2. View file_metadata table with pagination and search
@login_required
def file_metadata():
    if not is_admin():
        flash('Unauthorized access.', 'error')
        return redirect(url_for('appRoute.home'))
    
    search_query = request.args.get('search', '').strip()

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    per_page = 20

    # Use AdminModel for database operations
    admin_model = AdminModel(
        current_app.config['db_manager_reader'],
        current_app.config['db_manager_writer']
    )
    
    data = admin_model.get_file_metadata_with_search(search_query, page, per_page)
    
    return render_template(
        'admin/table.html', 
        title='File Metadata', 
        results=data['results'],
        columns=data['columns'],
        page=page,
        total_pages=data['total_pages'],
        search=search_query,
        search_placeholder='Search file name...'
    )

# 3. View file_metadata_archive table with pagination and search
@login_required
def file_metadata_archive():
    if not is_admin():
        flash('Unauthorized access.', 'error')
        return redirect(url_for('appRoute.home'))
    
    search_query = request.args.get('search', '').strip()

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    per_page = 20

    # Use AdminModel for database operations
    admin_model = AdminModel(
        current_app.config['db_manager_reader'],
        current_app.config['db_manager_writer']
    )
    
    data = admin_model.get_file_metadata_archive_with_search(search_query, page, per_page)
    
    return render_template(
        'admin/table.html', 
        title='File Metadata Archive', 
        results=data['results'],
        columns=data['columns'],
        page=page,
        total_pages=data['total_pages'],
        search=search_query,
        search_placeholder='Search file name...'
    )

# 4. Update manager email for a given employee (only allow updating manager_email)
@login_required
def update_manager_email():
    if not is_admin():
        logger.warning('Unauthorized access to update_manager_email by %s', g.user.get('preferred_username'))
        flash('Unauthorized access.', 'error')
        return redirect(url_for('appRoute.home'))
        
    if request.method == 'POST':
        employee_email = request.form.get('employee_email', '').strip()
        new_manager_email = request.form.get('new_manager_email', '').strip()
        
        # Check if both fields are provided
        if not employee_email or not new_manager_email:
            flash('Both employee email and new manager email must be provided.', 'error')
            return redirect(url_for('adminRoute.update_manager_email'))
        
        # Basic validation of new manager email format using regex (optional)
        email_regex = r'(^[\w\.\-]+@[\w\.\-]+\.[a-zA-Z]{2,}$)'
        if not re.match(email_regex, new_manager_email):
            flash('Invalid new manager email format.', 'error')
            return redirect(url_for('adminRoute.update_manager_email'))
        
        # Use AdminModel for database operations
        admin_model = AdminModel(
            current_app.config['db_manager_reader'],
            current_app.config['db_manager_writer']
        )
        
        result = admin_model.update_manager_email(
            employee_email, 
            new_manager_email, 
            g.user.get('preferred_username')
        )
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('adminRoute.home'))
        else:
            flash(result['message'], 'error')
            if result['error_type'] == 'not_found':
                return redirect(url_for('adminRoute.update_manager_email'))
            else:
                return redirect(url_for('adminRoute.update_manager_email'))
        
    return render_template('admin/update_manager_email.html')