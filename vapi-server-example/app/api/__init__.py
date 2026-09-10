from flask import Blueprint

api = Blueprint('api', __name__)

from .routes import *  # noqa: E402,F401,F403
