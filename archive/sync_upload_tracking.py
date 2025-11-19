"""
Sync Upload Tracking - One-Time Script
Updates file_search_uploads.json to reflect that all current PDFs are already uploaded
"""

import json
import time
from pathlib import Path

# Configuration
DOWNLOADS_FOLDER = Path("downloads")
DOWNLOAD_HISTORY_FILE = DOWNLOADS_FOLDER / "download_history.json"
UPLOAD_TRACKING_FILE = Path("file_search_uploads.json")

# Your existing File Search store ID
EXISTING_STORE_ID = "fileSearchStores/sgxkeppeldcreitannouncement-73mjajo0c7d7"
STORE_DISPLAY_NAME = "sgx-keppel-dc-reit-announcements"

def main():
    """Sync the upload tracking file with current state."""
    print("=" * 70)
    print("Sync Upload Tracking")
    print("=" * 70)

    # Check if download history exists
    if not DOWNLOAD_HISTORY_FILE.exists():
        print(f"\n❌ Error: Download history not found at {DOWNLOAD_HISTORY_FILE}")
        print("Please run the scraper first to download PDFs.")
        return

    # Load download history
    print(f"\nLoading download history from {DOWNLOAD_HISTORY_FILE}...")
    with open(DOWNLOAD_HISTORY_FILE, 'r', encoding='utf-8') as f:
        download_history = json.load(f)

    total_files = len(download_history.get('downloads', []))
    print(f"✓ Found {total_files} PDFs in download history")

    # Check if tracking file already exists
    if UPLOAD_TRACKING_FILE.exists():
        print(f"\n⚠ Warning: {UPLOAD_TRACKING_FILE} already exists")
        overwrite = input("Overwrite? (yes/no): ").strip().lower()
        if overwrite not in ['yes', 'y']:
            print("Cancelled. No changes made.")
            return

    # Create upload tracking structure
    print(f"\nCreating upload tracking file...")
    print(f"Store ID: {EXISTING_STORE_ID}")

    current_time = time.strftime('%Y-%m-%d %H:%M:%S')

    uploaded_files = []
    for record in download_history.get('downloads', []):
        uploaded_files.append({
            'filename': record['filename'],
            'upload_date': record.get('download_date', current_time),  # Use download date as upload date
            'operation_id': 'manual-upload',  # Placeholder since these were uploaded manually
            'file_size': record.get('file_size', 0),
            'announcement_title': record.get('announcement_title', ''),
            'date_from_announcement': record.get('date_from_announcement', '')
        })

    tracking = {
        'store_id': EXISTING_STORE_ID,
        'store_display_name': STORE_DISPLAY_NAME,
        'uploaded_files': uploaded_files,
        'last_updated': current_time
    }

    # Save tracking file
    with open(UPLOAD_TRACKING_FILE, 'w', encoding='utf-8') as f:
        json.dump(tracking, f, indent=2, ensure_ascii=False)

    # Calculate total storage
    total_storage = sum(f['file_size'] for f in uploaded_files)

    # Summary
    print("\n" + "=" * 70)
    print("Sync Complete!")
    print("=" * 70)
    print(f"✓ Created: {UPLOAD_TRACKING_FILE}")
    print(f"✓ Store ID: {EXISTING_STORE_ID}")
    print(f"✓ Files marked as uploaded: {len(uploaded_files)}")
    print(f"✓ Total storage tracked: {total_storage / (1024*1024):.2f} MB")
    print("\nNext steps:")
    print("  - Run 'python upload_to_file_search.py' to upload only NEW files")
    print("  - Run 'python RAG.py' to start querying")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSync interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
