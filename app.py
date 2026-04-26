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
api_key = os.getenv('GEMINI_API_KEY')  # Changed from OPENAI_API_KEY
if not api_key:
    print("❌ GEMINI_API_KEY not found in .env file")
    print("Please create a .env file with: GEMINI_API_KEY=your_key_here")
    print("Get your free key from: https://aistudio.google.com/app/apikey")
    sys.exit(1)

# Configure Gemini
genai.configure(api_key=api_key)

# List available models (optional - to verify)
try:
    models = genai.list_models()
    print("✅ Gemini API configured successfully")
    print("📦 Available models:")
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            print(f"   - {model.name}")
except Exception as e:
    print(f"❌ Failed to configure Gemini: {e}")
    sys.exit(1)

# Initialize the model (using gemini-pro for text)
model = genai.GenerativeModel('gemini-2.5-flash')

# Database helper function
def get_db():
    conn = sqlite3.connect('prompts.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database on startup
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            prompt_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert sample prompts if table is empty
    cursor.execute('SELECT COUNT(*) FROM prompts')
    count = cursor.fetchone()[0]
    
    if count == 0:
        sample_prompts = [
    ("Story Generator", "Write a short story about a {topic} in 100 words"),
    ("Email Helper", "Write a professional email about {topic}"),
    ("Code Explainer", "Explain this code in simple terms: {code}"),
    ("Recipe Creator", "Create a recipe for {dish} with simple ingredients"),
    ("Interview Prep", "Give me 10 common interview questions and answers for a {role} position"),
    ("Travel Planner", "Create a 3-day travel itinerary for {destination} with must-see spots and food recommendations"),
    ("Product Description", "Write a compelling product description for {product} that highlights its benefits and features"),
]
        
        cursor.executemany(
            "INSERT INTO prompts (name, prompt_text) VALUES (?, ?)",
            sample_prompts
        )
        print("✅ Sample prompts added to database")
    
    conn.commit()
    conn.close()

# Initialize DB
init_db()

@app.route('/api/prompts', methods=['GET'])
def get_prompts():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, prompt_text FROM prompts')
    prompts = cursor.fetchall()
    conn.close()
    
    prompts_list = [dict(prompt) for prompt in prompts]
    return jsonify(prompts_list)

@app.route('/api/execute', methods=['POST'])
def execute_prompt():
    data = request.json
    prompt_id = data.get('promptId')
    user_input = data.get('userInput', {})
    
    # Get the prompt from database
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT prompt_text FROM prompts WHERE id = ?', (prompt_id,))
    prompt_record = cursor.fetchone()
    conn.close()
    
    if not prompt_record:
        return jsonify({'error': 'Prompt not found'}), 404
    
    # Get the prompt template
    prompt_template = prompt_record['prompt_text']
    
    # Replace placeholders with user input
    final_prompt = prompt_template
    for key, value in user_input.items():
        final_prompt = final_prompt.replace(f'{{{key}}}', value)
    
    # Enhance the prompt for longer responses
    if "recipe" in final_prompt.lower():
        final_prompt = final_prompt + "\n\nPlease provide a detailed recipe with:\n- List of ingredients with measurements\n- Step-by-step cooking instructions\n- Cooking time and servings\n- Tips for best results"
    elif "story" in final_prompt.lower():
        final_prompt = final_prompt + "\n\nPlease write a complete story with:\n- Beginning, middle, and end\n- Character descriptions\n- Descriptive details\n- Minimum 300 words"
    elif "email" in final_prompt.lower():
        final_prompt = final_prompt + "\n\nPlease write a complete, professional email with:\n- Clear subject line\n- Proper greeting\n- Well-structured body paragraphs\n- Professional closing"
    elif "code" in final_prompt.lower():
        final_prompt = final_prompt + "\n\nPlease provide a detailed explanation with:\n- Line-by-line breakdown\n- Best practices\n- Common pitfalls to avoid\n- Code examples"
    elif "interview" in final_prompt.lower():
        final_prompt = final_prompt + "\n\nPlease provide:\n- 10 realistic interview questions\n- A strong sample answer for each\n- Tips on what interviewers look for"
    elif "travel" in final_prompt.lower():
        final_prompt = final_prompt + "\n\nPlease include:\n- Morning, afternoon, and evening activities per day\n- Recommended local restaurants\n- Transport tips between locations\n- Budget estimates where possible"
    elif "product" in final_prompt.lower():
        final_prompt = final_prompt + "\n\nPlease include:\n- A punchy headline\n- Key benefits in plain language\n- Who it's ideal for\n- A short call-to-action"
    try:
        print(f"🔄 Sending to Gemini: {final_prompt[:100]}...")
        
        # Call Gemini API with updated parameters for longer responses
        response = model.generate_content(
            final_prompt,
            generation_config={
                'max_output_tokens': 2048,  # Increased from 500
                'temperature': 0.7,
                'top_p': 0.95,
                'top_k': 40,
            }
        )
        
        # Extract response
        if response.text:
            llm_response = response.text
            print(f"✅ Gemini response received: {len(llm_response)} characters")
        else:
            llm_response = "No response generated"
            print("⚠️ Empty response from Gemini")
        
        return jsonify({
            'success': True,
            'response': llm_response,
            'prompt_used': final_prompt,
            'model': 'gemini-2.0-flash',
            'length': len(llm_response)
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/models', methods=['GET'])
def list_models():
    """Optional endpoint to see available models"""
    try:
        models = genai.list_models()
        model_list = []
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                model_list.append({
                    'name': model.name,
                    'display_name': model.display_name,
                    'description': model.description[:100] + '...' if model.description else ''
                })
        return jsonify(model_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print(f"🐍 Python version: {sys.version}")
    print("🚀 Starting Flask server on http://localhost:5000")
    print("📝 API endpoints:")
    print("   GET  /api/prompts  - List all prompts")
    print("   POST /api/execute  - Execute a prompt with Gemini")
    print("   GET  /api/models   - List available Gemini models")
    app.run(debug=True, port=5000, host='localhost')