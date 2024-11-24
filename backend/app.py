from flask import Flask, request, jsonify, send_from_directory, redirect, url_for, render_template_string
from pdfminer.high_level import extract_text
import os
from openai import OpenAI

# Initialize Flask app
app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

uploaded_file_name = None

# Configure OpenAI API
client = OpenAI()

# Helper function: Use GPT to evaluate the document based on rules
def evaluate_with_gpt(text, rules):
    prompt = f"""
    You are an expert document validator. The following text is extracted from a document:
    "{text}"

    Here are the validation rules:
    {rules}

    Validate the document based on these rules. Provide a report in the format:
    - "File contain empty fields: [Field name 1], [Field name 2]." if file have any empty fields without any value or information.
    - If only the rules are not followed provide suggestions based on the rules only like:
      1. [Suggestion 1]
      2. [Suggestion 2]
    - "File document is correct." if all rules are met.
    """
    try:
        # completion = client.chat.completions.create(
        #     model="gpt-4o-mini",
        #     messages=[
        #         {"role": "system", "content": "You are a document validation expert."},
        #         {"role": "user", "content": prompt}
        #     ]
        # )
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a document validation expert."},
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Error with OpenAI API: {str(e)}"

# Home page
@app.route('/')
def index():
    global uploaded_file_name
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Upload and Validate PDF</title>
    </head>
    <body>
        <h1>Upload and Validate PDF Files</h1>
        <form action="/upload" method="POST" enctype="multipart/form-data">
            <label for="file">Choose a PDF:</label>
            <input type="file" name="file" accept="application/pdf" required>
            <button type="submit">Upload</button>
        </form>

        {% if uploaded_file_name %}
        <h2>Uploaded File:</h2>
        <p><a href="/uploads/{{ uploaded_file_name }}" target="_blank">{{ uploaded_file_name }}</a></p>

        <h2>Validation Rules:</h2>
        <form action="/process" method="POST">
            <textarea name="rules" rows="5" cols="50" placeholder="Enter validation rules, e.g., &#10;1. Date of birth should be in the format dd/mm/yyyy&#10;2. First name should have at least 3 letters" required></textarea>
            <br>
            <button type="submit">Process Document</button>
        </form>

        <form action="/delete" method="POST">
            <input type="hidden" name="filename" value="{{ uploaded_file_name }}">
            <button type="submit">Delete File</button>
        </form>
        {% endif %}
    </body>
    </html>
    ''', uploaded_file_name=uploaded_file_name)

# Upload file
@app.route('/upload', methods=['POST'])
def upload_file():
    global uploaded_file_name

    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    uploaded_file_name = file.filename
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file_name)
    file.save(file_path)

    return redirect(url_for('index'))

# Process file with validation rules
@app.route('/process', methods=['POST'])
def process_document():
    global uploaded_file_name

    if not uploaded_file_name:
        return jsonify({'error': 'No uploaded file to process.'}), 400

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file_name)

    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found.'}), 404

    # Extract text from PDF
    try:
        text = extract_text(file_path)
        # print(text)
    except Exception as e:
        return jsonify({'error': f'Failed to extract text: {str(e)}'}), 500

    # Get rules from user input
    rules = request.form.get('rules', '')
    if not rules.strip():
        return jsonify({'error': 'Validation rules are missing.'}), 400

    # Evaluate using OpenAI GPT
    feedback = evaluate_with_gpt(text, rules)

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Validation Result</title>
    </head>
    <body>
        <h1>Validation Result</h1>
        <pre>{{ feedback }}</pre>
        <a href="/">Go Back</a>
    </body>
    </html>
    ''', feedback=feedback)

# Delete file
@app.route('/delete', methods=['POST'])
def delete_file():
    global uploaded_file_name

    filename = request.form['filename']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if os.path.exists(file_path):
        os.remove(file_path)
        uploaded_file_name = None
        return redirect(url_for('index'))
    else:
        return jsonify({'error': 'File not found'}), 404

# Serve uploaded files
@app.route('/uploads/<filename>')
def open_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
