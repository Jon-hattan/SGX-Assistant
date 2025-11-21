"""
Upload Manager for Gemini File Search
Automatically uploads new PDFs from downloads/ to File Search store
"""

import json
import time
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DOWNLOADS_FOLDER = Path("downloads")
DOWNLOAD_HISTORY_FILE = DOWNLOADS_FOLDER / "download_history.json"
UPLOAD_TRACKING_FILE = DOWNLOADS_FOLDER / "file_search_uploads.json"
FILE_SEARCH_STORE_NAME = "sgx-keppel-dc-reit-announcements"

# Chunking configuration
CHUNK_CONFIG = {
    'white_space_config': {
        'max_tokens_per_chunk': 200,
        'max_overlap_tokens': 20
    }
}

def load_upload_tracking():
    """Load or create the upload tracking file."""
    if UPLOAD_TRACKING_FILE.exists():
        with open(UPLOAD_TRACKING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "store_id": None,
        "store_display_name": FILE_SEARCH_STORE_NAME,
        "uploaded_files": [],
        "last_updated": None
    }

def save_upload_tracking(tracking):
    """Save upload tracking file."""
    tracking['last_updated'] = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(UPLOAD_TRACKING_FILE, 'w', encoding='utf-8') as f:
        json.dump(tracking, f, indent=2, ensure_ascii=False)

