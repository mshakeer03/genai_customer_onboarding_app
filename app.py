import os
from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash
import subprocess
from werkzeug.utils import secure_filename
import re
import pdfplumber
from flask_session import Session

# Initialize Flask and session
app = Flask(__name__)
sess = Session()

# Folder to store uploaded files
UPLOAD_FOLDER = 'Data/Other/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed extensions for file uploads
ALLOWED_EXTENSIONS = {'pdf'}

# Flask app configurations
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'
sess.init_app(app)

# Regular expressions for validating fields
regex_patterns = {
    'GBG ID': r'GB[0-9A-Z]+',
    'BGC ID': r'BGC[0-9A-Z]+',
    'BAC ID': r'BAC[0-9A-Z]+',
    'BAM ID': r'BAM[0-9A-Z]+',
    'GSMA': r'CA[0-9]+',
}

# Favicon route
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# Helper function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Extract text from PDF and perform validation
def validate_pdf(file_path):
    validation_results = {}

    # Open the uploaded PDF using pdfplumber
    with pdfplumber.open(file_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()

    # Perform basic validation on required fields and patterns
    required_fields = [
        'RITM Number raised', 'Account Name', 'Account Display Name on iAIOPS',
        'type in the Country name', 'Select the country / Market from the dropdown',
        'GBG ID', 'BGC ID', 'BAC ID', 'BAM ID', 'GSMA', 'CDIR', 'Chip ID'
    ]

    # Check for missing fields and validate against patterns
    for field in required_fields:
        field_regex = r'{}: (.+)'.format(field)
        match = re.search(field_regex, text)
        if match:
            value = match.group(1).strip()
            if field in regex_patterns:
                if not re.match(regex_patterns[field], value):
                    return "There are missing fields in the selected PDF. Kindly upload a valid PDF"
        else:
            return "There are missing fields in the selected PDF. Kindly upload a valid PDF"

    return "The file has been successfully uploaded and validated. How would you like to proceed from here?"

# File upload route
@app.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files.get('file')

        # Check if the file is valid and has a PDF extension
        if file and allowed_file(file.filename):
            # Save the uploaded file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
            file.save(file_path)

            # Perform validation on the uploaded PDF
            validation_result = validate_pdf(file_path)

            # Render the template with validation result
            return render_template('index.html', validation_result=validation_result)

        else:
            # flash('Not a PDF, Please upload a .pdf file')
            # return redirect(url_for('index'))
            validation_result = "Selected file is not an PDF, kindly upload an valid .pdf file"
            return render_template('index.html', validation_result=validation_result)

# Homepage route
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        query = request.form['query']
        services = "S"
        forms = "F"
        other = "O"

        # Run the query
        result = run_query(query, services, forms, other)

        # Render the template with the query results
        return render_template('index.html', result=result, query=query, services=services, forms=forms, other=other)
    return render_template('index.html', result="")

# Helper function to run a query script
def run_query(query, services, forms, other):
    try:
        result = subprocess.check_output(
            ['python3', 'query_data.py', query, '--services', services, '--forms', forms, '--other', other],
            stderr=subprocess.STDOUT, universal_newlines=True
        )
        return result
    except subprocess.CalledProcessError as e:
        return f"An error occurred: {e.output}"

# Run the Flask application
if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'
    sess.init_app(app)
    app.run(debug=True)
