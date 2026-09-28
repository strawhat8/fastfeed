# FastFeed

FastFeed is a small social-style media app built for easy sharing of photos and videos. The idea is simple: sign in, upload a file, and see it appear in a clean feed that feels more like a modern media platform than a basic demo app.

This project is meant to feel approachable and polished without being over-engineered. The frontend is powered by Streamlit, the backend uses FastAPI, and the data layer uses SQLAlchemy with SQLite for a lightweight local setup.

## What it does

- Lets users create an account and log in
- Uploads photos and videos
- Saves media locally in the project uploads folder
- Shows media in a feed with captions and descriptions
- Supports a premium dark/light visual style
- Keeps the project easy to run on a local machine

## Why this exists

This project was built to keep the workflow simple: upload content, store it, and view it as a feed. It is perfect for a small personal app, community gallery, or an internal media board where people can post content without needing a heavy production stack.

## Tech stack

- Python
- FastAPI
- Streamlit
- SQLAlchemy
- SQLite
- Pillow / image handling support
- Optional ImageKit integration via environment variables

## Project structure

- app/ – backend logic, database models, and schemas
- src/ – package structure for the app
- streamlit_app.py – the main Streamlit user interface
- uploads/ – local media files saved during uploads
- .env.example – example environment variables for secret settings

## Local setup

1. Create a virtual environment
   python -m venv .venv

2. Activate it
   On Windows PowerShell:
   .\.venv\Scripts\Activate.ps1

3. Install dependencies
   pip install -e .

4. Copy the environment template
   Copy-Item .env.example .env

5. Fill in any required values in .env if you are using ImageKit or other secret-based settings.

6. Run the app
   streamlit run streamlit_app.py

## Important note

The project is meant to be run locally and keeps secret values in a local .env file. Do not commit real credentials or ImageKit keys to GitHub.

## License

This project is provided as a personal app starter and can be adapted for your own use.
