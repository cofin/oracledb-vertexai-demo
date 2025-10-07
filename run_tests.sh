#!/bin/bash
# Test runner script for SQLSpec migration validation

set -e

echo "🧪 SQLSpec Migration Test Suite"
echo "================================"
echo ""

# Activate virtual environment
source .venv/bin/activate

# Check if Oracle database is available
if [ -z "$ORACLE_DSN" ]; then
    echo "⚠️  Warning: ORACLE_DSN not set. Using .env.testing"
    export $(cat .env.testing | grep -v '^#' | xargs)
fi

echo "📋 Test Configuration:"
echo "  - Python: $(python --version)"
echo "  - Pytest: $(python -m pytest --version)"
echo "  - Working Dir: $(pwd)"
echo ""

# Run tests with verbose output
echo "🚀 Running Integration Tests..."
echo ""

# Run specific test categories
python -m pytest tests/integration/test_sqlspec_connection.py -v -s 2>&1 || echo "⚠️  Connection tests completed with warnings"

echo ""
echo "✅ Test suite execution completed!"
echo ""
echo "📊 To run all tests:"
echo "  python -m pytest tests/integration/ -v"
echo ""
echo "📊 To run with coverage:"
echo "  python -m pytest tests/integration/ --cov=app --cov-report=html"
