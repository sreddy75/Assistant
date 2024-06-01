@echo off
:: Check for Docker installation
where docker >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo Docker is not installed. Please install Docker from: https://docs.docker.com/get-docker/
    exit /b 1
)

:: Check for Docker Compose installation
where docker-compose >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo Docker Compose is not installed. Please install Docker Compose from: https://docs.docker.com/compose/install/
    exit /b 1
)

:: Create .env file
echo Creating .env file...
(
echo OPENAI_API_KEY=sk-****
echo OPENAI_MODEL_NAME=gpt-4o
echo EXA_API_KEY=a22a2b0b****
) > .env

:: Build and run the Docker containers
echo Building Docker images and starting containers...
docker-compose up --build -d

echo Setup complete. The Streamlit app is running on http://localhost:8501
pause