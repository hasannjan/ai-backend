from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from dotenv import load_dotenv
import google.generativeai as genai
import sys

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Get API key
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("GEMINI_API_KEY not found in .env file")
    sys.exit(1)

# Configure Gemini
genai.configure(api_key=api_key)

# Verify models
try:
    models = genai.list_models()
    print("Gemini API configured successfully")
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            print(model.name)
except Exception as e:
    print(f"Failed to configure Gemini: {e}")
    sys.exit(1)

# Initialize model
model = genai.GenerativeModel('gemini-2.5-flash')

# Database helper function
def get_db():
    conn = sqlite3.connect('prompts.db')
    conn.row_factory = sqlite3.Row
    return conn


# GET all prompts
@app.route('/api/prompts', methods=['GET'])
def get_prompts():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, prompt_text FROM prompts')
        prompts = cursor.fetchall()
        conn.close()

        return jsonify([dict(prompt) for prompt in prompts])

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Execute prompt
@app.route('/api/execute', methods=['POST'])
def execute_prompt():
    try:
        data = request.json
        prompt_id = data.get('promptId')
        user_input = data.get('userInput', {})

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT prompt_text FROM prompts WHERE id = ?',
            (prompt_id,)
        )
        prompt_record = cursor.fetchone()
        conn.close()

        if not prompt_record:
            return jsonify({'error': 'Prompt not found'}), 404

        prompt_template = prompt_record['prompt_text']

        final_prompt = prompt_template
        for key, value in user_input.items():
            final_prompt = final_prompt.replace(f'{{{key}}}', str(value))

        if "recipe" in final_prompt.lower():
            final_prompt += "\nProvide ingredients, steps, time, servings, and tips."
        elif "story" in final_prompt.lower():
            final_prompt += "\nWrite a complete story with characters and descriptive detail."
        elif "email" in final_prompt.lower():
            final_prompt += "\nInclude subject, greeting, body, and professional closing."
        elif "code" in final_prompt.lower():
            final_prompt += "\nExplain line-by-line with best practices."
        elif "interview" in final_prompt.lower():
            final_prompt += "\nProvide questions, answers, and interview tips."
        elif "travel" in final_prompt.lower():
            final_prompt += "\nInclude itinerary, food, transport, and budget."
        elif "product" in final_prompt.lower():
            final_prompt += "\nInclude headline, benefits, target audience, and CTA."

        response = model.generate_content(
            final_prompt,
            generation_config={
                'max_output_tokens': 2048,
                'temperature': 0.7,
                'top_p': 0.95,
                'top_k': 40,
            }
        )

        llm_response = response.text if response.text else "No response generated"

        return jsonify({
            'success': True,
            'response': llm_response,
            'prompt_used': final_prompt,
            'model': 'gemini-2.5-flash',
            'length': len(llm_response)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# List Gemini models
@app.route('/api/models', methods=['GET'])
def list_models():
    try:
        models = genai.list_models()
        model_list = []

        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                model_list.append({
                    'name': model.name,
                    'display_name': model.display_name,
                    'description': model.description[:100] if model.description else ''
                })

        return jsonify(model_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Run server
if __name__ == '__main__':
    print(f"Python version: {sys.version}")
    print("Starting Flask server on http://localhost:5000")
    port = int(os.getenv('PORT', 5000))
    app.run(debug=True, port=port, host='0.0.0.0')