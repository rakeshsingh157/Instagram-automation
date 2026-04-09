#!/bin/bash

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing requirements..."
pip install -r requirements.txt

echo "Starting Instagram Bot Server..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
