from flask import Flask, request, redirect, send_from_directory
import os
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from docx import Document
import re
import openpyxl

app = Flask(__name__)

# Configurações de diretórios
UPLOAD_FOLDER = 'D:/zeugma/uploads'
RESULT_FOLDER = 'D:/zeugma/results'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

# Configurações de caminhos
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\43803016215\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
poppler_path = r'C:\Program Files\poppler-24.07.0\Library\bin'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

# Função para verificar a extensão do arquivo
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Função para aplicar OCR em arquivos PDF
def aplicar_ocr_pdf(caminho_arquivo):
    try:
        paginas = convert_from_path(caminho_arquivo, 300, poppler_path=poppler_path)
        texto_completo = ""
        for pagina in paginas:
            texto = pytesseract.image_to_string(pagina, lang='por')
            texto_completo += texto + "\n\n"
        return texto_completo
    except Exception as e:
        print(f"Erro ao aplicar OCR: {e}")
        return ""

# Função para salvar o texto extraído como DOCX
def salvar_como_docx(texto, caminho_saida):
    try:
        doc = Document()
        doc.add_paragraph(texto)
        doc.save(caminho_saida)
    except Exception as e:
        print(f"Erro ao salvar como DOCX: {e}")

# Função para extrair os dados do documento Word
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

# Função para salvar os dados no Excel
def salvar_dados_excel(dados, excel_file):
    try:
        if not os.path.exists(excel_file):
            wb = openpyxl.Workbook()
            ws = wb.active
            # Cabeçalhos da planilha
            ws['A1'] = 'Matrícula'
            ws['B1'] = 'Nome'
            ws['C1'] = 'Cargo'
            ws['D1'] = 'Dias'
            ws['E1'] = 'Cidade'
            ws['F1'] = 'Laudo'
            ws['G1'] = 'Data Início'
            ws['N1'] = 'CID'
        else:
            wb = openpyxl.load_workbook(excel_file)
            ws = wb.active

        # Encontrar a próxima linha disponível
        row = ws.max_row + 1

        # Preencher a planilha com os dados
        ws[f'A{row}'] = dados['matricula']
        ws[f'B{row}'] = dados['nome']
        ws[f'C{row}'] = dados['cargo']
        ws[f'D{row}'] = dados['dias']
        ws[f'E{row}'] = dados['cidade']
        ws[f'F{row}'] = dados['laudo']
        ws[f'G{row}'] = dados['data_inicio']
        ws[f'N{row}'] = dados['cid']

        wb.save(excel_file)
    except Exception as e:
        print(f"Erro ao salvar dados no Excel: {e}")

# Função principal de conversão de DOCX para Excel
def extrair_dados_docx_para_excel(docx_file, excel_file):
    dados = extrair_dados_docx(docx_file)
    salvar_dados_excel(dados, excel_file)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        file_extension = file.filename.rsplit('.', 1)[1].lower()

        if file_extension == 'pdf':
            filename = 'uploaded.pdf'
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Processamento do OCR
            texto = aplicar_ocr_pdf(file_path)
            docx_path = os.path.join(app.config['RESULT_FOLDER'], 'resultado.docx')  # Salvar no RESULT_FOLDER
            salvar_como_docx(texto, docx_path)

            return send_from_directory(app.config['RESULT_FOLDER'], 'resultado.docx', as_attachment=True)

        elif file_extension == 'docx':
            filename = 'uploaded.docx'
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Conversão do DOCX para Excel
            excel_path = os.path.join(app.config['RESULT_FOLDER'], 'resultado.xlsx')
            extrair_dados_docx_para_excel(file_path, excel_path)

            return send_from_directory(app.config['RESULT_FOLDER'], 'resultado.xlsx', as_attachment=True)

    return redirect(request.url)

if __name__ == '__main__':
    # Criação das pastas necessárias se não existirem
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(RESULT_FOLDER):
        os.makedirs(RESULT_FOLDER)
    app.run(debug=True)
