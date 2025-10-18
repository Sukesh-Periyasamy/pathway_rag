#!/usr/bin/env python3
"""
Medical RAG System Status and Test Script
Comprehensive system check and fresh startup
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def check_system_status():
    """Check the status of all system components"""
    
    print("🏥 Medical RAG System - Status Check")
    print("=" * 50)
    
    # Check Python installation
    print("\n🐍 Python Environment:")
    try:
        python_version = sys.version
        print(f"✅ Python: {python_version.split()[0]}")
    except Exception as e:
        print(f"❌ Python check failed: {e}")
        return False
    
    # Check required packages
    print("\n📦 Required Packages:")
    required_packages = [
        "streamlit", "pandas", "numpy", "openai", 
        "reportlab", "sentence-transformers", "faiss-cpu"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ Missing packages: {', '.join(missing_packages)}")
        install = input("Install missing packages? (y/n): ")
        if install.lower() == 'y':
            for package in missing_packages:
                print(f"Installing {package}...")
                subprocess.run([sys.executable, "-m", "pip", "install", package])
    
    # Check API configuration
    print("\n🔑 API Configuration:")
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print(f"✅ OpenAI API Key: ...{openai_key[-8:]}")
    else:
        print("❌ OpenAI API Key not set")
        print("Set with: set OPENAI_API_KEY=your_api_key_here")
    
    # Check required files
    print("\n📁 System Files:")
    required_files = [
        "new_app.py",
        "clinical_decision_orchestrator.py", 
        "drugbank_vectordb_query.py",
        "drugbank_vectordb_complete.pkl"
    ]
    
    missing_files = []
    for file in required_files:
        if Path(file).exists():
            size = Path(file).stat().st_size / (1024*1024)
            print(f"✅ {file} ({size:.1f} MB)")
        else:
            print(f"❌ {file} (missing)")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️ Missing files: {', '.join(missing_files)}")
        if "drugbank_vectordb_complete.pkl" in missing_files:
            print("Run: python streaming_drugbank_vectordb.py to create database")
    
    # Check ports
    print("\n🌐 Port Status:")
    ports_to_check = [8502, 8503, 8504, 8505]
    available_port = None
    
    for port in ports_to_check:
        try:
            response = requests.get(f"http://localhost:{port}", timeout=2)
            print(f"⚠️ Port {port}: In use")
        except:
            print(f"✅ Port {port}: Available")
            if available_port is None:
                available_port = port
    
    return available_port

def stop_existing_processes():
    """Stop any existing Python/Streamlit processes"""
    
    print("\n🛑 Stopping existing processes...")
    
    try:
        # Windows
        subprocess.run(["taskkill", "/F", "/IM", "python.exe"], 
                      capture_output=True, check=False)
        subprocess.run(["taskkill", "/F", "/IM", "streamlit.exe"], 
                      capture_output=True, check=False)
        print("✅ Processes stopped")
    except:
        # Linux/Mac
        try:
            subprocess.run(["pkill", "-f", "streamlit"], 
                          capture_output=True, check=False)
            print("✅ Processes stopped")
        except:
            print("⚠️ Could not stop processes automatically")
    
    time.sleep(2)

def start_system(port):
    """Start the Medical RAG system"""
    
    print(f"\n🚀 Starting Medical RAG System on port {port}...")
    print("\nSystem Features:")
    print("  ✅ DrugBank Vector Database (17,430 drugs)")
    print("  ✅ Clinical Decision Support")
    print("  ✅ AI-Generated Doctor Summaries (PDF)")
    print("  ✅ Patient Education Materials (PDF)")
    print("  ✅ Drug Interaction Analysis")
    print("  ✅ Real-time Vector Search")
    
    try:
        # Start Streamlit
        cmd = [
            sys.executable, "-m", "streamlit", "run", "new_app.py",
            "--server.port", str(port),
            "--server.enableCORS", "false", 
            "--server.enableXsrfProtection", "false"
        ]
        
        print(f"\n🌐 Access your system at: http://localhost:{port}")
        print("\n📋 Usage Instructions:")
        print("1. Enter patient demographics and medical history")
        print("2. Add current medications and known allergies") 
        print("3. Click 'Analyze Patient Data' for AI analysis")
        print("4. Review results in 'Doctor Summary' and 'Patient Education' tabs")
        print("5. Download PDF reports using the download buttons")
        print("\nPress Ctrl+C to stop the system")
        print("=" * 50)
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n🛑 System stopped by user")
    except Exception as e:
        print(f"❌ Failed to start system: {e}")

def main():
    """Main function"""
    
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    # Check system status
    available_port = check_system_status()
    
    if not available_port:
        print("\n❌ No available ports found")
        return
    
    print(f"\n📊 System Status: Ready")
    print(f"🔧 Will use port: {available_port}")
    
    # Ask user if they want to continue
    start = input("\nStart Medical RAG System? (y/n): ")
    if start.lower() != 'y':
        print("👋 Goodbye!")
        return
    
    # Stop existing processes
    stop_existing_processes()
    
    # Start system
    start_system(available_port)

if __name__ == "__main__":
    main()