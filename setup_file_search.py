"""
Setup script to upload all SGX PDFs to Gemini File Search Store
Run this once to index all your documents.
"""

import json
import time
from pathlib import Path
from google import genai
from google.genai import types
from gemini_config import *

def check_prerequisites():
    """Check if all required files and API key exist."""
    print("Checking prerequisites...")

    if not GOOGLE_API_KEY:
        print("\n❌ ERROR: GOOGLE_API_KEY not found in environment variables")
        print("\nTo fix this:")
        print("1. Get your API key from: https://makersuite.google.com/app/apikey")
        print("2. Set it as an environment variable:")
        print("   Windows: set GOOGLE_API_KEY=your_key_here")
        print("   Linux/Mac: export GOOGLE_API_KEY=your_key_here")
        return False

    if not DOWNLOADS_FOLDER.exists():
        print(f"\n❌ ERROR: Downloads folder not found: {DOWNLOADS_FOLDER}")
        return False

    if not HISTORY_FILE.exists():
        print(f"\n❌ ERROR: History file not found: {HISTORY_FILE}")
        print("Please run the scraper first to download PDFs.")
        return False

    print("✓ All prerequisites met")
    return True

def load_download_history():
    """Load the download history JSON file."""
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_file_search_store(client):
    """Create a new File Search Store or load existing one."""
    print(f"\nCreating File Search Store: '{FILE_SEARCH_STORE_NAME}'...")

    # Check if we already have a store ID saved
    if STORE_ID_FILE.exists():
        with open(STORE_ID_FILE, 'r') as f:
            store_data = json.load(f)
            store_id = store_data.get('store_id')

            if store_id:
                print(f"Found existing store ID: {store_id}")
                try:
                    # Try to retrieve the existing store
                    store = client.file_search_stores.get(name=store_id)
                    print(f"✓ Using existing File Search Store")
                    return store
                except Exception as e:
                    print(f"Could not load existing store: {e}")
                    print("Creating new store...")

    # Create new store
    try:
        file_search_store = client.file_search_stores.create(
            config={'display_name': FILE_SEARCH_STORE_NAME}
        )

        # Save store ID for future use
        with open(STORE_ID_FILE, 'w') as f:
            json.dump({
                'store_id': file_search_store.name,
                'display_name': FILE_SEARCH_STORE_NAME,
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }, f, indent=2)

        print(f"✓ Created new File Search Store: {file_search_store.name}")
        return file_search_store

    except Exception as e:
        print(f"❌ Error creating File Search Store: {e}")
        raise

def upload_pdf(client, pdf_path, metadata_dict, file_search_store_name, index, total):
    """Upload a single PDF to the File Search Store with metadata."""
    filename = pdf_path.name
    print(f"\n[{index}/{total}] Processing: {filename}")

    try:
        # Prepare custom metadata
        custom_metadata = []

        if metadata_dict.get('announcement_title'):
            custom_metadata.append({
                "key": "announcement_title",
                "string_value": metadata_dict['announcement_title']
            })

        if metadata_dict.get('date_from_announcement'):
            custom_metadata.append({
                "key": "date",
                "string_value": metadata_dict['date_from_announcement']
            })

        if metadata_dict.get('announcement_url'):
            custom_metadata.append({
                "key": "announcement_url",
                "string_value": metadata_dict['announcement_url']
            })

        # Upload and import in one step
        operation = client.file_search_stores.upload_to_file_search_store(
            file=str(pdf_path),
            file_search_store_name=file_search_store_name,
            config={
                'display_name': filename,
                'chunking_config': CHUNK_CONFIG,
                'custom_metadata': custom_metadata if custom_metadata else None
            }
        )

        # Wait for operation to complete
        print(f"  Uploading and indexing...")
        wait_count = 0
        while not operation.done:
            time.sleep(3)
            operation = client.operations.get(operation)
            wait_count += 1
            if wait_count % 5 == 0:
                print(f"  Still indexing... ({wait_count * 3}s)")

        if operation.error:
            print(f"  ❌ Error: {operation.error}")
            return False
        else:
            print(f"  ✓ Successfully indexed")
            return True

    except Exception as e:
        print(f"  ❌ Failed to upload: {str(e)}")
        return False

def main():
    """Main setup function."""
    print("=" * 70)
    print("SGX Gemini File Search RAG Setup")
    print("=" * 70)

    # Check prerequisites
    if not check_prerequisites():
        return

    # Initialize Gemini client
    print(f"\nInitializing Gemini client...")
    client = genai.Client(api_key=GOOGLE_API_KEY)
    print("✓ Client initialized")

    # Create or load File Search Store
    file_search_store = create_file_search_store(client)

    # Load download history
    print(f"\nLoading download history from {HISTORY_FILE}...")
    history = load_download_history()
    total_pdfs = len(history['downloads'])
    print(f"✓ Found {total_pdfs} PDFs in history")

    # Upload all PDFs
    print(f"\n{'=' * 70}")
    print(f"Starting PDF Upload and Indexing")
    print(f"{'=' * 70}")

    successful_uploads = 0
    failed_uploads = 0
    skipped_files = 0

    for index, record in enumerate(history['downloads'], 1):
        filename = record['filename']
        pdf_path = DOWNLOADS_FOLDER / filename

        if not pdf_path.exists():
            print(f"\n[{index}/{total_pdfs}] ⚠ File not found: {filename}")
            skipped_files += 1
            continue

        # Extract metadata from download record
        metadata = {
            'announcement_title': record.get('announcement_title', ''),
            'date_from_announcement': record.get('date_from_announcement', ''),
            'announcement_url': record.get('announcement_url', ''),
            'pdf_url': record.get('pdf_url', '')
        }

        # Upload PDF
        success = upload_pdf(
            client,
            pdf_path,
            metadata,
            file_search_store.name,
            index,
            total_pdfs
        )

        if success:
            successful_uploads += 1
        else:
            failed_uploads += 1

    # Final summary
    print(f"\n{'=' * 70}")
    print("Setup Complete!")
    print(f"{'=' * 70}")
    print(f"✓ Successfully uploaded: {successful_uploads} PDFs")
    if failed_uploads > 0:
        print(f"❌ Failed uploads: {failed_uploads} PDFs")
    if skipped_files > 0:
        print(f"⚠ Skipped (not found): {skipped_files} PDFs")
    print(f"\nFile Search Store ID: {file_search_store.name}")
    print(f"Store ID saved to: {STORE_ID_FILE}")
    print(f"\nYou can now query your documents with: python rag_query.py")
    print(f"{'=' * 70}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
