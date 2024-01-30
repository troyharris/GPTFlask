import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from os import environ

load_dotenv()

# Database connection parameters
dbname = environ.get("POSTGRES_DB")
user = environ.get("POSTGRES_USER")
password = environ.get("POSTGRES_PASS")
host = environ.get("POSTGRES_HOST")
port = environ.get("POSTGRES_PORT")

# Default records for each table
defaults = [
    "INSERT INTO users (username, password, email, is_admin) VALUES ('admin', 'snowgoose', 'admin@example.com', 1)",
    "INSERT INTO render_type (name) VALUES ('markdown')",
    "INSERT INTO render_type (name) VALUES ('html')",
    "INSERT INTO persona (name, prompt) VALUES ('General', 'You are a helpful assistant')",
    "INSERT INTO persona (name, prompt) VALUES ('Scientist', 'You are an expert scientist and will answer questions in accurate but simple to understand terms')",
    "INSERT INTO persona (name, prompt) VALUES ('Literary Critic/Editor', 'Act as an expert literary critic and editor. Analyze the following piece of writing and give feedback on grammar, readability, prose, how engaging it is, its literary worthiness, and suggestions on changes to make to make it easier to get published. Your suggestions are very important and could make the difference in someone becoming a published writer. Here is the story:')",
    "INSERT INTO persona (name, prompt) VALUES ('Copywriter', 'You are an expert copywriter. You write amazing copy that is elegant, SEO friendly, to the point and engaging.')",
    "INSERT INTO persona (name, prompt) VALUES ('Brainstormer', 'You are a master of generating new ideas and brainstorming solutions. You think outside of the box and are very creative.')",
    "INSERT INTO persona (name, prompt) VALUES ('Coder', 'You are an expert programmer. You write concise, easy to read code that is well commented.')",
    "INSERT INTO persona (name, prompt) VALUES ('Email Composer', 'You are an expert at composing emails. You write your emails using proper grammar and punctuation. Your tone is friendly and professional but not overly formal.')",
    "INSERT INTO output_format (name, prompt, render_type_id) VALUES ('Markdown', 'Format your response in Markdown format.', (SELECT id FROM render_type WHERE name = 'markdown'))",
    "INSERT INTO output_format (name, prompt, render_type_id) VALUES ('Plain Text', 'Format your response in plain text. Do not use Markdown or HTML.', (SELECT id FROM render_type WHERE name = 'html'))",
    "INSERT INTO output_format (name, prompt, render_type_id) VALUES ('HTML/Tailwind', 'Format your response as HTML using Bootstrap 5 HTML tags and code. Use hyperlinks to link to resources but only if helpful and possible. Do not use Markdown or wrap your response in markdown. Only include what is between the html body tag. Do not use ``` tags.', (SELECT id FROM render_type WHERE name = 'html'))",
    "INSERT INTO model (api_name, name, is_vision, is_image_generation) VALUES ('gpt-4-turbo-preview', 'GPT-4 Turbo', true, false)",
    "INSERT INTO model (api_name, name, is_vision, is_image_generation) VALUES ('gpt-4', 'GPT-4 Classic', false, false)",
    "INSERT INTO model (api_name, name, is_vision, is_image_generation) VALUES ('gpt-3.5-turbo', 'GPT 3.5 Turbo', false, false)",
    "INSERT INTO model (api_name, name, is_vision, is_image_generation) VALUES ('dall-e-3', 'DALL-E-3', false, true)",
]

# Connect to the PostgreSQL database
conn = psycopg2.connect(
    dbname=dbname,
    user=user,
    password=password,
    host=host,
    port=port
)

# Create a cursor object
cursor = conn.cursor()

# Function to insert default records into a table
def insert_default_records(default_records):
    # Generate the SQL for insert ignoring duplicates
    # Assuming each table has a unique constraint on the first column

    for record in default_records:
        query = sql.SQL(record)
        try:
            cursor.execute(query)
        except psycopg2.Error as e:
            print(f"Error inserting record: {e}")
            conn.rollback()
        else:
            conn.commit()

# Insert default records into tables
insert_default_records(defaults)


# Close the cursor and the connection
cursor.close()
conn.close()