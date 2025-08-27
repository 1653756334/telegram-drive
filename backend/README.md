# Telegram Drive Backend (Mixed Bot + Client API)

## Quick Start

1. Create and fill `.env` based on `.env.example`.
2. Create a Python venv and install dependencies:
   - pip install -r backend/requirements.txt
3. migrate database:
   - alembic upgrade head
4. for videos, you shoule make sure ffmepeg is installed
```bash
# Windows
choco install ffmpeg

# Linux
sudo apt install ffmpeg  # Ubuntu/Debian
sudo yum install ffmpeg  # CentOS/RHEL

# macOS
brew install ffmpeg
```
5. Run the API server:
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```


