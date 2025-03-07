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
from anthropic import Anthropic
import openai
import google.generativeai as genai
from dotenv import load_dotenv

from generate_api_key import generate_api_key

from .model import APIKey, db, UserSettings, Model


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


def get_summary_model(user_id):
    settings = UserSettings.query.filter_by(user_id=user_id).first()
    return Model.query.get(settings.summary_model_preference_id)


def openai_to_google_messages(messages):
    """
    Replace all instances of "content" with "parts" and make it an array
    with a single object in a list of dictionaries.

    Args:
        data (list): A list of dictionaries, each containing 'role' and 'content' keys.

    Returns:
        list: A new list with updated dictionaries where 'content' is replaced by 'parts'.
    """
    # Create a new list to hold the modified dictionaries
    new_messages = []
    del messages[0]
    # Iterate over each dictionary in the input list
    for item in messages:
        # Copy the dictionary to preserve the 'role' key
        new_item = item.copy()

        # Replace "content" with "parts" as an array with a single element
        new_item['parts'] = [item['content']]
        del new_item['content']  # Remove the original 'content' key

        # Add the modified dictionary to the new list
        new_messages.append(new_item)
    return new_messages


def anthropic_request(request):
    anthropic_client = Anthropic()
    # Anthropic does not take the system prompt in the message array,
    # so we need to get rid of it
    messages = request["messages"]
    del messages[0]

    # Anthropic variants support 8192 output tokens. If output token
    # amount is included in the array, use it, otherwise default to 8192.
    # Ensure max_tokens is never None by using the or operator
    print("Max Tokens:")
    print(request["max_tokens"])
    print("Budget Tokens")
    print(request["budget_tokens"])

    max_tokens = request.get("max_tokens") or 8192

    # Check if budget_tokens is in the request
    budget_tokens = request.get("budget_tokens", 0)

    # Build kwargs for the create method
    create_kwargs = {
        "model": request["model"],
        "max_tokens": max_tokens,
        "system": request["system_prompt"],
        "messages": messages
    }

    # Add thinking parameter only if budget_tokens exists and is greater than 0
    if budget_tokens is not None and budget_tokens > 0:
        print("THinking budget set. I will enable thinking mode.")
        create_kwargs["thinking"] = {
            "type": "enabled", "budget_tokens": budget_tokens}
    else:
        print("Thinking mode disabled.")
        create_kwargs["thinking"] = {"type": "disabled"}

    # Call Anthropic's client and send the messages with the appropriate parameters
    response = anthropic_client.messages.create(**create_kwargs)

    # Process the response to include thinking blocks if present
    processed_response = {"role": "assistant"}

    # Create a structured content that includes both thinking and text blocks
    content_blocks = []
    for block in response.content:
        if block.type == "thinking":
            content_blocks.append({
                "type": "thinking",
                "thinking": block.thinking,
                "signature": block.signature
            })
        elif block.type == "redacted_thinking":
            content_blocks.append({
                "type": "redacted_thinking",
                "data": block.data
            })
        elif block.type == "text":
            content_blocks.append({
                "type": "text",
                "text": block.text
            })

    # If there's only one text block and no thinking blocks, return as simple text
    if len(content_blocks) == 1 and content_blocks[0]["type"] == "text":
        processed_response["content"] = content_blocks[0]["text"]
    else:
        processed_response["content"] = content_blocks

    return processed_response


def openai_request(request):
    load_dotenv()
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    response = openai.ChatCompletion.create(
        model=request["model"],
        messages=request["messages"]
    )
    return response["choices"][0]["message"]


def google_request(request):
    load_dotenv()
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    # client = genai.Client(api_key=google_api_key)
    genai.configure(api_key=google_api_key)
    system_instruction = request["system_prompt"]
    messages = openai_to_google_messages(request["messages"])
    print(messages)
    model = genai.GenerativeModel(
        model_name=(request["model"]),
        system_instruction=system_instruction
    )
    response = model.generate_content(
        contents=messages
    )
    print(response)
    model = Model.query.filter_by(api_name=request["model"]).first()
    if model.is_thinking:
        print("Thinking model")
        response_text = "# Inner Thoughts\n" + \
            response.candidates[0].content.parts[0].text + \
            "\n# Response\n" + \
            response.candidates[0].content.parts[1].text
    else:
        print("Not a thinking model")
        response_text = response.text
    return {"role": "assistant", "content": response_text}


def system_prompt_dict(system_prompt, model_name):
    if model_name.startswith("o1"):
        messages = [{"role": "user", "content": system_prompt}]
    else:
        messages = [{"role": "system", "content": system_prompt}]
    return messages
