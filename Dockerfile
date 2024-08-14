# Use uma imagem base com Python
FROM python:3.8-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y tesseract-ocr

# Instalar as dependências do Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copiar o código da aplicação
COPY . /app
WORKDIR /app

# Comando para iniciar a aplicação
CMD ["gunicorn", "app:app"]
