from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
import openai
import os
import base64
import json
import string
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configuration for OAuth
app.config["GOOGLE_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID")
app.config["GOOGLE_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET")
# Ensure SESSION_COOKIE_SECURE is True in production
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_PERMANENT"] = False

# Get the Google OpenID configuration
google_discovery_url = "https://accounts.google.com/.well-known/openid-configuration"
google_discovery = requests.get(google_discovery_url).json()

# Initialize OAuth extension
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config["GOOGLE_CLIENT_ID"],
    client_secret=app.config["GOOGLE_CLIENT_SECRET"],
    access_token_url=google_discovery['token_endpoint'],
    authorize_url=google_discovery['authorization_endpoint'],
    api_base_url=google_discovery['userinfo_endpoint'],
    client_kwargs={'scope': 'openid email profile'},
    userinfo_endpoint=google_discovery['userinfo_endpoint'],
    jwks_uri=google_discovery['jwks_uri'],
    server_metadata_url=google_discovery_url,
)

# Tells flask-sqlalchemy what database to connect to
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
# Enter a secret key
app.config["SECRET_KEY"] = os.environb[b'FLASK_SECRET_KEY']
# Initialize flask-sqlalchemy extension
db = SQLAlchemy()

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Initialize LoginManager for handling user authentication
login_manager = LoginManager()
login_manager.init_app(app)

# Define User model
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=True)
    is_admin = db.Column(db.Integer, nullable=True)

#Define ConversationHistory model (for storing conversations)
class ConversationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.Text, nullable=True)
    conversation = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Represent the object when printed
    def __repr__(self):
        return f'<ConversationHistory {self.id}>'
    
    # Get a dict of the ConversationHistory object
    def toDict(self):
       return dict(id=self.id, title=self.title, conversation=self.conversation)
    
# Initialize SQLAlchemy with app
db.init_app(app)
# Create database within app context if needed
with app.app_context():
    db.create_all()

# Creates a user loader callback that returns the user object given an id
@login_manager.user_loader
def loader_user(user_id):
    return Users.query.get(user_id)

# Set which extentions are allowed for upload. NOTE: Not implemented
#
#ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
#
# Manage allowed 
#def allowed_file(filename):
#    return '.' in filename and \
#           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    
    history = ConversationHistory.query.filter_by(user_id=current_user.id).order_by(ConversationHistory.timestamp.desc()).all()
    return render_template('index.html', history=history)

@app.route('/get_response', methods=['POST'])
def get_response():
    request_json = request.get_json()
    response_history = request_json["responseHistory"]
    system_prompt_code = request_json["system-prompt"]
    image_data = request_json["imageData"]
    model = request_json["model"]

    # Translate system prompt id to system instructions for GPT
    system_prompt = "You are a helpful assistant."
    if system_prompt_code == "2":
        system_prompt = "You are an expert scientist and will answer questions in accurate but simple to understand terms"
    elif system_prompt_code == "3":
        system_prompt = "Act as an expert literary critic and editor. Analyze the following piece of writing and give feedback on grammar, readability, prose, and how engaging the scene is:"
    elif system_prompt_code == "4":
        system_prompt = "You are an expert copywriter. You write amazing copy that is elegant, SEO friendly, to the point and engaging."
    elif system_prompt_code == "5":
        system_prompt = "You are a master of generating new ideas and brainstorming solutions. You think outside of the box and are very creative."
    elif system_prompt_code == "6":
        system_prompt = "You are an expert programmer. You write concise, easy to read code that is well commented. Use Markdown formatting."
    elif system_prompt_code == "7":
        system_prompt = "You are an expert at composing emails. You write your emails using proper grammar and punctuation. Your tone is friendly and professional but not overly formal."
    if system_prompt_code != "6":
        system_prompt = system_prompt + " Format your response as HTML using Bootstrap 5 HTML tags and code. Use hyperlinks to link to resources but only if helpful and possible. Don't use Markdown or wrap your response in markdown. Don't use ``` tags."
 
    # Create the message object and populate it with any chat history
    messages = [{"role": "system", "content": system_prompt}]
    messages += response_history

    # If a file was uploaded, load the vision model no matter what and override the system prompt
    if image_data and image_data != '':
        print("I found a file")
        prompt = request.form['prompt']
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
        model='gpt-4-vision-preview'
        system_prompt = 'You are a helpful assistant that can describe an image in detail.'
        messages = [{"role": "system", "content": system_prompt}]
        messages += [{"role": "user", "content": content}]
    
    # If DALL-E 3 was selected, we use a different type of API call than the others
    if model == 'dall-e-3':
        image_prompt = request_json["imagePrompt"]
        response = openai.Image.create(
            model="dall-e-3",
            prompt=image_prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        # DALL-E-3 returns a response that includes an image URL. The front-end knows what to do with it.
        return jsonify(response)
    # If using the vision model, we need to set max_tokens to get a reasonable output.
    elif model == 'gpt-4-vision-preview':
        response =  openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=1024
        )
        return jsonify(response)
    # If just a standard chat model, we simply pass it our model and messages object
    else: 
        response =  openai.ChatCompletion.create(
            model=model,
            messages=messages
        )
        return jsonify(response)

