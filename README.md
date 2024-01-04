# SIAK Score Notifier
A Selenium web scraper to track SIAK's academic scores and notifies the changes using Discord Webhook. Inspired by [rorre's Gist](https://gist.github.com/rorre/0f1506d942961613caf397b68d562176), but used Selenium instead.

## Requirements
- Python 3
- Docker Compose (optional; needed if python3 fails)

## Installation
#### Using Python 3
```sh
pip install -r requirements.txt
```
#### Using Docker Compose
If the Python installation fails, you might want to run in a containerized environment. Checkout the [official docs](https://docs.docker.com/compose/install/) for the installation.

## Running
1. Create a discord webhook, you can see [this](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) as a reference.
2. Create `.env` file, and fill it with your relevant data following the format shown in `.env.example`.
3. Choose the preferred method to run the program:
#### Using Python 3
```sh
python main.py
```
#### Using Docker Compose
If running with python3 fails, you might want to try using docker-compose.
```sh
docker-compose up --build -d
```