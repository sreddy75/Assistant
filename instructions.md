# Project Setup Instructions

## Prerequisites

Before you begin, ensure you have Docker and Docker Compose installed:

**Docker**: Install Docker by following the instructions at the Docker Installation Guide.
**Docker Compose**: Install Docker Compose by following the instructions at the Docker Compose Installation Guide. Note: Docker Desktop for Windows and Mac includes Docker Compose.

## Setup Instructions

### 1. Get access to the app zip file

1. `Assistant-main.zip` 
2. extract to your local folder

### 2, The extracted folder should look like this:
`.`
`├── Dockerfile.streamlit`
`├── docker-compose.yml`
`├── setup.sh (for Mac/Unix users)`
`├── setup.bat (for Windows users)`
`├── src`
`│   ├── app.py`
`│   └── requirements.txt`
`└── .streamlit`
 `   └── config.toml`

### 3. Create Environment Variables

Create a file named .env in the root directory with the following content:

`OPENAI_API_KEY=your_openai_api_key`
`OPENAI_MODEL_NAME=gpt-4o`
`EXA_API_KEY=your_exa_api_key`

**Replace** your_openai_api_key and your_exa_api_key with the appropriate values.

### 3. Run the Setup Script

**For Mac/Unix users:**

1.Open a terminal.
2.Navigate to the cloned repository directory.
3.Create and run a setup script named `setup.sh.`

**For Windows users:**

1.Open Command Prompt or PowerShell.
2.Navigate to the cloned repository directory.
3.Create and run a setup script named setup.bat.

These scripts will check for Docker and Docker Compose installations, create the necessary environment variables, and start the Docker containers.

## Access the Application

Once the setup script has been run:

•Open a web browser.
•Navigate to http://localhost:8501 to access the Streamlit app.