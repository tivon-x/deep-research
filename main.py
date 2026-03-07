"""Convenient script entrypoint for local CLI usage."""
from dotenv import load_dotenv

from src.cli import main

load_dotenv(override=True)  # Load environment variables from .env file

if __name__ == "__main__":
    main()
