# Installation & Setup Guide

This guide covers installing dependencies, setting up virtual environments, configuring credentials, and preparing the systems.

---

## System Prerequisites

1. **Python 3.10+** (Ensure Python is added to your environment `PATH`).
2. **Node.js 18+** (Required if running the optional WhatsApp Bridge).
3. **Google Chrome** (Required if running the WhatsApp Bridge, since Puppeteer launches Chrome to scan WhatsApp QR codes).
4. **CUDA-Capable GPU** (Optional, for faster local Whisper audio transcription).

---

## Project Installation

### 1. Python Environment Setup
We recommend setting up a virtual environment in the project directory:

```bash
# Clone the repository
git clone https://github.com/<your-username>/profiler_guru.git
cd profiler_guru

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

# Install package dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Node.js Environment Setup (WhatsApp Bridge)
If you intend to run the live WhatsApp Bridge, navigate to the bridge directory and install its packages:

```bash
cd Whatsapp-Bridge
npm install
cd ..
```

---

## Credentials & Environment Variables

Copy the template environment file to create your local configurations:

```bash
cp .env.example .env
```

Open `.env` and fill in the required fields. Here is the configuration checklist:

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `APP_PASSWORD` | **Yes** | — | **Bcrypt hash** of your app portal password. Plaintext is rejected. |
| `SECRET_KEY` | **Yes** | — | Random 32-byte hex string used for JWT signing. |
| `GOOGLE_API_KEY` | **Yes** | — | Google AI Studio Key used for Gemini 1.5 Flash Cloud. |
| `INSTAGRAM_USERNAME`| No | — | Username used to distinguish your own messages ("Me") in imports. |
| `CHATS_DIR` | No | `chats` | Relative path where imported logs and audio files are stored. |
| `USE_GPU` | No | `false` | Set to `true` to use GPU CUDA for local faster-whisper. |
| `OLLAMA_MODEL` | No | `gemma-3-4b`| Default model name to use when Ollama is selected. |

---

## App Password Hash Generation

Profile Guru enforces a secure **Bcrypt-hashed app password** at startup. Plaintext values are rejected to protect your credentials.

You can use the helper script `hash_password.py` included in the root directory to generate a valid hash:

```bash
python hash_password.py
```

Input your desired password when prompted. Copy the output hash and paste it as the `APP_PASSWORD` value in your `.env` file:

```env
APP_PASSWORD=$2b$12$L7R2Fv8iUqWcKjYx...
```

To generate a secure `SECRET_KEY`, you can run:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
