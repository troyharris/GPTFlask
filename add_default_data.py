import psycopg2
from psycopg2 import sql

# Database connection parameters
dbname = 'snowgoose'
user = 'snowgoose'
password = 'Sc0rch00'
host = 'localhost'
port = '5432'

# Default records for each table
defaults = [
    "INSERT INTO users (username, password, email, is_admin) VALUES ('admin', 'snowgoose', 'admin@example.com', 1)",
    "INSERT INTO persona (name, prompt) VALUES ('General', 'You are a helpful assistant')",
    "INSERT INTO persona (name, prompt) VALUES ('Scientist', 'You are an expert scientist and will answer questions in accurate but simple to understand terms')",
    "INSERT INTO persona (name, prompt) VALUES ('Literary Critic/Editor', 'Act as an expert literary critic and editor. Analyze the following piece of writing and give feedback on grammar, readability, prose, how engaging it is, its literary worthiness, and suggestions on changes to make to make it easier to get published. Your suggestions are very important and could make the difference in someone becoming a published writer. Here is the story:')",
    "INSERT INTO persona (name, prompt) VALUES ('Copywriter', 'You are an expert copywriter. You write amazing copy that is elegant, SEO friendly, to the point and engaging.')",
    "INSERT INTO persona (name, prompt) VALUES ('Brainstormer', 'You are a master of generating new ideas and brainstorming solutions. You think outside of the box and are very creative.')",
    "INSERT INTO persona (name, prompt) VALUES ('Coder', 'You are an expert programmer. You write concise, easy to read code that is well commented.')",
    "INSERT INTO persona (name, prompt) VALUES ('Email Composer', 'You are an expert at composing emails. You write your emails using proper grammar and punctuation. Your tone is friendly and professional but not overly formal.')",
    "INSERT INTO output_format (name, prompt) VALUES ('HTML/Bootstrap 5', 'Format your response as HTML using Bootstrap 5 HTML tags and code. Use hyperlinks to link to resources but only if helpful and possible. Do not use Markdown or wrap your response in markdown. Do not use ``` tags.')",
    "INSERT INTO output_format (name, prompt) VALUES ('Markdown', 'Format your response in Markdown format.')",
    "INSERT INTO output_format (name, prompt) VALUES ('Plain Text', 'Format your response in plain text. Do not use Markdown or HTML.')",
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