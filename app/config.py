import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class containing settings applicable to all environments."""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DBNAME = os.environ.get("POSTGRES_DB")
    DBUSER = os.environ.get("POSTGRES_USER")
    DBPASSWORD = os.environ.get("POSTGRES_PASS")
    DBHOST = os.environ.get("POSTGRES_HOST")
    DBPORT = os.environ.get("POSTGRES_PORT")
    SQLALCHEMY_DATABASE_URI= f"postgresql://{DBUSER}:{DBPASSWORD}@{DBHOST}:{DBPORT}/{DBNAME}"
    SESSION_COOKIE_SECURE = bool(os.environ.get('SESSION_COOKIE_SECURE', False))
    SESSION_PERMANENT = False
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    CLERK_SECRET = os.environ.get("CLERK_SECRET")

class DevelopmentConfig(Config):
    """Development-specific configuration, inherits from the base Config class."""
    DEBUG = True
    SQLALCHEMY_ECHO = os.environ.get("SQLALCHEMY_ECHO", False)  # Set to True to log SQL queries for debugging

class ProductionConfig(Config):
    """Production-specific configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # Ensure cookies are sent over HTTPS

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# A dictionary to hold the configurations for easy retrieval.
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}