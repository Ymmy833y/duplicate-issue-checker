# pylint: disable=C0415

import os
from logging import FileHandler, StreamHandler, Formatter, getLogger
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__, template_folder='./templates', static_folder='./static')
    app.config.from_object(config_class)

    log_directory = './log'
    os.makedirs(log_directory, exist_ok=True)

    formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger = getLogger(__name__)
    logger.setLevel(app.config['LOG_LEVEL'])

    stream_handler = StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if not app.config.get("TESTING", False):
        file_handler = FileHandler(filename=f'{log_directory}/app.log', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    db.init_app(app)

    with app.app_context():
        from app.models import issue_model  # pylint: disable=unused-import
        db.create_all()

    from .routes import main_routes
    app.register_blueprint(main_routes)

    return app
