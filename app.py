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

# Configuração do pytesseract
pytesseract.pytesseract.tesseract_cmd = 'tesseract'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

def aplicar_ocr_pdf(file_content):
    try:
        paginas = convert_from_bytes(file_content)
        texto_completo = ""
        
        for i, pagina in enumerate(paginas):
            # Realizar OCR na imagem
            texto = pytesseract.image_to_string(pagina)
            logging.debug(f"Texto extraído da página {i}: {texto}")
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
    <title>Upload new File</title>
    <h1>Upload new File</h1>
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
    
    if file and file.filename.lower().endswith('.pdf'):
        try:
            texto = aplicar_ocr_pdf(file.read())
            if not texto.strip():
                return jsonify({'error': 'Nenhum texto extraído do PDF'}), 500
            
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
