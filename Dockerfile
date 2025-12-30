# Usamos una imagen ligera de Python
FROM python:3.9-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalamos dependencias del sistema necesarias para Postgres y compilación
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiamos el archivo de requerimientos
COPY requirements.txt .

# Instalamos las librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el código del proyecto
COPY . .

# Exponemos el puerto de Streamlit
EXPOSE 8501

# Comando para iniciar la app
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]