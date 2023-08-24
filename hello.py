from flask import Flask, render_template, request, jsonify
import openai
import os
import markdown

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_response', methods=['POST'])
def get_response():
    #print(request.get_json())
    request_json = request.get_json()
    #print(request_json["responseHistory"])
    response_history = request_json["responseHistory"]
    system_prompt_code = request_json["system-prompt"]
    #prompt = request.form['prompt']
    if len(response_history) == 1 :
        prompt = "hello there?"
        system_prompt_code = 1
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
        if system_prompt_code != "6":
            system_prompt = system_prompt + " Format your response as HTML using Bootstrap 5 HTML tags and code. Use hyperlinks to link to resources but only if helpful and possible."
        print(system_prompt)
        messages = [{"role": "system", "content": system_prompt}]
        messages.append(response_history[0])
    else :
        messages = response_history
    print(messages)
    response =  openai.ChatCompletion.create(
        model="gpt-3.5-turbo", 
        messages=messages
    )
    print(response)
    return jsonify(response)
    #if system_prompt_code == "6":
    #    return markdown.markdown(response.choices[0].message["content"], extensions=['fenced_code'])
    #else:
    #    return jsonify(response)
    #    return response.choices[0].message["content"]