import os
from logging import FileHandler, StreamHandler, Formatter, getLogger
from flask import Flask
from .config import Config
from .routes import main_routes

def create_app():
    app = Flask(__name__, template_folder='./templates', static_folder='./static')
    app.config.from_object(Config)

    log_directory = './log'
    os.makedirs(log_directory, exist_ok=True)

    formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger = getLogger(__name__)
    logger.setLevel(app.config['LOG_LEVEL'])

    stream_handler = StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = FileHandler(filename=f'{log_directory}/app.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.debug('Flask app initialized with logging')

    app.register_blueprint(main_routes)

    return app
