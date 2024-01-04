"""
A script to interact with OpenAI's ChatGPT and DALL-E models.

This script allows the user to get a text response from ChatGPT and then uses that response
to generate an image using DALL-E. It requires an OpenAI API key and uses a JSON file
for configuration.
"""

import json
import sqlite3
import os
import re
import requests
from openai import OpenAI

def read_json_file(file_path):
    """
    Read data from a JSON file.

    Parameters:
    file_path (str): The path to the JSON file to be read.

    Returns:
    dict: The data read from the JSON file.
    """
    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data

def get_chatgpt_response(client, prompt, model="gpt-3.5-turbo-1106"):
    """
    Get a response from ChatGPT based on the given prompt.

    Parameters:
    client (OpenAI): The OpenAI client instance.
    prompt (str): The prompt to send to ChatGPT.
    model (str): The model to use for the chat completion (default is 'gpt-3.5-turbo-1106').

    Returns:
    str: The content of the response from ChatGPT, or None if an error occurs.
    """
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model=model
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in getting response from ChatGPT: {e}")
        return None


def extract_image_instructions(text, max_length=500):
    """
    Extract key elements from the text to form a concise set of instructions for image generation.

    Parameters:
    text (str): The text from which to extract key elements.
    max_length (int): The maximum character length of the instruction.

    Returns:
    str: A concise set of instructions for image generation.
    """
    # Regular expressions to identify key story elements
    setting_pattern = r"(in a [^\.,]+|on a [^\.,]+|at the [^\.,]+)"
    characters_pattern = r"(a [^\.,]+ man|a [^\.,]+ woman|a [^\.,]+ person|a [^\.,]+ creature)"
    action_pattern = r"(holding a [^\.,]+|standing [^\.,]+|sitting [^\.,]+|lying [^\.,]+)"

    # Extract key elements
    setting = re.search(setting_pattern, text)
    characters = re.findall(characters_pattern, text)
    action = re.search(action_pattern, text)

    # Form the instruction string
    instruction_parts = [setting.group() if setting else "", 
                         ", ".join(characters[:]),  # Limiting to 10 characters for brevity
                         action.group() if action else ""]
    instruction = ", ".join(filter(None, instruction_parts))


    # Truncate if exceeds max length
    if len(instruction) > max_length:
        return instruction[:max_length].rsplit(' ', 1)[0]  # Avoid cutting off mid-word
    return instruction


def create_dalle_image(client, text):
    """
    Create an image using DALL-E based on the text.

    Parameters:
    client (OpenAI): The OpenAI client instance.
    text (str): The text prompt to be used for generating the image.

    Returns:
    str: The URL of the generated image, or None if an error occurs.
    """
    try:
        response = client.images.generate(
            prompt=text,
            n=1,
            size="256x256"
        )
        return response.data[0].url
    except Exception as e:
        print(f"Error in creating image with DALL-E: {e}")
        return None

def save_to_database(cursor, story_info, chat_response, image_url):
    """
    Save story information and responses to an SQL database.

    Parameters:
    cursor (sqlite3.Cursor): The database cursor.
    story_info (dict): The user's story preferences.
    chat_response (str): The response from ChatGPT.
    image_url (str): The URL of the generated image.
    """
    cursor.execute("""
        INSERT INTO stories (story_type, setting, characters, chat_response, image_url)
        VALUES (?, ?, ?, ?, ?)
    """, (story_info['story_type'], story_info['setting'], story_info['characters'], chat_response, image_url))

def download_image(image_url, image_dir):
    response = requests.get(image_url, stream=True)
    response.raise_for_status()
    with open(image_dir, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192): 
            f.write(chunk)

def main():
    # File paths
    file_path = "C:/Users/Denzi/Desktop/Git_Projects/StoryBook/Python/"
    file_name = "data.json"
    image_dir = "C:/Users/Denzi/Desktop/Git_Projects/StoryBook/Python/Images"
    db_path = "C:/Users/Denzi/Desktop/Git_Projects/StoryBook/Python/story_data.db"

    # Read configuration
    data = read_json_file(file_path + file_name)
    openai_api_key = data['KEY']
    client = OpenAI(api_key=openai_api_key)

    # Create/connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY,
            story_type TEXT,
            setting TEXT,
            characters TEXT,
            chat_response TEXT,
            image_url TEXT
        )
    """)

    # User input for story
    story_info = {
        "story_type": input("What kind of story do you want? "),
        "setting": input("What is the setting of the story? "),
        "characters": input("Who are the characters in the story? ")
    }

    # Combine inputs into a prompt
    prompt = f"Craft a childs {story_info['story_type']} story set in {story_info['setting']} with characters {story_info['characters']}."

    # Get ChatGPT response 
    text_response = get_chatgpt_response(client, prompt)

    # create a text prompt for dalle to generate an image from the chatgpt text_response
    prompt = "Images should be child approperate." + f"Summarize this text {text_response}. Encapsulate the essence of the story with a response no more than 800 characters."
    
    # Truncate the prompt if exceeds max length
    max_length = 800
    if len(prompt) > max_length:
        prompt = prompt[:max_length].rsplit(' ', 1)[0]  # Avoid cutting off mid-word
    
    prompt = prompt 

    #create an image from the text response
    image_prompt = get_chatgpt_response(client, prompt)

     # Truncate text if necessary
    image_instructions = extract_image_instructions(image_prompt) if image_prompt else None

    print("\n image text: " + image_instructions)

    # Create image and proceed as before
    image_url = create_dalle_image(client, image_instructions) if image_instructions else None


    # Save to database and display results
    if text_response and image_url:
        save_to_database(cursor, story_info, text_response, image_url)
        conn.commit()

        print(f"\nChatGPT Response: {text_response}")
        print(f"\nGenerated Image URL: {image_url}")

        image_path = f"{image_dir}/{cursor.lastrowid}.png"
        download_image(image_url, image_path)

    # Close database connection
    conn.close()

if __name__ == "__main__":
    main()
