from flask import Blueprint, render_template, session

errors = Blueprint('errors', __name__)

@errors.app_errorhandler(404)
def error_404(error):

    # In flask, the second value is a status code, and is always defaulted as '200', but here we change to '404'
    return render_template('errors/404.html', ptitle="404 Error"), 404


@errors.app_errorhandler(403)
def error_403(error):

    return render_template('errors/403.html', ptitle="403 Error"), 403


@errors.app_errorhandler(500)
def error_500(error):

    return render_template('errors/500.html', ptitle="500 Error"), 500


@errors.context_processor
def context_processor():
    return dict(avatar_key=session['nav_avatar'])