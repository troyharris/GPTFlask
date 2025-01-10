from app.model import Persona, OutputFormat, APIKey, db, Model
from app.utils import get_single_api_key, insert_api_key
from app.api import get_token_from_header, ai_request, save_chat, api_chat
import json
from unittest.mock import Mock, patch, MagicMock
import pytest
import flask
import responses
from flask import jsonify

# Mock classes for `Persona` and `OutputFormat`
class MockPersona:
    def __init__(self, id, name, prompt, owner_id):
        self.id = id
        self.name = name
        self.prompt = prompt
        self.owner_id = owner_id
class MockOutputFormat:
    def __init__(self, id, name, prompt, owner_id, render_type_name, render_type_id):
        self.id = id
        self.name = name
        self.prompt = prompt
        self.owner_id = owner_id
        self.render_type_name = render_type_name
        self.render_type_id = render_type_id

@pytest.fixture
def mock_request_data_dalle():
    return {
        "prompt": "Generate a sunset image",
        "model": "dall-e-3"
    }

@pytest.fixture
def mock_request_data_other_model():
    return {
        "prompt": "Write a poem",
        "model": "gpt-3",
        "responseHistory": [{"role": "user", "content": "Start a poem about nature."}],
        "personaId": 1,
        "outputFormatId": 2,
        "imageData": "Base64EncodedString"
    }

def test_insert_api_key(test_client):
    insert_api_key()
    api_key = get_single_api_key()
    assert api_key is not None

def test_openai_request_with_dalle(test_client, mock_request_data_dalle):
    request = Mock()
    request.get_json.return_value = mock_request_data_dalle
    res = ai_request(request)
    # For Dall-E model, it should only include the initial keys
    assert res == {
        "prompt": "Generate a sunset image",
        "model": "dall-e-3",
        "system_prompt": "",
    }

def test_openai_request_with_other_model(test_client, mock_request_data_other_model):
    mock_persona = MockPersona(id=1, name="Test", prompt="Persona Prompt", owner_id=1)
    mock_output_format = MockOutputFormat(id=2, name="Test", prompt="Output Format Prompt", owner_id=1, render_type_id=1, render_type_name="Test Render")

    with test_client.application.app_context():
        with patch('app.model.Persona.query') as mock_persona_query, patch('app.model.OutputFormat.query') as mock_output_format_query:
            mock_persona_query.get.return_value = mock_persona
            mock_output_format_query.get.return_value = mock_output_format
            
            request = Mock()
            request.get_json.return_value = mock_request_data_other_model
            res = ai_request(request)
            # For other models, it should update the dictionary with additional keys
            expected = {
                "prompt": "Write a poem",
                "model": "gpt-3",
                "system_prompt": "Persona Prompt Output Format Prompt",
                "image_data": "Base64EncodedString",
                "persona": mock_persona,
                "output_format": mock_output_format,
                "messages": [{"role": "system", "content": "Persona Prompt Output Format Prompt"},
                            {"role": "user", "content": "Start a poem about nature."}],
            }
            assert res == expected

@patch('openai.ChatCompletion.create')
@responses.activate
def test_save_chat(mock_openai_create, test_client):
    # Mock the Clerk API response
    responses.add(
        responses.GET,
        'https://api.clerk.com/v1/sessions/testSession',
        json={'status': 'active', 'user_id': 'testUser'},
        status=200
    )

    with test_client.application.test_request_context('/api/save_chat', json={
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ],
        "sessionId": "testSession",
        "userId": "testUser",
        "email": "test@example.com"
    }):

        # Mock the OpenAI API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test Chat Title"))]
        mock_openai_create.return_value = mock_response

        # Mock the user object
        mock_user = MagicMock(id=1)

        # Mock the database session
        with patch('app.model.db.session') as mock_db_session:
            # Call the save_chat function
            response = save_chat()

            # Assert the response status code and message
            assert response[1] == 201
            assert response[0].get_json() == {"message": "Successfully saved chat: Test Chat Title"}

            # Assert that the conversation history entry was created and added to the session
            mock_db_session.add.assert_called_once()
            conversation_history_entry = mock_db_session.add.call_args[0][0]
            # assert conversation_history_entry.user_id == 1
            assert conversation_history_entry.title == "Test Chat Title"
            assert conversation_history_entry.conversation == jsonify({
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"}
                ],
                "sessionId": "testSession",
                "userId": "testUser",
                "email": "test@example.com"
            }).get_data(as_text=True)

            # Assert that the session was committed
            mock_db_session.commit.assert_called_once()

