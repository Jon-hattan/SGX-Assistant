"""
Configuration for Gemini File Search RAG Pipeline
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv() 

# API Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


if not GOOGLE_API_KEY:
    print("WARNING: GOOGLE_API_KEY environment variable not set")
    print("Please set it with: set GOOGLE_API_KEY=your_key_here (Windows)")
    print("or: export GOOGLE_API_KEY=your_key_here (Linux/Mac)")

# File Search Store Configuration
FILE_SEARCH_STORE_NAME = "sgx-keppel-dc-reit-announcements"
STORE_ID_FILE = Path("file_search_store.json")

# Paths
DOWNLOADS_FOLDER = Path("downloads")
HISTORY_FILE = DOWNLOADS_FOLDER / "download_history.json"

# Chunking Configuration (for optimal retrieval)
CHUNK_CONFIG = {
    'white_space_config': {
        'max_tokens_per_chunk': 200,  # Smaller chunks for better precision
        'max_overlap_tokens': 20       # Overlap to maintain context
    }
}

# Query Configuration
DEFAULT_MODEL = "gemini-2.5-flash"  # Fast and cost-effective
TOP_K_RESULTS = 5                   # Number of chunks to retrieve per query
ENABLE_CITATIONS = True              # Show source documents
