"""
Delete Most Recent File from Gemini File Search
Removes the most recently uploaded file from the File Search store (does not update tracking JSON).
"""

import json
import os
from pathlib import Path
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
UPLOAD_TRACKING_FILE = Path("downloads/file_search_uploads.json")

def load_tracking():
    """Load upload tracking file."""
    if not UPLOAD_TRACKING_FILE.exists():
        print(f"❌ Error: Tracking file not found: {UPLOAD_TRACKING_FILE}")
        print("No files have been uploaded yet.")
        return None

    with open(UPLOAD_TRACKING_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_most_recent_file(tracking):
    """Find the most recently uploaded file."""
    uploaded_files = tracking.get('uploaded_files', [])

    if not uploaded_files:
        print("No files found in tracking.")
        return None

    # Sort by upload_date (most recent first)
    sorted_files = sorted(
        uploaded_files,
        key=lambda x: x.get('upload_date', ''),
        reverse=True
    )

    return sorted_files[0]

def delete_file_from_store(client, store_id, filename):
    """
    Delete a file from the File Search store using the correct API.
    Based on: https://www.philschmid.de/gemini-file-search-javascript
    """
    try:
        print(f"  Listing documents in store...")

        # List all documents in the store
        documents = client.file_search_stores.documents.list(parent=store_id)

        # Find the document matching the filename
        target_doc = None
        for doc in documents:
            if hasattr(doc, 'display_name') and doc.display_name == filename:
                target_doc = doc
                break

        if not target_doc:
            return False, f"Document '{filename}' not found in File Search store"

        print(f"  Found document: {target_doc.name}")
        print(f"  Deleting document...")

        # Delete the document with force=True (required for permanent deletion)
        client.file_search_stores.documents.delete(
            name=target_doc.name,
            config={'force': True}
        )

        return True, "Successfully deleted from File Search store"

    except Exception as e:
        return False, f"Error deleting from store: {str(e)}"

def main():
    """Main deletion function."""
    print("=" * 70)
    print("Delete Most Recent File from File Search")
    print("=" * 70)

    # Check API key
    if not GOOGLE_API_KEY:
        print("\n❌ Error: GOOGLE_API_KEY not found")
        print("Please set it in your .env file")
        return

    # Load tracking
    print("\nLoading tracking file...")
    tracking = load_tracking()
    if not tracking:
        return

    store_id = tracking.get('store_id')
    total_files = len(tracking.get('uploaded_files', []))

    print(f"✓ Found {total_files} files in tracking")

    if total_files == 0:
        print("No files to delete.")
        return

    # Find most recent file
    most_recent = find_most_recent_file(tracking)
    if not most_recent:
        return

    # Display file details
    print("\n" + "=" * 70)
    print("Most Recent File:")
    print("=" * 70)
    print(f"Filename: {most_recent['filename']}")
    print(f"Uploaded: {most_recent['upload_date']}")
    print(f"Size: {most_recent.get('file_size', 0) / (1024*1024):.2f} MB")
    if most_recent.get('announcement_title'):
        print(f"Title: {most_recent['announcement_title']}")
    if most_recent.get('date_from_announcement'):
        print(f"Date: {most_recent['date_from_announcement']}")
    print("=" * 70)

    # Confirm deletion
    confirm = input("\nDelete this file? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("Deletion cancelled.")
        return

    # Initialize client
    print("\nInitializing Gemini client...")
    client = genai.Client(api_key=GOOGLE_API_KEY)

    # Delete from store
    print("\nDeleting from File Search store...")
    success, message = delete_file_from_store(
        client,
        store_id,
        most_recent['filename']
    )

    if not success:
        print(f"❌ Failed to delete: {message}")
        return

    print(f"✓ {message}")

    # Final summary
    print("\n" + "=" * 70)
    print("Deletion Complete!")
    print("=" * 70)
    print(f"✓ Deleted from File Search: {most_recent['filename']}")
    print(f"💡 Note: Tracking JSON not updated (file still listed in {UPLOAD_TRACKING_FILE})")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDeletion cancelled by user.")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
