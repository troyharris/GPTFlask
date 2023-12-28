from flask import Flask, render_template, request, jsonify, redirect, url_for
import openai
import os
import base64
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Tells flask-sqlalchemy what database to connect to
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
# Enter a secret key
app.config["SECRET_KEY"] = os.environb[b'FLASK_SECRET_KEY']
# Initialize flask-sqlalchemy extension
db = SQLAlchemy()

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# LoginManager is needed for our application
# to be able to log in and out users
login_manager = LoginManager()
login_manager.init_app(app)

# Create user model
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=True)
    is_admin = db.Column(db.Integer, nullable=True)

class ConversationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.Text, nullable=True)
    conversation = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Represent the object when printed
    def __repr__(self):
        return f'<ConversationHistory {self.id}>'
    
    def toDict(self):
       return dict(id=self.id, title=self.title, conversation=self.conversation)
    
# Initialize app with extension
db.init_app(app)
# Create database within app context
 
with app.app_context():
    db.create_all()

# Creates a user loader callback that returns the user object given an id
@login_manager.user_loader
def loader_user(user_id):
    return Users.query.get(user_id)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    #prompt = request.form['prompt']
    #if len(response_history) == 1 :
    prompt = "hello there?"
    #system_prompt_code = 1
    #system_prompt_code = request.form['system-prompt']
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
    print(system_prompt)
    messages = [{"role": "system", "content": system_prompt}]
    messages += response_history
    print(messages)
    ### If a file was uploaded, load the vision model no matter what and override the system prompt ###
    if image_data and image_data != '':
        print("I found a file")
        #file = request.files['file']
        #base64_image = base64.b64encode(file.read())
        content = [
            {
                "type": "text",
                "text": "What is in this image?"
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
    else:
        print("I did not find a file")
    if model == 'dall-e-3':
        print("generate image")
        image_prompt = request_json["imagePrompt"]
        response = openai.Image.create(
            model="dall-e-3",
            prompt=image_prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        image_url = response.data[0].url
        print("Image URL....")
        print(image_url)
        print("End URL")
        return jsonify(response)
    else:
        response =  openai.ChatCompletion.create(
            #model="gpt-4-1106-preview", 
            model=model,
            messages=messages,
            max_tokens=1024
        )
        print(response)
        response_json = jsonify(response)
        
        #conversation_history_entry = ConversationHistory(
        #    user_id=current_user.id,
        #    conversation=response_json.get_data(as_text=True)  # Or however you want to format the content
        #)
        #db.session.add(conversation_history_entry)
        #db.session.commit()
        
        return response_json

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

@app.route('/add_conversation', methods=['POST'])
@login_required
def add_conversation():
    request_json = request.get_json()
    #print(request_json)
    #response_history = request_json["responseHistory"]
    conversation_json = jsonify(request_json)
    conversation_json_string = conversation_json.get_data(as_text=True)

    messages = [{"role": "system", "content": "You are an expert at taking in OpenAI API JSON chat requests and coming up with a brief one sentance title for the chat history."}]
    prompt = "Give me a short, one sentence title for this chat history: " + conversation_json_string
    messages += [{"role": "user", "content": prompt}]

    response =  openai.ChatCompletion.create(
        model="gpt-3.5-turbo", 
        messages=messages,
        max_tokens=2048
    )

    title = response.choices[0].message.content

    conversation_history_entry = ConversationHistory(
        user_id=current_user.id,
        title = title,
        conversation=conversation_json_string  # Or however you want to format the content
    )
    db.session.add(conversation_history_entry)
    db.session.commit()
    return request_json

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

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route('/settings')
@login_required
def settings():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    users = Users.query.all()
    return render_template('settings.html', users=users)

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

@app.route("/settings/delete_user/<int:id>", methods=["POST"])
@login_required
def delete_user(id):
    user = Users.query.get(id)

    db.session.delete(user)
    db.session.commit()

    return redirect(url_for("settings"))

@app.route("/history/delete_all", methods=["GET", "POST"])
@login_required
def delete_all():
    db.session.query(ConversationHistory).delete()
    db.session.commit()

    return redirect(url_for("history"))