import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from os import environ
import secrets
import string
import argparse


def generate_api_key(length=64):
    """
    Generates a secure API key without quotes or double quotes.
    
    :param length: The length of the API key to generate. Default is 64 characters.
    :return: A string representing the secure API key.
    """
    # Define the characters that can be used in the API key, excluding quotes
    #safe_punctuation = string.punctuation.replace('"', '').replace("'", '')
    characters = string.ascii_letters + string.digits
    
    # Generate a secure random string of the specified length
    secure_key = ''.join(secrets.choice(characters) for i in range(length))
    
    return secure_key

# Function to insert default records into a table
def insert_api_key(name, key):
    load_dotenv()
    # Database connection parameters
    dbname = environ.get("POSTGRES_DB")
    user = environ.get("POSTGRES_USER")
    password = environ.get("POSTGRES_PASS")
    host = environ.get("POSTGRES_HOST")
    port = environ.get("POSTGRES_PORT")

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

    # Prepare the SQL statement with placeholders for parameterized queries
    sql_statement = "INSERT INTO api_key (name, key) VALUES (%s, %s)"
    
    try:
        # Execute the SQL statement with parameters to avoid SQL injection
        cursor.execute(sql_statement, (name, key))
        conn.commit()
    except psycopg2.Error as e:
        print(f"Error inserting record: {e}")
        conn.rollback()
    finally:
        # Close the cursor and the connection
        cursor.close()
        conn.close()

def main():  
    # Setup command-line argument parsing
    parser = argparse.ArgumentParser(description='Generate a secure API key.')
    parser.add_argument(
        'name', 
        type=str, 
        help='The name of the API to associate with this key.'
    )
    parser.add_argument(
        '--length', 
        type=int, 
        default=64, # Default length can be adjusted as needed.
        help='The length of the API key to generate.'
    )
    
    # Parse command-line arguments
    args = parser.parse_args()
    
    # Generate API key
    api_key = generate_api_key(args.length)

    #Insert API key
    insert_api_key(args.name, api_key)
    
    # Output the API name and key
    print(f"Name: {args.name}")
    print(f"Key: {api_key}")

if __name__ == "__main__":
    main()