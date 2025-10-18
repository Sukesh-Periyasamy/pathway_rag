FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY data/ ./data/
COPY scripts/ ./scripts/

# Copy configuration files
COPY setup.py .
COPY README.md .
COPY LICENSE .

# Set environment variables
ENV PYTHONPATH=/app/src
ENV STREAMLIT_SERVER_PORT=8505
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Expose port
EXPOSE 8505

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8505/_stcore/health || exit 1

# Create startup script
RUN echo '#!/bin/bash\n\
echo "🏥 Starting MedCare AI CDSS..."\n\
echo "🔧 Environment:"\n\
echo "  - Python: $(python --version)"\n\
echo "  - Working Dir: $(pwd)"\n\
echo "  - OpenAI Key: ${OPENAI_API_KEY:+configured}${OPENAI_API_KEY:-not set}"\n\
echo "  - Pathway URL: ${PATHWAY_RAG_URL:-http://localhost:8008}"\n\
echo ""\n\
echo "🚀 Starting Streamlit application..."\n\
python -m streamlit run src/ui/main_app.py \\\n\
    --server.port=$STREAMLIT_SERVER_PORT \\\n\
    --server.address=$STREAMLIT_SERVER_ADDRESS \\\n\
    --server.enableCORS=false \\\n\
    --server.enableXsrfProtection=false\n\
' > /app/start.sh && chmod +x /app/start.sh

# Default command
CMD ["/app/start.sh"]