@patch('openai.ChatCompletion.create')
@patch('app.api.anthropic_client.messages.create')
@patch('flask.jsonify')
def test_api_chat(mock_openai_create, mock_anthropic_create, mock_jsonify, test_client):
    api_key = get_single_api_key()
    assert api_key is not None
    headers = {'Authorization': f'Bearer {api_key}'}

    mock_persona = MockPersona(id=1, name="Test", prompt="Persona Prompt", owner_id=1)
    mock_output_format = MockOutputFormat(id=2, name="Test", prompt="Output Format Prompt", owner_id=1, render_type_id=1, render_type_name="Test Render")

    with test_client.application.app_context():
            with patch('app.model.Persona.query') as mock_persona_query, patch('app.model.OutputFormat.query') as mock_output_format_query:
                mock_persona_query.get.return_value = mock_persona
                mock_output_format_query.get.return_value = mock_output_format

            # Test case 1: Test with a standard chat model
            with test_client.application.test_request_context('/api/chat', headers=headers, json={
                "model": "gpt-3.5-turbo",
                "prompt": "Testing the API. Respond with a test message.",
                "personaId": 1,
                "outputFormatId": 2,
                "imageData": "",
                "responseHistory": [
                    {
                        "role": "user",
                        "content": "Testing the API. Respond with a test message."
                    }
                ]
            }):
                mock_response = {"choices": [{"message": {"role": "assistant", "content": "Test message"}}]}
                mock_openai_create.return_value = mock_response
                mock_jsonify.return_value = mock_response

                
                response = api_chat()

                assert response.status_code == 200
                assert response.json == {"role": "assistant", "content": "Test message"}

            # Test case 2: Test with an Anthropic model
            mock_anthropic_response = {"content": [{"text": "Anthropic test message"}]}
            
            mock_anthropic_create.return_value = mock_anthropic_response
            mock_jsonify.return_value = mock_anthropic_response

            response = test_client.post('/api/chat', headers=headers, json={
                "model": "claude-3-opus-20240229",
                "prompt": "Testing the API with Anthropic. Respond with a test message.",
                "personaId": mock_persona.id,
                "outputFormatId": mock_output_format.id,
                "imageData": "",
                "responseHistory": [
                    {
                        "role": "user",
                        "content": "Testing the API with Anthropic. Respond with a test message."
                    }
                ]
            })

            assert response.status_code == 200
            assert response.json == {"role": "assistant", "content": "Anthropic test message"}

            # Test case 3: Test with an image upload
            mock_response = {"choices": [{"message": {"role": "assistant", "content": "Image description"}}]}
            mock_openai_create.return_value = mock_response
            mock_jsonify.return_value = mock_response

            response = test_client.post('/api/chat', headers=headers, json={
                "model": "gpt-4-vision-preview",
                "prompt": "Describe the uploaded image.",
                "personaId": mock_persona.id,
                "outputFormatId": mock_output_format.id,
                "imageData": "image_url",
                "responseHistory": []
            })

            print(response.json)
            assert response.status_code == 200
            assert response.json == {'choices': [{'message': {'content': 'Image description', 'role': 'assistant'}}]}

def test_index_route(test_client):
    response = test_client.get('/')
    assert response.status_code == 200

def test_api_personas_unauthorized(test_client):
    response = test_client.get('/api/personas')
    assert response.status_code == 401

def test_add_persona(test_client):
    api_key = get_single_api_key()
    assert api_key is not None
    print(api_key)
    headers = {'Authorization': f'Bearer {api_key}'}
    data = {'name': 'New Persona', 'prompt': 'New prompt'}
    response = test_client.post('/api/personas', headers=headers, json=data)
    assert response.status_code == 201
    assert Persona.query.filter_by(name='New Persona').first() is not None

def test_update_persona(test_client):
    api_key = get_single_api_key()
    assert api_key is not None

    persona = Persona(name='Test Persona', prompt='Test prompt')
    db.session.add(persona)
    db.session.commit()

    headers = {'Authorization': f'Bearer {api_key}'}
    data = {'name': 'Updated Persona', 'prompt': 'Updated prompt'}
    response = test_client.put(f'/api/personas/{persona.id}', headers=headers, json=data)
    assert response.status_code == 200
    assert Persona.query.get(persona.id).name == 'Updated Persona'

def test_delete_persona(test_client):
    api_key = get_single_api_key()
    assert api_key is not None

    persona = Persona(name='Test Persona', prompt='Test prompt')
    db.session.add(persona)
    db.session.commit()

    headers = {'Authorization': f'Bearer {api_key}'}
    response = test_client.delete(f'/api/personas/{persona.id}', headers=headers)
    assert response.status_code == 200
    assert Persona.query.get(persona.id) is None

def test_get_all_models(test_client):
    api_key = get_single_api_key()
    assert api_key is not None

    headers = {'Authorization': f'Bearer {api_key}'}
    response = test_client.get('/api/models', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_get_model_by_api_name(test_client):
    api_key = get_single_api_key()
    assert api_key is not None

    headers = {'Authorization': f'Bearer {api_key}'}

    model = Model(api_name='test-model', name='Test Model')
    db.session.add(model)
    db.session.commit()

    response = test_client.get(f'/api/models/api_name/{model.api_name}', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['name'] == 'Test Model'
