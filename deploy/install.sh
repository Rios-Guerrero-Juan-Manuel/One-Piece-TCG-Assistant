#!/bin/bash
set -e

echo "=== One Piece TCG Assistant - Pi 5 Install ==="

# Python venv
echo "Setting up Python environment..."
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Initialize database
echo "Initializing database..."
python -c "from app.infrastructure.persistence.session import init_db; init_db()"

# Build frontend
echo "Building frontend..."
cd ../frontend
npm install
npm run build

# Install systemd service
echo "Installing systemd service..."
sudo cp ../deploy/systemd/optcg-assistant.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable optcg-assistant

echo "=== Installation complete ==="
echo "Start with: sudo systemctl start optcg-assistant"
echo "Access at: http://$(hostname -I | awk '{print $1}'):8000"
