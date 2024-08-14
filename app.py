from flask import Flask, request, send_file, jsonify
import os
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
from docx import Document
import tempfile
import logging

# Configuração de logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

# Use environment variables for configuration
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
RESULT_FOLDER = os.environ.get('RESULT_FOLDER', '/tmp/results')
ALLOWED_EXTENSIONS = {'pdf'}

# Configuração do pytesseract
pytesseract.pytesseract.tesseract_cmd = 'tesseract'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def aplicar_ocr_pdf(file_content):
    try:
        paginas = convert_from_bytes(file_content)
        texto_completo = ""
        for pagina in paginas:
            texto = pytesseract.image_to_string(pagina, lang='por')
            texto_completo += texto + "\n\n"
        return texto_completo
    except Exception as e:
        logging.error(f"Erro ao aplicar OCR: {e}")
        return ""

def salvar_como_docx(texto):
    try:
        doc = Document()
        doc.add_paragraph(texto)
        os.makedirs(RESULT_FOLDER, exist_ok=True)  # Cria o diretório se não existir
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx', dir=RESULT_FOLDER) as tmp:
            doc.save(tmp.name)
            logging.debug(f"Arquivo DOCX salvo em: {tmp.name}")
        return tmp.name
    except Exception as e:
        logging.error(f"Erro ao salvar DOCX: {e}")
        return ""

@app.route('/')
def index():
    return '''
    <!doctype html>
    <title>Upload de Arquivo PDF</title>
    <h1>Upload de Arquivo PDF</h1>
    <form method=post enctype=multipart/form-data action="/upload">
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
    
    if file and allowed_file(file.filename):
        try:
            texto = aplicar_ocr_pdf(file.read())
            docx_path = salvar_como_docx(texto)
            if docx_path:
                return send_file(docx_path, as_attachment=True, download_name='resultado.docx')
            return jsonify({'error': 'Erro ao salvar o arquivo DOCX'}), 500

        except Exception as e:
            logging.error(f"Erro ao processar arquivo: {e}")
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Tipo de arquivo não permitido'}), 400

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(RESULT_FOLDER, exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
