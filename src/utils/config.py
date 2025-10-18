"""
Configuration management for MedCare AI CDSS
Handles environment variables, API keys, and system settings
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import json

class Config:
    """Central configuration management for the application"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent.parent
        self.data_dir = self.base_dir / "data"
        self.logs_dir = self.base_dir / "logs"
        
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from environment"""
        return os.getenv("OPENAI_API_KEY")
    
    @property
    def vector_db_path(self) -> Path:
        """Path to the vector database file"""
        return self.data_dir / "drugbank_vectordb.pkl"
    
    @property
    def streamlit_config(self) -> Dict[str, Any]:
        """Streamlit configuration settings"""
        return {
            "server.port": 8505,
            "server.address": "localhost",
            "server.maxUploadSize": 200,  # MB
            "theme.base": "light",
            "theme.primaryColor": "#1f77b4",
        }
    
    @property
    def ai_model_config(self) -> Dict[str, Any]:
        """AI model configuration"""
        return {
            "model_name": "gpt-4o-mini",
            "max_tokens": 2000,
            "temperature": 0.1,  # Low temperature for medical accuracy
            "timeout": 30,  # seconds
        }
    
    @property
    def vector_search_config(self) -> Dict[str, Any]:
        """Vector search configuration"""
        return {
            "embedding_model": "all-MiniLM-L6-v2",
            "search_top_k": 10,
            "similarity_threshold": 0.7,
            "max_results": 50,
        }
    
    @property
    def pdf_config(self) -> Dict[str, Any]:
        """PDF generation configuration"""
        return {
            "page_size": "letter",
            "margins": {
                "top": 72,
                "bottom": 72, 
                "left": 72,
                "right": 72
            },
            "fonts": {
                "title": "Helvetica-Bold",
                "header": "Helvetica-Bold", 
                "body": "Helvetica",
                "size_title": 16,
                "size_header": 12,
                "size_body": 10
            }
        }
    
    def validate_setup(self) -> Dict[str, bool]:
        """Validate that all required components are available"""
        checks = {
            "openai_api_key": bool(self.openai_api_key),
            "vector_database": self.vector_db_path.exists(),
            "data_directory": self.data_dir.exists(),
            "logs_directory": self.logs_dir.exists(),
        }
        return checks
    
    def get_env_info(self) -> Dict[str, str]:
        """Get environment information for debugging"""
        return {
            "base_directory": str(self.base_dir),
            "data_directory": str(self.data_dir),
            "logs_directory": str(self.logs_dir),
            "vector_db_exists": str(self.vector_db_path.exists()),
            "openai_key_configured": "Yes" if self.openai_api_key else "No",
        }

# Global configuration instance
config = Config()

def validate_environment() -> bool:
    """Quick environment validation"""
    checks = config.validate_setup()
    missing = [key for key, value in checks.items() if not value]
    
    if missing:
        print(f"❌ Missing requirements: {', '.join(missing)}")
        return False
    
    print("✅ All requirements satisfied")
    return True

if __name__ == "__main__":
    print("🔧 MedCare AI CDSS Configuration")
    print("=" * 40)
    
    # Show environment info
    env_info = config.get_env_info()
    for key, value in env_info.items():
        print(f"{key}: {value}")
    
    print("\n🔍 Validation Results:")
    print("=" * 20)
    validate_environment()