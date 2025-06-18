from flask import Flask, request, jsonify, send_file, render_template
import pandas as pd
import json
import os
from werkzeug.utils import secure_filename
import zipfile
from tabula import read_pdf
from PyPDF2 import PdfReader
from Evtx.Evtx import FileHeader
import xml.etree.ElementTree as ET
from datetime import datetime
import shutil

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'pdf', 'evtx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_excel_to_json(filepath):
    """Convert Excel file to JSON format"""
    df = pd.read_excel(filepath)
    return df.to_json(orient='records', indent=2)

def convert_pdf_to_json(filepath):
    """Convert PDF file to JSON format"""
    # First try using tabula-py
    try:
        df = read_pdf(filepath, pages='all')
        if isinstance(df, list):
            # If multiple tables, combine them
            df = pd.concat(df, ignore_index=True)
        return df.to_json(orient='records', indent=2)
    except Exception as e:
        print(f"Tabula-py conversion failed: {str(e)}")
        # Fallback to PyPDF2 for text extraction
        try:
            reader = PdfReader(filepath)
            text_content = []
            for page in reader.pages:
                text_content.append(page.extract_text())
            return json.dumps({"text_content": text_content}, indent=2)
        except Exception as e:
            print(f"PyPDF2 conversion failed: {str(e)}")
            return json.dumps({"error": "Failed to convert PDF"})

def convert_evtx_to_json(filepath):
    """Convert EVTX file to JSON format"""
    events = []
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        from io import BytesIO
        evtx_file = BytesIO(content)
        
        try:
            header = FileHeader(evtx_file.getvalue(), 0x0)
            
            for chunk in header.chunks():
                for record in chunk.records():
                    try:
                        xml_string = record.xml()
                        root = ET.fromstring(xml_string)
                        event_data = {}
                        
                        # Get System section
                        system = root.find('.//{http://schemas.microsoft.com/win/2004/08/events/event}System')
                        if system is not None:
                            for child in system:
                                tag = child.tag.split('}')[-1]
                                if child.text:
                                    event_data[tag] = child.text
                                for attr_name, attr_value in child.attrib.items():
                                    event_data[f"{tag}_{attr_name}"] = attr_value
                        
                        # Get EventData section
                        event_data_section = root.find('.//{http://schemas.microsoft.com/win/2004/08/events/event}EventData')
                        if event_data_section is not None:
                            data_items = {}
                            for data in event_data_section.findall('.//{http://schemas.microsoft.com/win/2004/08/events/event}Data'):
                                name = data.get('Name')
                                if name and data.text:
                                    data_items[name] = data.text
                                for attr_name, attr_value in data.attrib.items():
                                    if name:
                                        data_items[f"{name}_{attr_name}"] = attr_value
                            if data_items:
                                event_data['EventData'] = data_items
                        
                        # Get UserData section
                        user_data = root.find('.//{http://schemas.microsoft.com/win/2004/08/events/event}UserData')
                        if user_data is not None:
                            user_data_items = {}
                            for child in user_data:
                                tag = child.tag.split('}')[-1]
                                if child.text:
                                    user_data_items[tag] = child.text
                                for attr_name, attr_value in child.attrib.items():
                                    user_data_items[f"{tag}_{attr_name}"] = attr_value
                            if user_data_items:
                                event_data['UserData'] = user_data_items
                        
                        # Add timestamp
                        if 'TimeCreated_SystemTime' in event_data:
                            try:
                                timestamp = datetime.strptime(
                                    event_data['TimeCreated_SystemTime'],
                                    '%Y-%m-%dT%H:%M:%S.%fZ'
                                )
                                event_data['TimeCreated'] = timestamp.isoformat()
                            except ValueError:
                                pass
                        
                        event_data['RecordNumber'] = record.record_num()
                        events.append(event_data)
                    except Exception as e:
                        print(f"Error parsing record: {str(e)}")
                        continue
        finally:
            evtx_file.close()
            
    except Exception as e:
        print(f"Error reading EVTX file: {str(e)}")
        return json.dumps({"error": str(e)})
    
    return json.dumps(events, indent=2)

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    """Handle file conversion"""
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files[]')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No files selected'}), 400
    
    # Create a unique temporary directory for this conversion
    import uuid
    temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{uuid.uuid4().hex}')
    os.makedirs(temp_dir, exist_ok=True)
    
    converted_files = []
    try:
        for file in files:
            if file and allowed_file(file.filename):
                # Save the file temporarily
                temp_path = os.path.join(temp_dir, secure_filename(file.filename))
                file.save(temp_path)
                
                try:
                    filename = secure_filename(file.filename)
                    extension = filename.rsplit('.', 1)[1].lower()
                    
                    if extension in ['xlsx', 'xls']:
                        json_data = convert_excel_to_json(temp_path)
                    elif extension == 'pdf':
                        json_data = convert_pdf_to_json(temp_path)
                    elif extension == 'evtx':
                        json_data = convert_evtx_to_json(temp_path)
                    else:
                        continue
                    
                    # Save the converted JSON
                    json_filename = f"{os.path.splitext(filename)[0]}.json"
                    json_path = os.path.join(temp_dir, json_filename)
                    with open(json_path, 'w', encoding='utf-8') as f:
                        f.write(json_data)
                    
                    converted_files.append(json_path)
                finally:
                    # Clean up the original file
                    try:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                    except Exception as e:
                        print(f"Error removing temporary file {temp_path}: {str(e)}")
        
        if not converted_files:
            return jsonify({'error': 'No files were successfully converted'}), 400
        
        # Create a zip file containing all converted files
        zip_path = os.path.join(temp_dir, 'converted_files.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in converted_files:
                zipf.write(file_path, os.path.basename(file_path))
        
        # Send the zip file
        response = send_file(
            zip_path,
            as_attachment=True,
            download_name='converted_files.zip',
            mimetype='application/zip'
        )
        
        # Clean up after sending the response
        @response.call_on_close
        def cleanup():
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Error cleaning up temporary directory {temp_dir}: {str(e)}")
        
        return response
    
    except Exception as e:
        # Clean up on error
        try:
            shutil.rmtree(temp_dir)
        except Exception as cleanup_error:
            print(f"Error cleaning up temporary directory {temp_dir}: {str(cleanup_error)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 