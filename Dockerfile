# Single stage build with build tools
FROM python:3.11-slim

# Install system dependencies including build tools for Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    gcc \
    g++ \
    pkg-config \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Configure pip to use Chinese mirror for faster downloads
COPY pip.conf /etc/pip.conf
RUN pip install --no-cache-dir --upgrade pip

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Install core dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Poetry and configure mirrors
RUN pip install --no-cache-dir poetry==1.8.3

# Copy the entire application
COPY . .

# Install Poetry dependencies for gnosis tool (this handles the complex dependencies)
WORKDIR /app/gnosis_predict_market_tool
RUN poetry config virtualenvs.create false && \
    poetry source add --priority=primary tsinghua https://pypi.tuna.tsinghua.edu.cn/simple/ && \
    poetry lock --no-update && \
    poetry install --only=main --no-interaction --no-ansi

# Back to main app directory
WORKDIR /app

# Create logs directory
RUN mkdir -p logs && chown -R appuser:appuser logs

# Set proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONPATH="/app:/app/gnosis_predict_market_tool"
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]