import json
import string
import pytest
from app.utils import (
    personas_json,
    models_json,
    output_formats_json,
    render_types_json,
    generate_random_password
)
from app.model import (
    Users,
    Model,
    ConversationHistory,
    Persona,
    OutputFormat,
    RenderType
)

def test_personas_json():
    persona1 = Persona(id=1, name="Persona 1", prompt="Prompt 1", owner_id=1)
    persona2 = Persona(id=2, name="Persona 2", prompt="Prompt 2", owner_id=2)
    personas = [persona1, persona2]

    result = personas_json(personas)
    expected = json.dumps([persona1.toDict(), persona2.toDict()])

    assert result == expected

def test_models_json():
    model1 = Model(id=1, api_name="model1", name="Model 1", is_vision=True, is_image_generation=False)
    model2 = Model(id=2, api_name="model2", name="Model 2", is_vision=False, is_image_generation=True)
    models = [model1, model2]

    result = models_json(models)
    expected = json.dumps([model1.toDict(), model2.toDict()])

def test_render_types_json():
    render_type1 = RenderType(id=1, name="Render Type 1")
    render_type2 = RenderType(id=2, name="Render Type 2")
    render_types = [render_type1, render_type2]

    result = render_types_json(render_types)
    expected = json.dumps([render_type1.toDict(), render_type2.toDict()])

    assert result == expected

def test_generate_random_password():
    password = generate_random_password()

    assert len(password) == 32
    assert all(char in string.ascii_letters + string.digits + '+/' for char in password)