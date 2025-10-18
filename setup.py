"""
setup.py - Package configuration for MedCare AI CDSS
Hackathon project for AI-powered clinical decision support
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
if requirements_path.exists():
    requirements = requirements_path.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]
else:
    requirements = [
        "streamlit>=1.28.0",
        "openai>=1.0.0",
        "faiss-cpu>=1.7.4",
        "sentence-transformers>=2.2.0",
        "reportlab>=4.0.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "scikit-learn>=1.3.0",
        "python-dotenv>=1.0.0",
        "ijson>=3.2.0",
    ]

setup(
    name="medcare-ai-cdss",
    version="1.0.0",
    description="AI-Powered Clinical Decision Support System with Vector Database Integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Healthcare AI Innovators",
    author_email="team@medcare-ai.com",
    url="https://github.com/your-team/medcare-ai-cdss",
    
    # Package configuration
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=requirements,
    
    # Additional files to include
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.txt", "*.md"],
    },
    include_package_data=True,
    
    # Entry points for command-line scripts
    entry_points={
        "console_scripts": [
            "medcare-demo=ui.main_app:main",
            "medcare-setup=scripts.setup_database:main",
            "medcare-test=scripts.run_tests:main",
        ],
    },
    
    # Classifiers for PyPI
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    
    # Keywords for searchability
    keywords=[
        "healthcare", "ai", "clinical-decision-support", "rag", 
        "vector-database", "medical-ai", "drug-interactions", 
        "patient-education", "clinical-intelligence"
    ],
    
    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/your-team/medcare-ai-cdss/issues",
        "Source": "https://github.com/your-team/medcare-ai-cdss",
        "Documentation": "https://github.com/your-team/medcare-ai-cdss/docs",
        "Demo": "http://localhost:8505",
    },
    
    # Development dependencies
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "docs": [
            "mkdocs>=1.4.0",
            "mkdocs-material>=8.0.0",
            "mkdocs-mermaid2-plugin>=0.6.0",
        ],
        "deployment": [
            "docker>=6.0.0",
            "gunicorn>=20.0.0",
            "uvicorn>=0.20.0",
        ],
    },
)