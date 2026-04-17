#!/bin/bash

# NotiFlow Test Runner
# Comprehensive test execution script

set -e  # Exit on any error

echo "🧪 NotiFlow Test Runner"
echo "=========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Check if virtual environment is active
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_warning "No virtual environment detected. Activating .venv..."
    source .venv/bin/activate
fi

# Check if dependencies are installed
print_header "Checking Dependencies"

echo "Checking Python packages..."
python -c "import fastapi, sqlalchemy, celery, redis" 2>/dev/null || {
    print_error "Missing Python dependencies. Run: pip install -r requirements.txt"
    exit 1
}

print_status "✅ Python dependencies OK"

# Check if services are running
print_header "Checking Services"

echo "Checking PostgreSQL..."
if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    print_status "✅ PostgreSQL is running"
else
    print_warning "PostgreSQL is not running. Start with: docker-compose up -d postgres"
fi

echo "Checking Redis..."
if redis-cli ping >/dev/null 2>&1; then
    print_status "✅ Redis is running"
else
    print_warning "Redis is not running. Start with: docker-compose up -d redis"
fi

# Database setup
print_header "Database Setup"

echo "Running database migrations..."
alembic upgrade head
print_status "✅ Database migrations complete"

# Run tests based on arguments
TEST_TYPE=${1:-"all"}

case $TEST_TYPE in
    "unit")
        print_header "Running Unit Tests"
        python -m pytest tests/unit/ -v --cov=app --cov-report=term-missing
        ;;
    "integration")
        print_header "Running Integration Tests"
        python -m pytest tests/integration/ -v --cov=app --cov-report=term-missing
        ;;
    "e2e")
        print_header "Running End-to-End Tests"
        python -m pytest tests/e2e/ -v --cov=app --cov-report=term-missing
        ;;
    "performance")
        print_header "Running Performance Tests"
        python -m pytest tests/performance/ -v
        ;;
    "all")
        print_header "Running All Tests"
        python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing
        ;;
    "fast")
        print_header "Running Fast Tests (unit only, no coverage)"
        python -m pytest tests/unit/ -x -v
        ;;
    *)
        print_error "Unknown test type: $TEST_TYPE"
        echo "Usage: $0 [unit|integration|e2e|performance|all|fast]"
        exit 1
        ;;
esac

# Check test results
if [ $? -eq 0 ]; then
    print_status "✅ Tests completed successfully"
    
    # Show coverage report if generated
    if [ -f "htmlcov/index.html" ]; then
        print_status "📊 Coverage report generated: htmlcov/index.html"
    fi
else
    print_error "❌ Tests failed"
    exit 1
fi

# Linting and formatting checks
if [ "$TEST_TYPE" = "all" ] || [ "$TEST_TYPE" = "fast" ]; then
    print_header "Code Quality Checks"
    
    echo "Running Black (code formatting)..."
    if black --check app/ tests/; then
        print_status "✅ Code formatting OK"
    else
        print_warning "Code formatting issues found. Run: black app/ tests/"
    fi
    
    echo "Running Ruff (linting)..."
    if ruff check app/ tests/; then
        print_status "✅ Linting OK"
    else
        print_warning "Linting issues found. Run: ruff check app/ tests/"
    fi
    
    echo "Running MyPy (type checking)..."
    if mypy app/; then
        print_status "✅ Type checking OK"
    else
        print_warning "Type checking issues found. Run: mypy app/"
    fi
fi

# Security checks
print_header "Security Checks"

echo "Checking for secrets in code..."
if git grep --cached --text --ignore-case --no-index -e 'password\|secret\|key\|token' app/ scripts/ > /dev/null 2>&1; then
    print_warning "Potential secrets found in code. Please review."
else
    print_status "✅ No obvious secrets found in code"
fi

# Performance profiling
if [ "$TEST_TYPE" = "performance" ]; then
    print_header "Performance Profiling"
    
    echo "Running with cProfile..."
    python -m cProfile -o profile.stats -m pytest tests/performance/ --benchmark-only
    
    echo "Generating flame graph..."
    if command -v flamegraph >/dev/null 2>&1; then
        flamegraph profile.stats -o profile.svg
        print_status "📈 Flame graph generated: profile.svg"
    fi
fi

# Documentation generation
if [ "$TEST_TYPE" = "all" ]; then
    print_header "Documentation"
    
    echo "Generating API documentation..."
    if command -v redoc-cli >/dev/null 2>&1; then
        redoc-cli build app/main.py --output docs/api.html
        print_status "📚 API documentation generated: docs/api.html"
    fi
fi

print_header "Test Summary"
echo "Test Type: $TEST_TYPE"
echo "Environment: ${VIRTUAL_ENV:-system}"
echo "Python: $(python --version)"
echo "Timestamp: $(date)"

if [ "$TEST_TYPE" = "all" ]; then
    echo ""
    echo "📊 Coverage Report: htmlcov/index.html"
    echo "📚 API Docs: http://localhost:8000/docs"
    echo "🌸 Flower: http://localhost:5555"
fi

print_status "🎉 Test runner completed!"
