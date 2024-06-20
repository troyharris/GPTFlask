import os
from functools import partial, wraps

import openai
import requests
from anthropic import Anthropic
from dotenv import load_dotenv
from flask import Blueprint, abort, jsonify, render_template, request

from .model import (APIKey, APIVendor, ConversationHistory, Model,
                    OutputFormat, Persona, RenderType, Users, db)
from .utils import (api_vendors_json, generate_random_password, models_json,
                    output_formats_json, personas_json, render_types_json)

api_bp = Blueprint('api', __name__)
load_dotenv()

openai.api_key = os.environ.get("OPENAI_API_KEY")
anthropic_client = Anthropic()


def get_token_from_header():
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ', 1)[1]
    print("No auth header token")
    return None


def get_api_key_or_abort(token):
    key_object = APIKey.query.filter_by(key=token).first()
    if not key_object:
        abort(401, description="Invalid or missing API key")
    return key_object


def require_api_key(f):
    """
    A decorator to authenticate API key provided in the Bearer token of the Authorization header.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_header()
        get_api_key_or_abort(token)
        return f(*args, **kwargs)
    return decorated_function


def require_clerk_session(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        clerk_secret = os.environ.get("CLERK_SECRET")

        if not clerk_secret:
            # api_bp.logger.debug('Clerk API Key Missing')
            abort(401, description="Clerk API Key Missing")

        # Retrieve session_id from the JSON body
        data = request.get_json()
        session_id = data.get("sessionId")
        user_id = data.get("userId")
        email = data.get("email")
        if not session_id:
            # api_bp.logger.debug('No session id')
            abort(400, description="Session ID required")

        # Prepare the request
        headers = {
            'Authorization': f'Bearer {clerk_secret}',
            'Content-Type': 'application/json'
        }
        # Assuming session_id needs to be a part of the URL
        url = f'https://api.clerk.com/v1/sessions/{session_id}'
        # api_bp.logger.debug(url)

        # Send a request to the Clark API
        response = requests.get(url, headers=headers)

        # Check if the response is okay and the status is active
        if response.status_code == 200:
            response_json = response.json()
            if response_json.get('status') != 'active':
                abort(401, description="Session is not active")
            verified_user_id = response_json.get('user_id')
            if not verified_user_id or verified_user_id == "":
                # api_bp.logger.debug('Clerk User not found')
                abort(401, description="User not found")

            # api_bp.logger.debug(f"recieved user: {user_id} clerk verified user: {verified_user_id}")

            if user_id != verified_user_id:
                abort(401, f"Mismatched Users {user_id} {verified_user_id}")

            user = Users.query.filter_by(username=user_id).first()

            if not user:
                # api_bp.logger.debug('Adding user')
                password = generate_random_password()
                user = Users(username=user_id, password=password, email=email)
                db.session.add(user)
                db.session.commit()

        else:
            # api_bp.logger.debug('Clerk User not found')
            abort(401, description="Failed to verify session with Clerk API")

        # api_bp.logger.debug('All good. Auth successful')
        return partial(f, user=user)(*args, **kwargs)

    return decorated_function


def openai_request(post_request):
    """
    Process a POST request for an AI model, preparing data for the request.

    Args:
        post_request (flask.Request): The POST request received from a client.

    Returns:
        dict: A dictionary that contains the processed request data, including prompts,
        model selection, and additional information based on the model and available
        data like persona and output format if applicable.
    """
    request_json = post_request.get_json()
    prompt = request_json["prompt"]
    model = request_json["model"]
    system_prompt = ""
    request_dict = {
        "prompt": prompt,
        "model": model,
        "system_prompt": system_prompt,
    }
    # Dall-E only uses the prompt, so ignore the rest if Dall-E
    if model != "dall-e-3":
        response_history = request_json["responseHistory"]
        persona_id = request_json["personaId"]
        output_format_id = request_json["outputFormatId"]
        image_data = request_json["imageData"]
        model_id = request_json["modelId"]
        persona = Persona.query.get(persona_id)
        output_format = OutputFormat.query.get(output_format_id)
        if persona and output_format:
            request_dict["system_prompt"] = persona.prompt + \
                " " + output_format.prompt
            system_prompt = request_dict["system_prompt"]
        messages = [{"role": "system", "content": system_prompt}]
        messages += response_history
        request_dict_additions = {
            "image_data": image_data,
            "persona": persona,
            "output_format": output_format,
            "messages": messages,
            "model_id": model_id,
        }
        request_dict.update(request_dict_additions)

    return request_dict

# Routing


@api_bp.route('/')
def index():
    return render_template('index.html')


@api_bp.route('/api/current_user', methods=['POST'])
@require_api_key
@require_clerk_session
def api_clerk_test(user):
    user_json = {
        "id": user.id,
        "username": user.username,
        "password": user.password,
        "email": user.email,
        "isAdmin": user.is_admin
    }
    return jsonify(user_json)

# Personas

# Get all personas


@api_bp.route('/api/personas', methods=["GET"])
@require_api_key
def api_personas():
    """
    Get All Personas
    ---
    tags:
      - Personas
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
    responses:
      200:
        description: Returns a list of all personas
        examples:
          application/json: [{"id": 1, "name": "Assistant", "prompt": "You are a helpful assistant."}]
      401:
        description: Unauthorized, invalid or missing API key
    """
    personas = Persona.query.all()
    return personas_json(personas)

# Get single persona


@api_bp.route('/api/personas/<int:id>', methods=["GET"])
@require_api_key
def api_persona(id):
    """
    Get Single Persona
    ---
    tags:
      - Personas
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
      - name: id
        in: path
        type: integer
        required: true
        description: ID of the persona to retrieve
    responses:
      200:
        description: Returns a single persona based on ID
        examples:
          application/json: {"id": 1, "name": "Assistant", "prompt": "You are a helpful assistant."}
      401:
        description: Unauthorized, invalid or missing API key
      404:
        description: The requested persona is not found
      500:
        description: An unexpected error occurred
    """
    try:
        persona = Persona.query.get(id)
    except Exception as e:
        return jsonify({"message": "An unexpected error occurred."}), 500
    return jsonify(persona.to_dict())

# Add a persona


@api_bp.route("/api/personas", methods=["POST"])
@require_api_key
def api_add_persona():
    """
    Add Persona
    ---
    tags:
      - Personas
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
    responses:
      200:
        description: Returns a success message
        examples:
          application/json: {"message": "success"}
      401:
        description: Unauthorized, invalid or missing API key
      500:
        description: An unexpected error occurred
    """
    request_json = request.get_json()

    if not request_json or 'name' not in request_json or 'prompt' not in request_json:
        return jsonify({"message": "Missing 'name' or 'prompt' in request data."}), 400

    try:
        name = request_json["name"]
        prompt = request_json["prompt"]
        new_persona = Persona(name=name, prompt=prompt)

        db.session.add(new_persona)
        db.session.commit()

        return jsonify({"message": "Success"}), 201
    except Exception as e:
        return jsonify({"message": "An unexpected error occurred."}), 500

# Update a Persona


@api_bp.route("/api/personas/<int:persona_id>", methods=["PUT"])
@require_api_key
def api_update_persona(persona_id):
    """
    Update Persona
    ---
    tags:
      - Personas
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
      - name: id
        in: path
        type: integer
        required: true
        description: ID of the persona to update
    responses:
      200:
        description: Returns a success message
        examples:
          application/json: {"message": "Persona updated successfully"}
      400:
        description: No input data provided
        examples:
            application/json: {"message": "No input data provided"}
      401:
        description: Unauthorized, invalid or missing API key
      404:
        description: The requested persona is not found
        examples:
            application/json: {"message": "Persona not found"}
      500:
        description: An unexpected error occurred
        examples:
            application/json: {"message": "An unexpected error occurred."}
    """
    request_json = request.get_json()

    if not request_json:
        return jsonify({"message": "No input data provided"}), 400

    persona = Persona.query.get(persona_id)
    if not persona:
        return jsonify({"message": "Persona not found"}), 404

    name = request_json.get('name')
    prompt = request_json.get('prompt')

    # Validate the received data
    if name is not None:
        persona.name = name
    if prompt is not None:
        persona.prompt = prompt

    try:
        db.session.commit()
        return jsonify({"message": "Persona updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "An unexpected error occurred."}), 500

# Delete a persona


@api_bp.route("/api/personas/<int:id>", methods=["DELETE"])
@require_api_key
def api_delete_persona(id):
    """
    Delete Persona
    ---
    tags:
      - Personas
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
      - name: id
        in: path
        type: integer
        required: true
        description: ID of the persona to update
    responses:
      200:
        description: Returns a success message
        examples:
          application/json: {"message": "Success"}
      401:
        description: Unauthorized, invalid or missing API key
      404:
        description: The requested persona is not found
      500:
        description: An unexpected error occurred
        examples:
            application/json: {"message": "An unexpected error occurred."}
    """
    try:
        persona = Persona.query.get(id)
        db.session.delete(persona)
        db.session.commit()
        return jsonify({"message": "Success"}), 200
    except Exception as e:
        return jsonify({"message": "An unexpected error occurred."}), 500

# Models

# Get all models


@api_bp.route('/api/models')
@require_api_key
def api_models():
    """
    Get All Models
    ---
    tags:
      - Models
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
    responses:
      200:
        description: Returns a list of all personas
        examples:
          application/json: [{"id": 1, "api_name": "gpt-4-turbo-preview", "name": "GPT-4 Turbo", "is_vision": false, "is_image_generation": false, "api_vendor_id": 1}]
      401:
        description: Unauthorized, invalid or missing API key
    """
    models = Model.query.order_by(Model.id).all()
    return models_json(models)

# Get single model


@api_bp.route('/api/models/<int:id>', methods=["GET"])
@require_api_key
def api_model(id):
    """
    Get Single Model by ID
    ---
    tags:
      - Models
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
      - name: id
        in: path
        type: integer
        required: true
        description: ID of the model to retrieve
    responses:
      200:
        description: Returns a single model based on ID
        examples:
          application/json: {"id": 1, "api_name": "gpt-3", "name": "GPT-3", "is_vision": false, "is_image_generation": false, "api_vendor_id": 1}
      401:
        description: Unauthorized, invalid or missing API key
      404:
        description: The requested model is not found
      500:
        description: An unexpected error occurred
    """
    try:
        model = Model.query.get(id)
    except Exception as e:
        return jsonify({"message": "An unexpected error occurred."}), 500
    return jsonify(model.to_dict())

# Get single model by Model's API name


@api_bp.route('/api/models/api_name/<string:api_name>')
def api_model_api_name(api_name):
    """
    Get Single Model by API Name
    ---
    tags:
      - Models
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
      - name: api_name
        in: path
        type: string
        required: true
        description: API name of the model to retrieve
    responses:
      200:
        description: Returns a single model based on API name
        examples:
          application/json: {"id": 1, "api_name": "gpt-3", "name": "GPT-3", "is_vision": false, "is_image_generation": false, "api_vendor_id": 1}
      401:
        description: Unauthorized, invalid or missing API key
      404:
        description: The requested model is not found
      500:
        description: An unexpected error occurred
    """
    model = Model.query.filter_by(api_name=api_name).first()
    return jsonify(model.to_dict())

# Delete a model


@api_bp.route("/api/models/<int:id>", methods=["DELETE"])
@require_api_key
def api_delete_model(id):
    """
    Delete a Model
    ---
    tags:
      - Models
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
      - name: id
        in: path
        type: integer
        required: true
        description: ID of the model to delete
    responses:
      201:
        description: Model deleted successfully
        examples:
          application/json: {"message": "Success"}
      401:
        description: Unauthorized, invalid or missing API key
      404:
        description: The requested model is not found
      500:
        description: An unexpected error occurred
    """
    try:
        model = Model.query.get(id)
        db.session.delete(model)
        db.session.commit()
        return jsonify({"message": "Success"}), 201
    except Exception as e:
        return jsonify({"message": "An unexpected error occurred."}), 500

# Output Formats
# Get all Output Formats


@api_bp.route('/api/output-formats')
@require_api_key
def api_output_formats():
    """
    Get All Output Formats
    ---
    tags:
      - Output Formats
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
    responses:
      200:
        description: Returns a list of all output formats
        examples:
          application/json: [{"id": 1, "name": "Text", "prompt": "Output as text.", "render_type_id": 1}]
      401:
        description: Unauthorized, invalid or missing API key
    """
    # if not current_user.is_admin:
    #    return redirect(url_for('index'))

    output_formats = OutputFormat.query.order_by(OutputFormat.id).all()
    # personas_json = json.dumps([ob.__dict__ for ob in personas])
    return output_formats_json(output_formats)

# Get Single Output Format


@api_bp.route('/api/output-formats/<int:id>', methods=["GET"])
@require_api_key
def api_output_format(id):
    """
    Get Single Output Format
    ---
    tags:
      - Output Formats
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
      - name: id
        in: path
        type: integer
        required: true
        description: ID of the output format to retrieve
    responses:
      200:
        description: Returns a single output format based on ID
        examples:
          application/json: {"id": 1, "name": "Text", "prompt": "Output as text.", "render_type_id": 1}
      401:
        description: Unauthorized, invalid or missing API key
      404:
        description: The requested output format is not found
      500:
        description: An unexpected error occurred
    """
    try:
        output_format = OutputFormat.query.get(id)
    except Exception as e:
        return jsonify({"message": "An unexpected error occurred."}), 500
    return jsonify(output_format.to_dict())

# Add an Output Format from the API


@api_bp.route("/api/output-formats", methods=["POST"])
@require_api_key
def api_add_output_formats():
    """
    Add Output Format
    ---
    tags:
      - Output Formats
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
    responses:
      200:
        description: Returns a success message
        examples:
          application/json: {"message": "success"}
      401:
        description: Unauthorized, invalid or missing API key
      500:
        description: An unexpected error occurred
    """
    request_json = request.get_json()

    if not request_json or 'name' not in request_json or 'prompt' not in request_json:
        return jsonify({"message": "Missing 'name' or 'prompt' in request data."}), 400

    try:
        name = request_json["name"]
        prompt = request_json["prompt"]
        render_type_id = request_json["render_type_id"]
        new_output_format = OutputFormat(
            name=name, prompt=prompt, render_type_id=render_type_id)

        db.session.add(new_output_format)
        db.session.commit()

        return jsonify({"message": "Success"}), 201
    except Exception as e:
        return jsonify({"message": "An unexpected error occurred."}), 500

# Update Output Format


@api_bp.route("/api/output-formats/<int:output_format_id>", methods=["PUT"])
@require_api_key
def api_update_output_format(output_format_id):
    """
    Update Output Format
    ---
    tags:
      - Output Formats
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
      - name: id
        in: path
        type: integer
        required: true
        description: ID of the output format to update
    responses:
      200:
        description: Returns a success message
        examples:
          application/json: {"message": "Success"}
      400:
        description: No input data provided
        examples:
            application/json: {"message": "No input data provided"}
      401:
        description: Unauthorized, invalid or missing API key
      404:
        description: The requested persona is not found
        examples:
            application/json: {"message": "Persona not found"}
      500:
        description: An unexpected error occurred
        examples:
            application/json: {"message": "An unexpected error occurred."}
    """
    request_json = request.get_json()

    if not request_json:
        return jsonify({"message": "No input data provided"}), 400

    output_format = OutputFormat.query.get(output_format_id)
    if not output_format:
        return jsonify({"message": "output_format not found"}), 404

    name = request_json.get('name')
    prompt = request_json.get('prompt')
    render_type_id = request_json.get('render_type_id')

    # Validate the received data
    if name is not None:
        output_format.name = name
    if prompt is not None:
        output_format.prompt = prompt
    if render_type_id is not None:
        output_format.render_type_id = render_type_id

    try:
        db.session.commit()
        return jsonify({"message": "Success"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "An unexpected error occurred."}), 500

# Delete Output Format


@api_bp.route("/api/output-formats/<int:id>", methods=["DELETE"])
@require_api_key
def api_delete_output_format(id):
    """
    Delete Output Format
    ---
    tags:
      - Output Formats
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
      - name: id
        in: path
        type: integer
        required: true
        description: ID of the output format to delete
    responses:
      200:
        description: Returns a success message
        examples:
          application/json: {"message": "Success"}
      401:
        description: Unauthorized, invalid or missing API key
      404:
        description: The requested persona is not found
      500:
        description: An unexpected error occurred
        examples:
            application/json: {"message": "An unexpected error occurred."}
    """
    try:
        output_format = OutputFormat.query.get(id)
        db.session.delete(output_format)
        db.session.commit()
        return jsonify({"message": "Success"}), 201
    except Exception as e:
        return jsonify({"message": "An unexpected error occurred."}), 500

# Render Types
# Get all Render Types


@api_bp.route('/api/render-types', methods=["GET"])
@require_api_key
def api_render_types():
    """
    Get All Render Types
    ---
    tags:
      - Render Types
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
    responses:
      200:
        description: Returns a list of all render types
        examples:
          application/json: [{"id": 1, "name": "Text"}, {"id": 2, "name": "Image"}]
      401:
        description: Unauthorized, invalid or missing API key
    """
    render_types = RenderType.query.all()
    return render_types_json(render_types)


@api_bp.route('/api/api-vendors', methods=["GET"])
@require_api_key
def api_api_vendors():
    """
    Get All API Vendors
    ---
    tags:
      - API Vendors
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
    responses:
      200:
        description: Returns a list of all API vendors
        examples:
          application/json: [{"id": 1, "name": "openai"}, {"id": 2, "name": "anthropic"}]
      401:
        description: Unauthorized, invalid or missing API key
    """
    api_vendors = APIVendor.query.all()
    return api_vendors_json(api_vendors)

# The main chat/conversation endpoint


@api_bp.route('/api/chat', methods=['POST'])
@require_api_key
def api_chat():
    """
    Generate a chat response from selected AI model
    ---
    tags:
      - Chat
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        description: JSON object containing information to generate a chat response
        required: true
        schema:
          type: object
          properties:
            model:
              type: string
            prompt:
              type: string
            personaId:
              type: integer
            outputFormatId:
              type: integer
            responseHistory:
              type: array
              items:
                type: object
                properties:
                    role:
                        type: string
                    content:
                        type: string
            imageData:
              type: string
          example:
            model: "gpt-3.5-turbo"
            prompt: "Testing the API. Respond with a test message."
            personaId: 1
            outputFormatId: 1
            imageData: ""
            responseHistory:
                - role: "user"
                  content: "Testing the API. Respond with a test message."
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
    responses:
      200:
        description: Returns an object with role and content
        examples:
          application/json: > 
            {
                "content": "Test message: This is a test message from the API.",
                "role": "assistant"
            }
      401:
        description: Unauthorized, invalid or missing API key
      500:
        description: An unexpected error occurred
    """
    request_dict = openai_request(request)
    model_id = request_dict["model_id"]
    model = Model.query.get(model_id)

    if not model:
        return jsonify({"message": "Model not found"}), 404

    api_vendor_name = model.api_vendor.name

    print("Is the model a vision model?")
    print(model.is_vision)

    # If a file was uploaded and the model is a vision model, use the vision API and override the system prompt
    if request_dict["image_data"] and request_dict["image_data"] != '' and model.is_vision:
        print("Is a vision model")
        prompt = request_dict['prompt']
        image_data = request_dict["image_data"]
        content = [
            {
                "type": "text",
                "text": prompt
            },
            {
                "type": "image_url",
                "image_url": {"url": image_data, "detail": "low"},
            }
        ]
        system_prompt = 'You are a helpful assistant that can describe an image in detail.'
        messages = [{"role": "system", "content": system_prompt}]
        messages += [{"role": "user", "content": content}]
        request_dict["messages"] = messages

        response = openai.ChatCompletion.create(
            model=request_dict["model"],
            messages=request_dict["messages"],
            max_tokens=1024
        )
        return jsonify(response["choices"][0]["message"])

    # Use the Anthropic client if the API vendor is Anthropic
    elif api_vendor_name.lower() == 'anthropic':
        # Anthropic does not take the system prompt in the message array,
        # so we need to get rid of it
        messages = request_dict["messages"]
        del messages[0]

        # Call Anthropic's client and send the messages.
        response = anthropic_client.messages.create(
            model=request_dict["model"],
            max_tokens=1024,
            system=request_dict["system_prompt"],
            messages=messages
        )
        # We need to convert Anthropic's chat response to be in OpenAI's format
        message = {"role": "assistant",
                   "content": response.content[0].text}
        return jsonify(message)

    # If the API vendor is OpenAI, we simply pass it our model and messages object
    elif api_vendor_name.lower() == 'openai':
        response = openai.ChatCompletion.create(
            model=request_dict["model"],
            messages=request_dict["messages"]
        )
        return jsonify(response["choices"][0]["message"])

# DALLE-3 image generation API


@api_bp.route('/api/dalle', methods=['POST'])
@require_api_key
def api_dalle():
    """
    Generate an image using DALLE-3
    ---
    tags:
      - DALL-E
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        description: JSON object containing the image generation prompt
        required: true
        schema:
          type: object
          properties:
            model:
              type: string
            prompt:
              type: string
      - name: Authorization
        in: header
        type: string
        required: true
        description: API key (Bearer Token)
    responses:
      200:
        description: Returns the generated image information in OpenAI image generation format
        examples:
          application/json: >
            {
              "created": 1589478378,
              "data": [
                {
                  "revised_prompt": "photo of a dog",
                  "url": "https://image.url"
                }
              ]
            }
      401:
        description: Unauthorized, invalid or missing API key
      500:
        description: An unexpected error occurred
    """
    request_dict = openai_request(request)
    prompt = request_dict["prompt"]
    response = openai.Image.create(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1
    )
    # DALL-E-3 returns a response that includes an image URL. The front-end knows what to do with it.
    return jsonify(response)

# Get all history for current user


@api_bp.route('/api/history', methods=['POST'])
@require_api_key
@require_clerk_session
def api_history(user):
    # api_bp.logger.debug(f'fetching history for user id: {user.id}')
    history = ConversationHistory.query.filter_by(user_id=user.id).order_by(
        ConversationHistory.timestamp.desc()).all()
    histories = []
    for h in history:
        histories.append(h.to_dict())
        # api_bp.logger.debug(h.title)
    return jsonify(histories)

# Save chat as a history object


@api_bp.route('/api/save_chat', methods=['POST'])
@require_api_key
@require_clerk_session
def save_chat(user):
    request_json = request.get_json()
    chat_json = jsonify(request_json)
    chat_json_string = chat_json.get_data(as_text=True)

    # Ask ChatGPT to summerize the conversation as a single sentence and use for the conversation title.
    messages = [{"role": "system", "content": "You are an expert at taking in OpenAI API JSON chat requests and coming up with a brief one sentance title for the chat history."}]
    prompt = "Give me a short, one sentence title for this chat history: " + chat_json_string
    messages += [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    title = response.choices[0].message.content

    # Save the conversation
    conversation_history_entry = ConversationHistory(
        user_id=user.id,
        title=title,
        conversation=chat_json_string  # Or however you want to format the content
    )
    db.session.add(conversation_history_entry)
    db.session.commit()
    return jsonify({"message": f"Successfully saved chat: {title}"}), 201

# Delete a histroy object


@api_bp.route("/api/history/delete/<int:id>", methods=["POST"])
@require_api_key
@require_clerk_session
def api_delete_history(id, user):
    try:
        chat = ConversationHistory.query.get(id)
        if chat.user_id == user.id:
            db.session.delete(chat)
            db.session.commit()
            return jsonify({"message": "Successfully deleted history"}), 201

        return jsonify({"message": "Error: Record user did not match logged in user"}), 500
    except Exception as e:
        return jsonify({"message": "An unexpected error occurred."}), 500
