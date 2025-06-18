# File to JSON Converter

A web application that converts various file formats (Excel, PDF, and EVTX) to JSON format.

## Features

- Convert Excel files (.xlsx, .xls) to JSON
- Convert PDF files to JSON (extracts tables and text)
- Convert Windows Event Log files (EVTX) to JSON
- Modern web interface with drag-and-drop support
- Batch file processing
- Downloads converted files as a ZIP archive

## Requirements

- Python 3.7+
- Flask
- pandas
- openpyxl
- tabula-py
- PyPDF2
- python-evtx

## Installation

1. Clone the repository:
```bash
git clone https://github.com/gohilrajbha0312/EVTX_TO_CONVERT_JSON_FILE.git
cd EVTX_TO_CONVERT_JSON_FILE
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask application:
```bash
python app.py
```

2. Open your web browser and navigate to `http://127.0.0.1:5000`

3. Upload your files using the web interface:
   - Drag and drop files or click to browse
   - Supported formats: .xlsx, .xls, .pdf, .evtx
   - Multiple files can be uploaded at once

4. Click "Convert to JSON" to process the files

5. The converted files will be downloaded as a ZIP archive

## Project Structure

```
EVTX_TO_CONVERT_JSON_FILE/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── templates/         # HTML templates
│   └── index.html     # Main web interface
└── uploads/          # Temporary file storage
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Rajbha Gohil 