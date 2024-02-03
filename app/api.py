from flask import Blueprint
from functools import wraps, partial
from flask import Flask, render_template, request, jsonify, abort
from .model import APIKey, Users, OutputFormat, Persona, Model, ConversationHistory, db
import requests
import openai
from .utils import generate_random_password, personas_json, models_json, output_formats_json
import os


api_bp = Blueprint('api', __name__)

openai.api_key = os.environ.get("OPENAI_API_KEY")

def require_api_key(f):
    """
    A decorator to authenticate API key provided in the Bearer token of the Authorization header.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #api_bp.logger.debug('getting API key')
        auth_header = request.headers.get('Authorization')
        # Verify the Authorization header is present and is a Bearer token
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
            key_object = APIKey.query.filter_by(key=token).first()
            if key_object:
                return f(*args, **kwargs)

        # If the API key is not valid, or not provided in the right format, return 401 Unauthorized
        abort(401, description="Invalid or missing API key")
    return decorated_function


def require_clerk_session(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #api_bp.logger.debug('Checking API')
        auth_header = request.headers.get('Authorization')

        if not auth_header or  not auth_header.startswith('Bearer '):
            #api_bp.logger.debug('Invalid or missing API key')
            abort(401, description="Invalid or missing API key")

        #api_bp.logger.debug('Auth header formatted correctly')
        token = auth_header.split(' ', 1)[1]
        key_object = APIKey.query.filter_by(key=token).first()
        
        if not key_object:
            #api_bp.logger.debug('INvalid or missing API key')
            abort(401, description="Invalid or missing API key")
        
        #api_bp.logger.debug('Auth Key successfully verified')

        clerk_secret = os.environ.get("CLERK_SECRET")

        if not clerk_secret: 
            #api_bp.logger.debug('Clerk API Key Missing')
            abort(401, description="Clerk API Key Missing")

        # Retrieve session_id from the JSON body
        data = request.get_json()
        session_id = data.get("sessionId")
        user_id = data.get("userId")
        email = data.get("email")
        if not session_id:
            #api_bp.logger.debug('No session id')
            abort(400, description="Session ID required")

        # Prepare the request
        headers = {
            'Authorization': f'Bearer {clerk_secret}',
            'Content-Type': 'application/json'
        }
        url = f'https://api.clerk.com/v1/sessions/{session_id}'  # Assuming session_id needs to be a part of the URL
        #api_bp.logger.debug(url)

        # Send a request to the Clark API
        response = requests.get(url, headers=headers)

        # Check if the response is okay and the status is active
        if response.status_code == 200:
            response_json = response.json()
            if response_json.get('status') != 'active':
                abort(401, description="Session is not active")
            verified_user_id = response_json.get('user_id')
            if not verified_user_id or verified_user_id == "":
                #api_bp.logger.debug('Clerk User not found')
                abort(401, description="User not found")

            #api_bp.logger.debug(f"recieved user: {user_id} clerk verified user: {verified_user_id}")

            if user_id != verified_user_id:
                abort(401, f"Mismatched Users {user_id} {verified_user_id}")
            
            user = Users.query.filter_by(username=user_id).first()

            if not user:
                #api_bp.logger.debug('Adding user')
                password = generate_random_password()
                user = Users(username=user_id, password=password, email=email)
                db.session.add(user)
                db.session.commit()


        else:
            #api_bp.logger.debug('Clerk User not found')
            abort(401, description="Failed to verify session with Clerk API")

        #api_bp.logger.debug('All good. Auth successful')
        return partial(f, user=user)(*args, **kwargs)

    return decorated_function
        


def openai_request(request):
    request_json = request.get_json()
    response_history = request_json["responseHistory"]
    system_prompt_code = request_json["persona"]
    output_format_code = request_json["outputFormat"]
    prompt = request_json["prompt"]
    image_data = request_json["imageData"]
    model = request_json["model"]
    persona = Persona.query.get(system_prompt_code)
    output_format = OutputFormat.query.get(output_format_code)
    # Persona and Output Format might be blank if its DALLE or Vision.
    system_prompt = ""
    if persona and output_format:
        system_prompt = persona.prompt + " " + output_format.prompt
    messages = [{"role": "system", "content": system_prompt}]
    messages += response_history

    # Create a dictionary with the local variables
    request_dict = {
        "response_history": response_history,
        "system_prompt_code": system_prompt_code,
        "output_format_code": output_format_code,
        "image_data": image_data,
        "model": model,
        "persona": persona,
        "output_format": output_format,
        "system_prompt": system_prompt,
        "prompt": prompt,
        "messages": messages
    }
    return request_dict

# Routing
@api_bp.route('/')
def index():
    return render_template('index.html')

@api_bp.route('/api/test', methods=['POST'])
# @require_api_key
def api_test():
    request_json = request.get_json()
    greeting = request_json["greeting"]
    compiled_greeting = greeting + " world"
    hello_world = {"compiled_greeting": compiled_greeting}
    return jsonify(hello_world)

@api_bp.route('/api/current_user', methods=['POST'])
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

# Personas API page
@api_bp.route('/api/personas', methods=["GET"])
@require_api_key
def api_personas():
    #api_bp.logger.debug('getting personas')
    #if not current_user.is_admin:
    #    return redirect(url_for('index'))
    
    personas = Persona.query.all()
    # personas_json = json.dumps([ob.__dict__ for ob in personas])
    return personas_json(personas)

# Add a persona from the API
@api_bp.route("/api/personas", methods=["POST"])
@require_api_key
def api_add_persona():
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
    
@api_bp.route("/api/personas/<int:id>", methods=["DELETE"])
@require_api_key
def api_delete_persona(id):
    try:
        persona = Persona.query.get(id)
        db.session.delete(persona)
        db.session.commit()
        return jsonify({"message": "Success"}), 201
    except Exception as e:
        return jsonify({"message": "An unexpected error occurred."}), 500

# Models API page
@api_bp.route('/api/models')
def api_models():
    models = Model.query.all()
    return models_json(models)

# Models API page
@api_bp.route('/api/models/api_name/<string:api_name>')
def api_model_api_name(api_name):
    model = Model.query.filter_by(api_name=api_name).first()
    return jsonify(model.toDict())

# Output Formats API page
@api_bp.route('/api/output-formats')
@require_api_key
def api_output_formats():
    #if not current_user.is_admin:
    #    return redirect(url_for('index'))
    
    output_formats = OutputFormat.query.order_by(OutputFormat.id).all()
    # personas_json = json.dumps([ob.__dict__ for ob in personas])
    return output_formats_json(output_formats)

@api_bp.route('/api/output-formats/<int:id>', methods=["GET"])
@require_api_key
def api_output_format(id):
    #if not current_user.is_admin:
    #    return redirect(url_for('index'))
    
    output_format = OutputFormat.query.get(id)
    output_format_obj = output_format.toDict()
    # personas_json = json.dumps([ob.__dict__ for ob in personas])
    return jsonify(output_format_obj)

@api_bp.route("/api/output-formats/<int:id>", methods=["DELETE"])
@require_api_key
def api_delete_output_format(id):
    try:
        output_format = OutputFormat.query.get(id)
        db.session.delete(output_format)
        db.session.commit()
        return jsonify({"message": "Success"}), 201
    except Exception as e:
        return jsonify({"message": "An unexpected error occurred."}), 500

@api_bp.route('/api/chat', methods=['POST'])
@require_api_key
def api_chat():
    request_dict = openai_request(request)

    # If a file was uploaded, load the vision model no matter what and override the system prompt
    if request_dict["image_data"] and request_dict["image_data"] != '':
        prompt = request_dict['prompt']
        image_data = request_dict["image_data"]
        content = [
            {
                "type": "text",
                "text": prompt
            },
            {
                "type": "image_url",
                "image_url": f"{image_data}"
            }
        ]
        request_dict["model"]='gpt-4-vision-preview'
        system_prompt = 'You are a helpful assistant that can describe an image in detail.'
        messages = [{"role": "system", "content": system_prompt}]
        messages += [{"role": "user", "content": content}]
        request_dict["messages"] = messages

        response =  openai.ChatCompletion.create(
            model=request_dict["model"],
            messages=request_dict["messages"],
            max_tokens=1024
        )
        return jsonify(response)

    # If just a standard chat model, we simply pass it our model and messages object
    else: 
        response =  openai.ChatCompletion.create(
            model=request_dict["model"],
            messages=request_dict["messages"]
        )
        return jsonify(response)

@api_bp.route('/api/save_chat', methods=['POST'])
@require_clerk_session
def save_chat(user):
    request_json = request.get_json()
    chat_json = jsonify(request_json)
    chat_json_string = chat_json.get_data(as_text=True)

    # Ask ChatGPT to summerize the conversation as a single sentence and use for the conversation title.
    messages = [{"role": "system", "content": "You are an expert at taking in OpenAI API JSON chat requests and coming up with a brief one sentance title for the chat history."}]
    prompt = "Give me a short, one sentence title for this chat history: " + chat_json_string
    messages += [{"role": "user", "content": prompt}]
    response =  openai.ChatCompletion.create(
        model="gpt-3.5-turbo", 
        messages=messages
    )
    title = response.choices[0].message.content

    # Save the conversation
    conversation_history_entry = ConversationHistory(
        user_id=user.id,
        title = title,
        conversation=chat_json_string  # Or however you want to format the content
    )
    db.session.add(conversation_history_entry)
    db.session.commit()
    return jsonify({"message": f"Successfully saved chat: {title}"}), 201

@api_bp.route('/api/dalle', methods=['POST'])
def api_dalle():
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

@api_bp.route('/api/history', methods=['POST'])
@require_clerk_session
def api_history(user):
    #api_bp.logger.debug(f'fetching history for user id: {user.id}')
    history = ConversationHistory.query.filter_by(user_id=user.id).order_by(ConversationHistory.timestamp.desc()).all()
    histories = []
    for h in history:
        histories.append(h.toDict())
        #api_bp.logger.debug(h.title)
    return jsonify(histories)

@api_bp.route("/api/history/delete/<int:id>", methods=["POST"])
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