import sqlite3

def init_database():
    # Connect to SQLite database (creates it if it doesn't exist)
    conn = sqlite3.connect('prompts.db')
    cursor = conn.cursor()
    
    # Create prompts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            prompt_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert some sample prompts
    sample_prompts = [
        ("Story Generator", "Write a short story about a {topic} in 100 words"),
        ("Email Helper", "Write a professional email about {topic}"),
        ("Code Explainer", "Explain this code in simple terms: {code}"),
        ("Recipe Creator", "Create a recipe for {dish} with simple ingredients"),
    ]
    
    cursor.executemany(
        "INSERT OR IGNORE INTO prompts (name, prompt_text) VALUES (?, ?)",
        sample_prompts
    )
    
    conn.commit()
    conn.close()
    print("Database initialized with sample prompts!")

if __name__ == "__main__":
    init_database()