# Routes to retrieve saved conversations
@app.route('/history', methods=['GET'])
@login_required
def history():
    history = ConversationHistory.query.filter_by(user_id=current_user.id).order_by(ConversationHistory.timestamp.desc()).all()
    return render_template('history.html', history=history)

@app.route('/history/id/<int:id>', methods=['POST'])
@login_required
def single_history(id):
    conversation = ConversationHistory.query.get(id)
    conversation_json = jsonify(conversation.toDict())
    return conversation_json

# Route to save a conversation
@app.route('/add_conversation', methods=['POST'])
@login_required
def add_conversation():
    request_json = request.get_json()
    conversation_json = jsonify(request_json)
    conversation_json_string = conversation_json.get_data(as_text=True)

    # Ask ChatGPT to summerize the conversation as a single sentence and use for the conversation title.
    messages = [{"role": "system", "content": "You are an expert at taking in OpenAI API JSON chat requests and coming up with a brief one sentance title for the chat history."}]
    prompt = "Give me a short, one sentence title for this chat history: " + conversation_json_string
    messages += [{"role": "user", "content": prompt}]
    response =  openai.ChatCompletion.create(
        model="gpt-3.5-turbo", 
        messages=messages,
        max_tokens=4096
    )
    title = response.choices[0].message.content

    # Save the conversation
    conversation_history_entry = ConversationHistory(
        user_id=current_user.id,
        title = title,
        conversation=conversation_json_string  # Or however you want to format the content
    )
    db.session.add(conversation_history_entry)
    db.session.commit()
    return request_json

# Google authentication
@app.route('/login/google', methods=["GET", "POST"])
def google_login():
    redirect_uri = url_for('google_authorize', _external=True, _scheme="https")
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/authorize', methods=["GET", "POST"])
def google_authorize():
    # Get the authorization token
    token = google.authorize_access_token()
    # You can use the token to get user info
    resp = google.get('userinfo', token=token)
    resp.raise_for_status
    user_info = resp.json()

    user = Users.query.filter_by(email=user_info['email']).first()
    if not user:
        password = generate_random_password()
        print("password is: " + password)
        user = Users(username=user_info['name'], password=password, email=user_info['email'])
        db.session.add(user)
        db.session.commit()
    
    # Login the user with Flask-Login
    login_user(user)
    return redirect('/')

# Flask-login to login user
@app.route("/login", methods=["GET", "POST"])
def login():
    # If a post request was made, find the user by
    # filtering for the username
    if request.method == "POST":
        user = Users.query.filter_by(
            username=request.form.get("username")).first()
        # Check if the password entered is the
        # same as the user's password
        if user.password == request.form.get("password"):
            # Use the login_user method to log in the user
            login_user(user)
            return redirect(url_for("index"))
    return render_template("login.html")

# Flask-login to log out user
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

# Settings page
@app.route('/settings')
@login_required
def settings():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    users = Users.query.all()
    return render_template('settings.html', users=users)

# Add a user from the settings page
@app.route("/settings/add_user", methods=["POST"])
@login_required
def add_user():
    username = request.form.get("username")
    password = request.form.get("password")
    email = request.form.get("email")
    is_admin = request.form.get("is_admin")

    new_user = Users(username=username, password=password, email=email, is_admin=is_admin)
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for("settings"))

# Delete a user from the settings page
@app.route("/settings/delete_user/<int:id>", methods=["POST"])
@login_required
def delete_user(id):
    user = Users.query.get(id)

    db.session.delete(user)
    db.session.commit()

    return redirect(url_for("settings"))

# WARNING! For dev purposes only. Will be removed in a future update. Will delete all saved conversations for all users
@app.route("/history/delete_all", methods=["GET", "POST"])
@login_required
def delete_all():
    db.session.query(ConversationHistory).delete()
    db.session.commit()

    return redirect(url_for("history"))

# When an account is created via Google, a password still needs to be created but doesn't need to be used.
def generate_random_password():
    chars = string.ascii_letters + string.digits + '+/'
    assert 256 % len(chars) == 0  # non-biased later modulo
    PWD_LEN = 32
    return ''.join(chars[c % len(chars)] for c in os.urandom(PWD_LEN))