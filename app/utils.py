import json
import string
import os

def personas_json(personas):
    persona_array = []
    for persona in personas:
        persona_obj = persona.toDict()
        persona_array.append(persona_obj)
    return json.dumps(persona_array)

def models_json(models):
    models_array = []
    for model in models:
        models_array.append(model.toDict())
    return json.dumps(models_array)

def output_formats_json(output_formats):
    output_formats_array = []
    for output_format in output_formats:
        output_format_obj = output_format.toDict()
        output_formats_array.append(output_format_obj)
    return json.dumps(output_formats_array)

def render_types_json(render_types):
    render_types_array = []
    for render_type in render_types:
        render_types_array.append(render_type.toDict())
    return json.dumps(render_types_array)

# When an account is created via Google, a password still needs to be created but doesn't need to be used.
def generate_random_password():
    chars = string.ascii_letters + string.digits + '+/'
    assert 256 % len(chars) == 0  # non-biased later modulo
    PWD_LEN = 32
    return ''.join(chars[c % len(chars)] for c in os.urandom(PWD_LEN))