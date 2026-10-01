# 🤖 Termux Code

**Termux Code v4.3.1** is an AI-powered coding assistant built to run directly inside **Termux on Android**.

Use AI from your phone to create and edit files, analyze code, execute commands, run programs, and work with projects directly from the terminal.

## ✨ Features

- 🤖 AI-powered coding assistant
- 📁 Create and edit files
- 📖 Read and analyze project files
- 💻 Execute terminal commands
- ▶️ Run generated programs
- 🐍 Python support
- 🧠 Local memory system
- 💬 Local chat history
- 📱 Designed for Termux on Android
- 🔐 Private data stays on your device

## 📋 Requirements

Before installing Termux Code, you need:

- Android
- Termux
- Internet connection
- Python 3
- Git
- An API key for a supported AI provider

## 📦 Installation

Update Termux:

```bash
pkg update && pkg upgrade
```

Install Python and Git:

```bash
pkg install python git
```

Clone Termux Code:

```bash
git clone https://github.com/siggmaez/termux-code.git
```

Enter the directory:

```bash
cd termux-code
```

## 📚 Dependencies

Install required Python packages if they are not already installed:

```bash
pip install requests
```

If Termux Code reports that another Python module is missing, install it with:

```bash
pip install PACKAGE_NAME
```

## 🔑 API Key

Termux Code requires an API key to access AI models.

**Never share or publish your API key.**

You can store an API key using an environment variable:

```bash
export OPENROUTER_API_KEY="YOUR_API_KEY"
```

Python applications can read it using:

```python
import os

api_key = os.getenv("OPENROUTER_API_KEY")
```

Do not hard-code real API keys into files that you plan to upload to GitHub.

## ▶️ Running Termux Code

Start Termux Code with:

```bash
python termuxcode.py
```

## 🧠 Memory & Chat History

Termux Code stores local data inside:

```text
.termuxcode/
```

This may include:

```text
.termuxcode/history.json
.termuxcode/memory.json
```

These files can contain private chat history and AI memory.

The `.termuxcode/` directory is excluded from this repository through `.gitignore`.

## 🔒 Security

The repository is configured to keep local/private data out of Git.

Before contributing or pushing changes, always check:

```bash
git status
```

Never commit:

- API keys
- Passwords
- Access tokens
- `.env` files
- Chat history
- Local AI memory
- Private credentials

If an API key is accidentally published, revoke it immediately and generate a new one.

## 🔄 Updating

To update an existing installation:

```bash
cd ~/termux-code
git pull
```

## 🛠 Development

After modifying Termux Code:

```bash
git add .
git status
git commit -m "Update Termux Code"
git push
```

Always review `git status` before committing.

## 📱 Project

**Version:** 4.3.1  
**Platform:** Android / Termux  
**Language:** Python  
**Author:** siggmaez

---

**Termux Code — AI-powered coding directly from your Android terminal. 🚀**
