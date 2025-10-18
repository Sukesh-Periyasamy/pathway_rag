@echo off
echo 🏥 MedCare AI CDSS - Hackathon Demo Startup
echo =========================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if OpenAI API key is set
if "%OPENAI_API_KEY%"=="" (
    echo ❌ OPENAI_API_KEY environment variable not set
    echo Please set your OpenAI API key:
    echo set OPENAI_API_KEY=your_api_key_here
    pause
    exit /b 1
)

echo ✅ Python found
echo ✅ OpenAI API key configured

REM Navigate to project directory
cd /d "%~dp0.."
echo 📁 Working directory: %CD%

REM Install dependencies if needed
echo � Installing dependencies...
pip install -r requirements.txt

REM Check if vector database exists
if not exist "data\drugbank_vectordb.pkl" (
    echo ❌ Vector database not found at data\drugbank_vectordb.pkl
    echo Please ensure the DrugBank vector database is available
    pause
    exit /b 1
)

echo ✅ Vector database found
echo 🚀 Starting MedCare AI CDSS Demo...
echo 🌐 Demo will be available at: http://localhost:8505

REM Start Streamlit application
python -m streamlit run src\ui\main_app.py --server.port 8505

pause