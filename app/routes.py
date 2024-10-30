import logging
from flask import Blueprint, render_template, redirect, url_for, request, session
from .logics import get_related_issues
from .exceptions import MissingFieldsError, RepositoryNotFoundError

main_routes = Blueprint('main_routes', __name__)
logger = logging.getLogger(__name__)

@main_routes.route('/')
def index():
    logger.debug('Index is called')
    form_data = session.pop("form_data", {})
    issues = session.pop('issues', [])
    detail = session.pop('detail', {})
    error_message = session.pop('error_message', None)

    return render_template('index.html', form_data=form_data, issues=issues, detail=detail, error_message=error_message)

@main_routes.route('/search', methods=['POST'])
def search():
    logger.debug('Search is called')
    try:
        issues, detail = get_related_issues(request.form)
        session['issues'] = issues
        session['detail'] = detail
    except (MissingFieldsError, RepositoryNotFoundError) as e:
        logger.error(str(e))
        session['error_message'] = str(e)
    except Exception as e:
        logger.error("An unexpected error occurred: " + str(e))
        session['error_message'] = "An unexpected error occurred. Please try again."
    
    session['form_data'] = request.form.to_dict()
    return redirect(url_for('main_routes.index'))