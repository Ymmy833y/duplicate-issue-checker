import os
import logging
from dotenv import load_dotenv

load_dotenv()

class Config:
    PORT = os.getenv('PORT')
    HOST = os.getenv('HOST')
    LOG_LEVEL = os.getenv('LOG_LEVEL') or logging.DEBUG

    SECRET_KEY = os.getenv('SECRET_KEY') or 'dummy'
    GITHUB_ACCESS_TOKEN = os.getenv('GITHUB_ACCESS_TOKEN') or ''
