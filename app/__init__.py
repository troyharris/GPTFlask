from flask import Flask
from .config import config_by_name
from flask_cors import CORS
import openai
from .api import api_bp
import os
import logging
from flask_migrate import Migrate


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    # Further app initialization (extensions, blueprints, etc.)
    CORS(app)
    openai.api_key = app.config["OPENAI_API_KEY"]

    handler = logging.FileHandler('flask_app.log')  # You can specify the path to your log file
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Configure logging
    if os.environ.get('FLASK_ENV') == 'development':
        handler.setLevel(logging.DEBUG)  # Or another level like logging.DEBUG or logging.ERROR
    else:
        handler.setLevel(logging.ERROR)

    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.debug('Debug logging is enabled.')

    from .model import db
    # Initialize Flask-Migrate
    migrate = Migrate(app, db, render_as_batch=True)
    db.init_app(app)

    # Create database within app context if needed
    with app.app_context():
        db.create_all()

    app.register_blueprint(api_bp)
    
    return app