def load_download_history():
    """Load download history."""
    if not DOWNLOAD_HISTORY_FILE.exists():
        print(f"❌ Error: Download history not found at {DOWNLOAD_HISTORY_FILE}")
        print("Please run the scraper first: python sgx_scraper.py")
        return None

    with open(DOWNLOAD_HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_or_create_store(client, tracking):
    """Get existing File Search store or create new one."""
    # Check if we have a saved store ID
    if tracking.get('store_id'):
        store_id = tracking['store_id']
        print(f"Using existing store: {store_id}")
        try:
            # Verify store exists
            store = client.file_search_stores.get(name=store_id)
            return store
        except Exception as e:
            print(f"Stored store ID invalid: {e}")
            print("Creating new store...")

    # Create new store
    print(f"Creating new File Search store: {FILE_SEARCH_STORE_NAME}...")
    try:
        store = client.file_search_stores.create(
            config={'display_name': FILE_SEARCH_STORE_NAME}
        )
        tracking['store_id'] = store.name
        save_upload_tracking(tracking)
        print(f"✓ Created store: {store.name}")
        return store
    except Exception as e:
        print(f"❌ Error creating store: {e}")
        raise

def find_new_files(download_history, tracking):
    """Find files that are downloaded but not yet uploaded."""
    downloaded_files = set(record['filename'] for record in download_history.get('downloads', []))
    uploaded_files = set(record['filename'] for record in tracking.get('uploaded_files', []))

    new_files = downloaded_files - uploaded_files
    return list(new_files)

def upload_file(client, pdf_path, metadata, store_name):
    """Upload a single PDF to File Search store."""
    filename = pdf_path.name

    try:
        # Prepare custom metadata
        custom_metadata = []

        if metadata.get('announcement_title'):
            custom_metadata.append({
                "key": "announcement_title",
                "string_value": metadata['announcement_title']
            })

        if metadata.get('date_from_announcement'):
            custom_metadata.append({
                "key": "date",
                "string_value": metadata['date_from_announcement']
            })

        if metadata.get('announcement_url'):
            custom_metadata.append({
                "key": "announcement_url",
                "string_value": metadata['announcement_url']
            })

        # Upload and import
        operation = client.file_search_stores.upload_to_file_search_store(
            file=str(pdf_path),
            file_search_store_name=store_name,
            config={
                'display_name': filename,
                'chunking_config': CHUNK_CONFIG,
                'custom_metadata': custom_metadata if custom_metadata else None
            }
        )

        # Wait for completion
        wait_count = 0
        while not operation.done:
            time.sleep(3)
            operation = client.operations.get(operation)
            wait_count += 1
            if wait_count % 5 == 0:
                print(f"    Still processing... ({wait_count * 3}s)")

        if operation.error:
            return False, str(operation.error)
        else:
            return True, operation.name

    except Exception as e:
        return False, str(e)

def main():
    """Main upload manager function."""
    print("=" * 70)
    print("Upload Manager - SGX File Search")
    print("=" * 70)

    # Check API key
    if not GOOGLE_API_KEY:
        print("\n❌ Error: GOOGLE_API_KEY not found")
        print("Please set it in your .env file or environment variables")
        return

    # Initialize client
    print("\nInitializing Gemini client...")
    client = genai.Client(api_key=GOOGLE_API_KEY)
    print("✓ Client initialized")

    # Load tracking
    print("\nLoading upload tracking...")
    tracking = load_upload_tracking()

    # Get or create store
    print("\nSetting up File Search store...")
    store = get_or_create_store(client, tracking)

    # Load download history
    print("\nLoading download history...")
    download_history = load_download_history()
    if not download_history:
        return

    total_downloads = len(download_history.get('downloads', []))
    already_uploaded = len(tracking.get('uploaded_files', []))
    print(f"✓ Download history: {total_downloads} PDFs")
    print(f"✓ Already uploaded: {already_uploaded} PDFs")

    # Find new files
    new_files = find_new_files(download_history, tracking)

    if not new_files:
        print("\n✓ All downloaded files are already uploaded!")
        print(f"Total in File Search store: {already_uploaded} PDFs")
        return

    print(f"\n📤 New files to upload: {len(new_files)} PDFs")
    print("=" * 70)

    # Create filename to metadata mapping
    metadata_map = {
        record['filename']: {
            'announcement_title': record.get('announcement_title', ''),
            'date_from_announcement': record.get('date_from_announcement', ''),
            'announcement_url': record.get('announcement_url', ''),
            'pdf_url': record.get('pdf_url', ''),
            'file_size': record.get('file_size', 0)
        }
        for record in download_history.get('downloads', [])
    }

    # Upload new files
    successful_uploads = 0
    failed_uploads = 0
    total_size_uploaded = 0

    for index, filename in enumerate(sorted(new_files), 1):
        pdf_path = DOWNLOADS_FOLDER / filename

        if not pdf_path.exists():
            print(f"\n[{index}/{len(new_files)}] ⚠ File not found: {filename}")
            failed_uploads += 1
            continue

        metadata = metadata_map.get(filename, {})
        file_size = metadata.get('file_size', 0)

        print(f"\n[{index}/{len(new_files)}] Uploading: {filename}")
        print(f"  Size: {file_size / (1024*1024):.2f} MB")

        success, result = upload_file(client, pdf_path, metadata, store.name)

        if success:
            print(f"  ✓ Uploaded successfully")

            # Add to tracking
            tracking['uploaded_files'].append({
                'filename': filename,
                'upload_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'operation_id': result,
                'file_size': file_size,
                'announcement_title': metadata.get('announcement_title', ''),
                'date_from_announcement': metadata.get('date_from_announcement', '')
            })

            # Save tracking after each upload
            save_upload_tracking(tracking)

            successful_uploads += 1
            total_size_uploaded += file_size
        else:
            print(f"  ❌ Failed: {result}")
            failed_uploads += 1

    # Final summary
    print("\n" + "=" * 70)
    print("Upload Complete!")
    print("=" * 70)
    print(f"✓ Successfully uploaded: {successful_uploads} PDFs")
    if failed_uploads > 0:
        print(f"❌ Failed uploads: {failed_uploads} PDFs")

    total_files_in_store = len(tracking['uploaded_files'])
    total_storage = sum(f.get('file_size', 0) for f in tracking['uploaded_files'])

    print(f"\n📊 File Search Store Status:")
    print(f"  Total files: {total_files_in_store} PDFs")
    print(f"  Total storage: {total_storage / (1024*1024):.2f} MB / 1024 MB")
    print(f"  Store ID: {store.name}")
    print(f"\n✓ Tracking saved to: {UPLOAD_TRACKING_FILE}")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nUpload interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
