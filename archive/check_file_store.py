"""
Prints all the file names currently in the file store.
"""


from google import genai
from google.genai import types
import time
from dotenv import load_dotenv
import os
import json
from pathlib import Path

# Load .env file
load_dotenv()


client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Load File Search store ID from tracking file
DOWNLOADS_FOLDER = Path("downloads")
UPLOAD_TRACKING_FILE = DOWNLOADS_FOLDER / "file_search_uploads.json"


def load_store_id():
    """Load the File Search store ID from tracking file."""
    if not UPLOAD_TRACKING_FILE.exists():
        print(f"\n❌ Error: Upload tracking file not found: {UPLOAD_TRACKING_FILE}")
        print("\nPlease run the upload manager first:")
        print("  python upload_to_file_search.py")
        return None

    with open(UPLOAD_TRACKING_FILE, 'r', encoding='utf-8') as f:
        tracking = json.load(f)

    store_id = tracking.get('store_id')
    if not store_id:
        print(f"\n❌ Error: No store_id found in {UPLOAD_TRACKING_FILE}")
        print("\nPlease run the upload manager first:")
        print("  python upload_to_file_search.py")
        return None

    total_files = len(tracking.get('uploaded_files', []))
    print(f"Loaded File Search store with {total_files} PDFs")
    return store_id

# Interactive Q&A with File Search
file_search_store_name = load_store_id()

if not file_search_store_name:
    print("\nCannot start interactive mode without a File Search store.")
    exit(1)


docs = client.file_search_stores.documents.list(parent=file_search_store_name)
for doc in docs:
    print(doc.display_name + "\n")