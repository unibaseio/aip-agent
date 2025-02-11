from . import chroma
import asyncio

def main():
    """Main entry point for the package."""
    asyncio.run(chroma.main())

# Optionally expose other important items at package level
__all__ = ['main', 'chroma']