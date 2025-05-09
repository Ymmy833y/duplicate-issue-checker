import logging
import traceback
from flask import Blueprint, render_template, jsonify, request, session
from .services.issue_service import get_related_issues
from .utils.exceptions import (
    MissingFieldsError, RepositoryNotFoundError, RateLimitExceededError,
    UnauthorizedError, IssueFetchFailedError
)

main_routes = Blueprint('main_routes', __name__)
logger = logging.getLogger(__name__)

@main_routes.route('/')
def index():
    logger.debug('Index is called')
    form_data = session.pop('form_data', {})
    error_message = session.pop('error_message', None)

    return render_template(
        'index.html',
        form_data=form_data,
        error_message=error_message
    )

@main_routes.route('/search', methods=['POST'])
async def search():
    logger.debug('Search is called')
    try:
        issues, detail = await get_related_issues(request.get_json())
        return jsonify({
            "issues": issues,
            "detail": detail
        })
    except (
        MissingFieldsError, RepositoryNotFoundError, RateLimitExceededError,
        UnauthorizedError, IssueFetchFailedError
    ) as e:
        logger.error('%s', e)
        logger.error(traceback.format_exc())
        return jsonify({"errorMessage": str(e)}), 400
    except Exception as e:
        logger.error('An unexpected error occurred: %s', e)
        logger.error(traceback.format_exc())
        return jsonify({"errorMessage": 'An unexpected error occurred. Please try again.'}), 500
