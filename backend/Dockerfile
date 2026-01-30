# Development Dockerfile for Flask API with Full ML Stack
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model for NER (using pip for reliable installation)
RUN pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

# Download NLTK data for tokenization
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

# Download TextBlob corpora
RUN python -m textblob.download_corpora

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "run.py"]
