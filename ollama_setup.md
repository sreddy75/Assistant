# Ollama and llama3 Setup Guide

This guide provides step-by-step instructions for setting up Ollama and the llama3 model on your system.

## 1. Install Ollama

Install Ollama using the official installation script:

```bash
curl https://ollama.ai/install.sh | sh
```

## 2. Start Ollama Service

Start the Ollama service:

```bash
ollama serve
```

## 3. Pull the llama3 Model

Download and install the llama3 model:

```bash
ollama pull llama3
```

## 4. Verify Installation

Check that llama3 is in the list of available models:

```bash
ollama list
```

## 5. Test the Model

Run a quick test to ensure the model is working:

```bash
ollama run llama3 "Hello, how are you?"
```

## 6. Docker Configuration (Optional)

If using Docker, update your docker-compose.yml to include the Ollama service:

```yaml
Copyservices:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ~/.ollama:/root/.ollama
    deploy:
      resources:
        limits:
          memory: 8G  # Adjust based on your system's capabilities
```

## 7. Set Environment Variable

Set the OLLAMA_BASE_URL environment variable:

For local development:

```bash
export OLLAMA_BASE_URL=http://localhost:11434
```

For Docker, in your .env file:

```
OLLAMA_BASE_URL=http://ollama:11434
```

## 8. Update Python Requirements

Add the Ollama client to your Python requirements:

```
ollama-python==0.1.0
```

## 9. Import Ollama Client

In your Python code, import the Ollama client:

```python
from ollama import Client as OllamaClient
```

## 10. Check System Requirements

View the system requirements for the llama3 model:

```bash
ollama show llama3
```
