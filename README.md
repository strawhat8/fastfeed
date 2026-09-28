# FastFeed

FastFeed is a simple social-style media app built for sharing photos and videos in a clean, modern feed. The idea is straightforward: create an account, upload content, and instantly see it appear in a polished gallery that feels like a lightweight media platform.

This project is designed to be easy to understand and easy to run. The frontend is built with Streamlit, the API layer uses FastAPI, and the app stores data with SQLAlchemy and SQLite so it works well as a small local project without extra complexity.

## What it does

- Lets users sign up and log in
- Uploads photos and videos
- Saves media locally in the project uploads folder
- Displays posts in a feed with captions and descriptions
- Supports a sleek dark/light visual style
- Keeps the project simple enough for local use and quick iteration

## Why this project exists

FastFeed was created to make media sharing feel accessible and fun without building a huge production system. It is a good fit for personal projects, internal team sharing, or small community-style posting where people want a clear feed and a simple upload flow.

## Tech stack

- Python
- FastAPI
- Streamlit
- SQLAlchemy
- SQLite
- Optional ImageKit integration through environment variables

## Project structure

- app/ – backend logic, database models, and schemas
- src/ – package structure for the app
- streamlit_app.py – the main Streamlit interface
- uploads/ – local media files saved during uploads
- .env.example – safe example environment variables

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

5. Fill in secret values only in your local .env file if you are using ImageKit or other external services.

6. Start the app
   streamlit run streamlit_app.py

## Important note

This app is intended to be run locally. Keep secret values in a local .env file and never commit real credentials, API keys, or ImageKit secrets to GitHub.

## License

This project is shared as a starter app for personal or learning use and can be adapted to your own needs.
>>>>>>> origin/main
