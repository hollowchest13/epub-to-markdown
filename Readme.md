# Book Converter for LLM

A CLI/GUI and Web API tool for converting PDF and EPUB files into structured Markdown, optimized for RAG (Retrieval-Augmented Generation) pipelines.

## Features

* Converts PDF and EPUB files to Markdown
* Splits output into chapters and sections as separate files
* GUI mode for interactive use, CLI mode for automation
* FastAPI backend for web service integration
* Powered by the Google Gemini API
* Automatic fallback to CLI if GUI is unavailable

## Requirements

* Python 3.12+
* [uv](https://github.com/astral-sh/uv) (Fast Python package manager)
* Google Gemini API Key

## Installation

Clone the repository and set up the environment using `uv`:

```bash
git clone https://github.com/hollowchest13/epub-to-markdown.git
cd epub-to-markdown

uv venv --python 3.12
```

Windows (cmd / PowerShell)
```bash
.venv\Scripts\activate
uv pip install .
```
Linux / macOS
```bash
source .venv/bin/activate
uv pip install .
```
Usage
CLI and GUI Modes
Run the application in the default mode (GUI or CLI based on settings):
```bash
convert
```
Additional CLI options:
```bash
convert --dir /path/to/files
convert --set-key
```
FastAPI Web Server
Start the backend server using uvicorn:
```bash
uvicorn server.run_api:app --reload
```
API Endpoints

POST /convert: Accepts uploaded files (files) and a Gemini API key via the X-API-Key request header. Returns a ZIP archive (converted.zip) containing the structured Markdown files.

GET /health: Health check endpoint returning the server status.
Testing:
To test FastApi layout you may use curl:

```bash
curl -X POST "http://localhost:8000/convert" -H "X-API-Key: your_gemini_api_key" -F "files=@/path/to/book.epub" --output converted.zip
```
But more comfortable use **Bruno** or **Postman**!

Configuration
Edit settings.json to configure the default launch mode:

```JSON
{
  "mode": "gui"
}
```
Available modes: `gui` (default), `cli`, and `api`. 
* `gui`: Launches the graphical interface (automatically falls back to CLI mode if a graphical environment is unavailable).
* `cli`: Runs the command-line interface.
* `api`: Automatically starts the FastAPI web server.

## Screenshots

**`GUI` mode:**

![GUI Interface](https://raw.githubusercontent.com/hollowchest13/epub-to-markdown/main/screenshots/gui.png)

**`CLI` mode:**

![CLI Commands](https://raw.githubusercontent.com/hollowchest13/epub-to-markdown/main/screenshots/cli.png)

Upon first launch in CLI or GUI mode, the application will prompt for your Google Gemini API key and save it to a .env file.

Use Case
Designed for preparing book content for LLM fine-tuning and RAG systems, producing clean, structured Markdown output split by chapter.