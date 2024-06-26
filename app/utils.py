"""
utils.py
--------

Utility module for a Flask application providing essential functionalities including
data serialization to JSON format, password generation, and API key handling.

Functions:
- `personas_json(personas)`: Converts a list of persona objects to JSON format.
- `models_json(models)`: Converts a list of model objects to JSON format.
- `output_formats_json(output_formats)`: Converts a list of output format objects to JSON format.
- `render_types_json(render_types)`: Converts a list of render type objects to JSON format.
- `api_vendors_json(api_vendors)`: Converts a list of API vendor objects to JSON format.
- `generate_random_password()`: Generates a random password. 
  Used for accounts created via Google authentication, where a password is required but not used.
- `get_single_api_key()`: Retrieves the first API key from the database.
- `insert_api_key()`: Generates a new API key, adds it to the database with a 'test' name,
  and commits the change.

The module uses `json` for serialization, `os` and `string` for password generation,
and custom functions and models for API key handling.
"""

import json
import os
import string

from generate_api_key import generate_api_key

from .model import APIKey, db


def personas_json(personas):
    persona_array = []
    for persona in personas:
        persona_obj = persona.to_dict()
        persona_array.append(persona_obj)
    return json.dumps(persona_array)


def models_json(models):
    models_array = []
    for model in models:
        models_array.append(model.to_dict())
    return json.dumps(models_array)


def output_formats_json(output_formats):
    output_formats_array = []
    for output_format in output_formats:
        output_format_obj = output_format.to_dict()
        output_formats_array.append(output_format_obj)
    return json.dumps(output_formats_array)


def render_types_json(render_types):
    render_types_array = []
    for render_type in render_types:
        render_types_array.append(render_type.to_dict())
    return json.dumps(render_types_array)


def api_vendors_json(api_vendors):
    api_vendors_array = []
    for api_vendor in api_vendors:
        api_vendors_array.append(api_vendor.to_dict())
    return json.dumps(api_vendors_array)

# When an account is created via Google, a password still needs to be created but
# doesn't need to be used.


def generate_random_password():
    chars = string.ascii_letters + string.digits + '+/'
    assert 256 % len(chars) == 0  # non-biased later modulo
    pwd_len = 32
    return ''.join(chars[c % len(chars)] for c in os.urandom(pwd_len))


def get_single_api_key():
    apikey = APIKey.query.first()
    return apikey.key


def insert_api_key():
    api_key = generate_api_key()
    new_api_key = APIKey(name="test", key=api_key)
    db.session.add(new_api_key)
    db.session.commit()
