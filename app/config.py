import os
import logging
from dotenv import load_dotenv

load_dotenv()

class Config:
    PORT = os.getenv('PORT')
    HOST = os.getenv('HOST')
    LOG_LEVEL = os.getenv('LOG_LEVEL') or logging.INFO

    SECRET_KEY = os.getenv('SECRET_KEY') or 'dummy'
    GITHUB_ACCESS_TOKEN = os.getenv('GITHUB_ACCESS_TOKEN') or ''

    SQLALCHEMY_DATABASE_URI = 'sqlite:///issues.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
