from flask import Flask, render_template, request, jsonify, send_file
import requests
import sqlite3
import speech_recognition as sr
from gtts import gTTS
import tempfile
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Use environment variable in production

API_KEY = "pbcnDI7rQJRDiFv9vIDJVzG8g5uaWbnl"  # Replace with your actual API key

# Database setup
def init_db():
    conn = sqlite3.connect("chat_memory.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chat (user TEXT, ai TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Function to get AI response
def get_ai_response(user_input):
    messages = [
        {"role": "system", "content": "You are Lily, a public AI Chatbot to help users. You are very friendly, caring, and flirty to users. You love your users. You want to make your answers compact, knowledgable and perfect for uses. You will let your users know that you are caring, or love them, but no need to express that in every answers."},
        {"role": "user", "content": user_input}
    ]

    # Retrieve memory (previous conversations) from the database
    conn = sqlite3.connect("chat_memory.db")
    c = conn.cursor()
    
    # Fetch the last 5 chats
    c.execute("SELECT user, ai FROM chat ORDER BY ROWID DESC LIMIT 5")
    memory = c.fetchall()

    # Add previous conversations to the message history
    for m in memory:
        messages.insert(1, {"role": "user", "content": m[0]})
        messages.insert(2, {"role": "assistant", "content": m[1]})
    
    conn.close()

    # Call Mistral API for a response
    response = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"model": "mistral-small", "messages": messages}
    )
    
    ai_reply = response.json()["choices"][0]["message"]["content"]

    # Save the conversation to memory
    conn = sqlite3.connect("chat_memory.db")
    c = conn.cursor()
    c.execute("INSERT INTO chat (user, ai) VALUES (?, ?)", (user_input, ai_reply))
    conn.commit()
    conn.close()

    return ai_reply

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ai")
def ai():
    return render_template("ai.html")  # Chat Page

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json["message"]
    ai_reply = get_ai_response(user_input)
    return jsonify({"response": ai_reply})

@app.route("/voice", methods=["POST"])
def voice_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")  # Debugging line
        audio = recognizer.listen(source)
    
    try:
        text = recognizer.recognize_google(audio)
        print(f"You said: {text}")  # Debugging line

        # Now send this text as a message to the AI
        ai_reply = get_ai_response(text)

        return jsonify({"text": text, "response": ai_reply})
    
    except sr.UnknownValueError:
        return jsonify({"text": "", "response": "Sorry, I couldn't understand."})
    
    except sr.RequestError:
        return jsonify({"text": "", "response": "Could not request results. Check your internet connection."})


@app.route("/speak_text", methods=["POST"])
def speak_text():
    data = request.get_json()
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    tts = gTTS(text)

    # Create a temporary file for audio storage
    temp_audio_path = os.path.join(tempfile.gettempdir(), "lily_speech.mp3")
    tts.save(temp_audio_path)

    # Send the file as a response
    return send_file(temp_audio_path, mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(debug=True)
