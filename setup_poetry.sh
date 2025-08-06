#!/bin/bash
# Post-deployment setup script for Poetry dependencies

echo "🚂 Railway post-deployment setup..."

# Check if Poetry is available
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found, installing..."
    pip install poetry
fi

# Install gnosis_predict_market_tool dependencies
if [ -d "gnosis_predict_market_tool" ]; then
    echo "Installing gnosis_predict_market_tool dependencies..."
    cd gnosis_predict_market_tool
    poetry install --no-dev --no-root
    cd ..
    echo "✅ Poetry dependencies installed"
else
    echo "⚠️ gnosis_predict_market_tool directory not found"
fi

echo "🎉 Setup complete!"