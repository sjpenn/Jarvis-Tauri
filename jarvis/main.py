"""JARVIS - Main entry point"""

import asyncio
import sys
from pathlib import Path

from jarvis.cli import app as cli_app


def main():
    """Main entry point for JARVIS"""
    cli_app()


if __name__ == "__main__":
    main()
