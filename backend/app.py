from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os, requests, fitz  # PyMuPDF is imported as 'fitz'
from dotenv import load_dotenv
import re

load_dotenv()

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'backend', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Groq Setup
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_ID = "llama3-8b-8192"  # ✅ RECOMMENDED for speed & decent output
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# 🟣 Upload Requirements Route (PDF → Text → Classify)
@app.route('/upload-requirements', methods=['POST'])
def upload_requirements():
    if 'pdf' not in request.files:
        return jsonify({"error": "No PDF uploaded"}), 400

    pdf_file = request.files['pdf']
    if pdf_file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    save_path = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
    pdf_file.save(save_path)

    # ✅ Extract text
    with fitz.open(save_path) as doc:
        text = "\n".join(page.get_text() for page in doc)

    # ✅ Format prompt
    prompt = f"Classify each sentence into one of the SDLC phases (Requirements, Design, Development, Testing, Deployment). Format each as:\nText: <sentence>\nPhase: <phase>\nConfidence: <value from 0 to 1>\n\n{text}"

    # ✅ Call Groq
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": "You are an expert SDLC classifier"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }
    )

    result = response.json()
    print("Groq Response:", result)

    try:
        # ✅ Parse plain text result into structured format
        raw_text = result["choices"][0]["message"]["content"]
        grouped = {
            "Requirements": [],
            "Design": [],
            "Development": [],
            "Testing": [],
            "Deployment": [],
            "Others": []
        }

        current_text = ""
        current_phase = ""
        current_confidence = 1.0

        for line in raw_text.splitlines():
            line = line.strip()
            if line.startswith("Text:"):
                current_text = line.replace("Text:", "").strip()
            elif line.startswith("Phase:"):
                current_phase = line.replace("Phase:", "").strip()
            elif line.startswith("Confidence:"):
                try:
                    current_confidence = float(line.replace("Confidence:", "").strip())
                except:
                    current_confidence = 1.0

                if current_phase not in grouped:
                    current_phase = "Others"

                grouped[current_phase].append({
                    "text": current_text,
                    "confidence": current_confidence
                })

        return jsonify({
            "success": True,
            "classified_requirements": grouped
        })

    except Exception as e:
        return jsonify({"error": "Failed to parse Groq response", "details": str(e), "raw": result}), 500

#Scenario-2 code generation
@app.route('/generate-code', methods=['POST'])
def generate_code():
    data = request.get_json()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    groq_response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama3-8b-8192",  # or another live Groq-supported model
            "messages": [
                {"role": "system", "content": "You are a coding assistant that returns clean, production-ready code."},
                {"role": "user", "content": f"Write code for: {prompt}"}
            ],
            "temperature": 0.5
        }
    )

    result = groq_response.json()
    print("Groq Code Response:", result)

    if "choices" in result and result["choices"]:
       raw_code = result["choices"][0]["message"]["content"]
    # Clean markdown code block syntax if present
       cleaned = re.sub(r"```(?:\w+)?\n(.*?)```", r"\1", raw_code, flags=re.DOTALL).strip()
       return jsonify({"code": cleaned})
    else:
        return jsonify({"error": "Groq code generation failed", "details": result}), 500

#Scenario-3 BuG Fixer
@app.route('/fix-bug', methods=['POST'])
def fix_bug():
    try:
        data = request.get_json()
        code = data.get("code", "")
        language = data.get("language", "python")

        if not code:
            return jsonify({"success": False, "error": "No code provided"}), 400

        full_prompt = (
            f"Fix the bugs in the following {language} code and explain what was wrong:\n\n"
            f"{code}\n\n"
            f"Return only the corrected code first, then a short explanation."
        )

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": "You are a helpful AI programming assistant."},
                    {"role": "user", "content": full_prompt}
                ],
                "temperature": 0.7
            }
        )

        result = response.json()
        print("Groq Bug Fix Response:", result)  # Debug in terminal

        if 'choices' in result:
            fixed_code = result['choices'][0]['message']['content']
            return jsonify({"success": True, "fixed_code_response": fixed_code})
        else:
            return jsonify({"success": False, "error": "Unexpected Groq response", "details": result}), 500

    except Exception as e:
        return jsonify({"success": False, "error": "Server error", "details": str(e)}), 500

#Scenario -4 Test Case Generator
def call_groq(prompt):
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL_ID,
            "messages": [
                {"role": "system", "content": "You are a test case generation expert."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.4
        }
    )
    result = response.json()
    print("Groq Test Case Response:", result)

    if "choices" in result:
        return result["choices"][0]["message"]["content"]
    else:
        raise Exception("Groq failed to generate test cases")


@app.route('/generate-tests', methods=['POST'])
def generate_tests():
    data = request.get_json()
    code = data.get("code", "").strip()
    requirement = data.get("requirement", "").strip()
    framework = data.get("framework", "unittest")

    if not code and not requirement:
        return jsonify({"success": False, "error": "Code or requirement must be provided"}), 400

    # Prepare prompt
    prompt_parts = [f"Generate test cases using {framework} framework."]
    if requirement:
        prompt_parts.append(f"The requirement is: {requirement}")
    if code:
        prompt_parts.append(f"The code to be tested is:\n{code}")

    prompt = "\n".join(prompt_parts)

    try:
        test_output = call_groq(prompt)
        return jsonify({
            "success": True,
            "generated_tests": test_output
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to generate test cases: {str(e)}"
        }), 500

#Scenario-5 Code Summarizer
@app.route('/summarize-code', methods=['POST'])
def summarize_code():
    data = request.get_json()
    code = data.get("code", "").strip()

    if not code:
        return jsonify({"success": False, "error": "No code provided"}), 400

    # Prepare prompt
    prompt = f"""
    Analyze the following code and provide a concise summary of what it does:

    ```
    {code}
    ```
    """

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant that summarizes code."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        groq_response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        result = groq_response.json()

        summary = result['choices'][0]['message']['content'] if 'choices' in result else None

        if summary:
            return jsonify({"success": True, "code_summary": summary})
        else:
            return jsonify({"success": False, "error": "Failed to generate summary"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


#Scenario-6 project dashboard
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",  # You can change to "unhealthy" to simulate issues
        "watson_ai_available": True,  # Update based on whether you're using Watson or Groq
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }), 200


#Floating chat bot 
@app.route("/chat", methods=["POST"])
def chat_with_bot():
    data = request.get_json()
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"success": False, "error": "Empty message"}), 400

    try:
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL_ID,
                "messages": [
                    {"role": "system", "content": "You are an intelligent assistant who helps users with Software Development Lifecycle (SDLC), testing, requirements, and coding practices."},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.7
            }
        )

        groq_data = response.json()
        reply = groq_data["choices"][0]["message"]["content"].strip()

        return jsonify({"success": True, "response": reply})

    except Exception as e:
        print("Chatbot Error:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500

# 🔁 Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
