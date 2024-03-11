# GPT Flask

This project is a backend Python Flask application that exposes API endpoints for interacting with both OpenAI and Anthropic APIs for AI chat functionalities. This project is mainly used to be the backend for [Snowgoose](https://github.com/troyharris/snowgoose) which is a frontend The API is documented using Swagger and can be accessed from `/apidocs`.

## Features

- Integration with OpenAI and Anthropic APIs.
- Swagger API documentation
- Authentication system using Clerk.
- PostgreSQL database for storing default data and API keys.

## Prerequisites

Before you begin, ensure you have met the following requirements:

- Python 3.10 or higher installed.
- PostgreSQL installed and running.
- An account and API keys from OpenAI and (optional) Anthropic.
- An account and a secret key from Clerk.

## Installation

Follow these steps to get your development environment set up:

1. Clone the repository:
   ```
   git clone [REPO_URL]
   ```
2. Navigate to the cloned repository directory:
   ```
   cd [REPO_NAME]
   ```
3. Create a PostgreSQL database named `gptflask`.
4. Copy the `.env.example` file to a new file named `.env` and fill in the necessary details:
   - `OPENAI_API_KEY`: Your OpenAI API key.
   - `FLASK_SECRET_KEY`: A secret key for Flask.
   - `POSTGRES_DB`: Should be `gptflask`.
   - `POSTGRES_USER`: Your PostgreSQL username.
   - `POSTGRES_PASS`: Your PostgreSQL password.
   - `POSTGRES_HOST`: Host for your PostgreSQL database, usually `localhost`.
   - `POSTGRES_PORT`: Port for your PostgreSQL database, usually `5432`.
   - `CLERK_SECRET`: Your Clerk secret key.
   - `ANTHROPIC_API_KEY`: Your Anthropic API key.
5. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```
6. Run the scripts to set up the database and generate an API key:
   ```
   python add_default_data.py
   python generate_api_key.py
   ```
   Note: `generate_api_key.py` will print out a new API key. You will need this API key to interact with the API by including a Bearer token in any request. Save this API key. You can generate as many as you'd like.

## Usage

To start the Flask application, run:

```
flask run
```

Access the Swagger documentation at `/apidocs` for details on how to use the API endpoints.

## Production Deployment

Please refer to one of the many guides on the internet for deploying a Flask app for your situation. I have personally deployed using Gunicorn and NGINX.

## Contributing

Contributions to the GPT Flask API are welcome!

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

If you have any questions or feedback, please open an issue in the GitHub issue tracker for this repository.
