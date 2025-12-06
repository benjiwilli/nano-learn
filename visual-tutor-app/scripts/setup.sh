#!/bin/bash

# Visual Tutor App - Setup Script
# This script sets up the development environment

set -e

echo "========================================="
echo "Visual Tutor App - Development Setup"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: Please run this script from the visual-tutor-app directory${NC}"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

if ! command_exists python3; then
    echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
    exit 1
fi

if ! command_exists node; then
    echo -e "${RED}Error: Node.js is required but not installed.${NC}"
    exit 1
fi

if ! command_exists npm; then
    echo -e "${RED}Error: npm is required but not installed.${NC}"
    exit 1
fi

echo -e "${GREEN}All prerequisites found!${NC}"

# Setup Backend
echo -e "\n${YELLOW}Setting up Backend...${NC}"

cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r ../requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    cp ../.env.example .env
    echo -e "${YELLOW}Please edit backend/.env with your API keys!${NC}"
fi

cd ..

echo -e "${GREEN}Backend setup complete!${NC}"

# Setup Frontend
echo -e "\n${YELLOW}Setting up Frontend...${NC}"

cd frontend

# Install dependencies
echo "Installing npm dependencies..."
npm install

cd ..

echo -e "${GREEN}Frontend setup complete!${NC}"

# Final instructions
echo -e "\n========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit backend/.env with your API keys:"
echo "   - GEMINI_API_KEY"
echo "   - GENSPARK_API_KEY"
echo ""
echo "2. Start the backend server:"
echo "   cd backend && source venv/bin/activate && python main.py"
echo ""
echo "3. In a new terminal, start the frontend:"
echo "   cd frontend && npm run dev"
echo ""
echo "4. Open http://localhost:5173 in your browser"
echo ""
echo -e "${YELLOW}Happy coding!${NC}"
