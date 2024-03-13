import pytest
from app import create_app
from dotenv import load_dotenv


@pytest.fixture(scope='module')
def test_client():
    load_dotenv()
    flask_app = create_app("testing")  # Assuming you have a TestingConfig in your config.py

    # Flask provides a way to test your application by exposing the Werkzeug test Client
    testing_client = flask_app.test_client()

    # Establish an application context
    ctx = flask_app.app_context()
    ctx.push()

    yield testing_client  # this is where the testing happens!

    ctx.pop()