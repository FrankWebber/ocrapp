from flask import Flask, request, send_file, jsonify
import os
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
from docx import Document
import re
import openpyxl
import tempfile

app = Flask(__name__)

# Use environment variables for configuration
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
RESULT_FOLDER = os.environ.get('RESULT_FOLDER', '/tmp/results')
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

# Configure Tesseract path if needed
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'  # Atualize o caminho conforme necessário

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
        print(f"Erro ao aplicar OCR: {e}")
        return ""

def salvar_como_docx(texto):
    doc = Document()
    doc.add_paragraph(texto)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.docx', dir=RESULT_FOLDER) as tmp:
        doc.save(tmp.name)
    return tmp.name

def extrair_dados_docx(docx_file):
    try:
        document = Document(docx_file)
        text = '\n'.join([paragraph.text for paragraph in document.paragraphs])

        # Padrões de regex para extração
        matricula_pattern = r"matrícula nº ([\d\.\-A-Za-z]+)"
        nome_pattern = r"servidor\(a\) ([A-Z\s]+) CPF:"
        cargo_pattern = r"Cargo de: ([A-Z\s]+)"
        cidade_pattern = r"cidade: ([A-Z\s]+)"
        laudo_pattern = r"LAUDO MÉDICO Nº (\d+)/(\d+)"
        periodo_pattern = r"Por (\d+) dias (\d{2}/\d{2}/\d{4}) à (\d{2}/\d{4})"
        cid_pattern = r"CID: ([A-Z0-9\-]+)"

        # Extração usando regex
        matricula = re.search(matricula_pattern, text)
        nome = re.search(nome_pattern, text)
        cargo = re.search(cargo_pattern, text)
        cidade = re.search(cidade_pattern, text)
        laudo = re.search(laudo_pattern, text)
        periodo = re.search(periodo_pattern, text)
        cid = re.search(cid_pattern, text)

        # Verificação e retorno dos dados extraídos
        return {
            'matricula': matricula.group(1) if matricula else '',
            'nome': nome.group(1) if nome else '',
            'cargo': cargo.group(1) if cargo else '',
            'cidade': cidade.group(1) if cidade else '',
            'laudo': laudo.group(1) if laudo else '',
            'ano_laudo': laudo.group(2) if laudo else '',
            'dias': periodo.group(1) if periodo else '',
            'data_inicio': periodo.group(2) if periodo else '',
            'cid': cid.group(1) if cid else ''
        }
    except Exception as e:
        print(f"Erro ao extrair dados do DOCX: {e}")
        return {}

def salvar_dados_excel(dados):
    wb = openpyxl.Workbook()
    ws = wb.active
    # Cabeçalhos da planilha
    headers = ['Matrícula', 'Nome', 'Cargo', 'Dias', 'Cidade', 'Laudo', 'Data Início', 'CID']
    ws.append(headers)

    # Preencher a planilha com os dados
    ws.append([
        dados['matricula'],
        dados['nome'],
        dados['cargo'],
        dados['dias'],
        dados['cidade'],
        dados['laudo'],
        dados['data_inicio'],
        dados['cid']
    ])

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx', dir=RESULT_FOLDER) as tmp:
        wb.save(tmp.name)
    return tmp.name

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
    
    if file and allowed_file(file.filename):
        file_extension = file.filename.rsplit('.', 1)[1].lower()

        try:
            if file_extension == 'pdf':
                # Processamento do OCR
                texto = aplicar_ocr_pdf(file.read())
                docx_path = salvar_como_docx(texto)
                return send_file(docx_path, as_attachment=True, download_name='resultado.docx')

            elif file_extension == 'docx':
                # Conversão do DOCX para Excel
                dados = extrair_dados_docx(file)
                excel_path = salvar_dados_excel(dados)
                return send_file(excel_path, as_attachment=True, download_name='resultado.xlsx')

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Tipo de arquivo não permitido'}), 400

if __name__ == '__main__':
    # Ensure the upload and result folders exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(RESULT_FOLDER, exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
