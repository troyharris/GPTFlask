from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Models
# User model


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=True)
    is_admin = db.Column(db.Boolean, nullable=True)


class Model(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_name = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    is_vision = db.Column(db.Boolean, nullable=False, default=False)
    is_image_generation = db.Column(db.Boolean, nullable=False, default=False)
    is_thinking = db.Column(db.Boolean, nullable=False, default=False)
    api_vendor_id = db.Column(
        db.Integer, db.ForeignKey('api_vendor.id'), nullable=True)
    api_vendor = db.relationship(
        'APIVendor', backref=db.backref('api_vendors', lazy=True))

    def to_dict(self):
        model_obj = {
            "id": self.id,
            "api_name": self.api_name,
            "name": self.name,
            "is_vision": self.is_vision,
            "is_image_generation": self.is_image_generation,
            "is_thinking": self.is_thinking,
            "api_vendor_id": self.api_vendor_id
        }
        return model_obj


class APIVendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        api_vendor_obj = {
            "id": self.id,
            "name": self.name,
        }
        return api_vendor_obj


# ConversationHistory model (for storing conversations)
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
    def to_dict(self):
        return dict(id=self.id, title=self.title, conversation=self.conversation)

# Persona Model (sets the OpenAI system prompt)


class Persona(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    owner = db.relationship('Users', backref=db.backref('personas', lazy=True))

    def to_dict(self):
        persona_obj = {
            "id": self.id,
            "name": self.name,
            "prompt": self.prompt,
            "owner_id": self.owner_id
        }
        return persona_obj

# Output format model


class OutputFormat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    owner = db.relationship(
        'Users', backref=db.backref('output_formats', lazy=True))
    render_type_id = db.Column(
        db.Integer, db.ForeignKey('render_type.id'), nullable=True)
    render_type = db.relationship(
        'RenderType', backref=db.backref('output_formats', lazy=True))

    def to_dict(self):
        render_type = RenderType.query.get(self.render_type_id)
        output_format_obj = {
            "id": self.id,
            "name": self.name,
            "prompt": self.prompt,
            "owner_id": self.owner_id,
            "render_type_name": render_type.name,
            "render_type_id": self.render_type_id
        }
        return output_format_obj

# API Key model


class APIKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    key = db.Column(db.String(255), nullable=False)

# Render Types


class RenderType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        render_type_obj = {
            "id": self.id,
            "name": self.name,
        }
        return render_type_obj

# User Settings

class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('Users', backref=db.backref('settings', lazy=True))
    appearance_mode = db.Column(db.String(10), nullable=False, default='light') # Values: 'dark' or 'light'
    summary_model_preference_id = db.Column(db.Integer, db.ForeignKey('model.id'), nullable=True)
    summary_model_preference = db.relationship('Model')

    def to_dict(self):
        settings_obj = {
            "id": self.id,
            "user_id": self.user_id,
            "appearance_mode": self.appearance_mode,
            "summary_model_preference_id": self.summary_model_preference_id,
            "summary_model_preference": self.summary_model_preference.name if self.summary_model_preference else None,
        }
        return settings_obj