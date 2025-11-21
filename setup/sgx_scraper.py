"""Scrapes the SGX Announcement Site for Filings TILL 2021"""
"""Doesn't redownload duplicates, does not stop until 2021 is reached or 1GB storage is reached."""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
import os
import re
import json
import hashlib
from datetime import datetime

# Constants
STORAGE_LIMIT_BYTES = 1024 * 1024 * 1024  # 1GB in bytes
SLIDING_WINDOW_SIZE = 50  # Keep hashes from last 50 PDFs for duplicate detection

# Helper functions for download history management
def calculate_file_hash(file_path):
    """Calculate SHA256 hash of file content."""
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

# Loads download history from json file, with path: downloads/downloads_history.json
# returns: python object (dictionary) that contains the info from the json file.
def load_history():
    history_file = os.path.join('downloads', 'download_history.json')
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print("Warning: Could not load history file, starting fresh")
            return {"last_updated": None, "total_downloads": 0, "downloads": []}
    return {"last_updated": None, "total_downloads": 0, "downloads": []}

# takes in history (dictionary) which contains all the download history from the current downloads,
#   and loads it into the download_history.json file.
def save_history(history):
    history_file = os.path.join('downloads', 'download_history.json')
    history['last_updated'] = datetime.now().isoformat()
    history['total_downloads'] = len(history['downloads'])
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Warning: Could not save history: {e}")

# checks if the file is a duplicate (i.e it has alr been downloaded)
# Checks if file is in download history, or on disk.
def is_duplicate(pdf_url, filename, history):
    # Check if URL already exists in history
    for record in history.get('downloads', []):
        if record.get('pdf_url') == pdf_url:
            return True, "URL already in history"
        if record.get('filename') == filename:
            return True, "Filename already in history"

    # Check if file exists on disk
    file_path = os.path.join('downloads', filename)
    if os.path.exists(file_path):
        return True, "File already exists on disk"

    return False, None

# Add a specific record to history (which is a dictionary)
def add_to_history(history, pdf_url, filename, announcement_url, announcement_title, date_str, file_size):
    """Add a download record to history."""
    record = {
        "pdf_url": pdf_url,
        "filename": filename,
        "announcement_url": announcement_url,
        "announcement_title": announcement_title,
        "download_date": datetime.now().isoformat(),
        "file_size": file_size,
        "date_from_announcement": date_str
    }
    history['downloads'].append(record)

# Calculate total storage used by all downloads in bytes
def get_total_storage(history):
    return sum(record.get('file_size', 0) for record in history.get('downloads', []))

# Setup downloads folder
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
print(f"Downloads folder ready: {DOWNLOAD_FOLDER}")

# Setup browser
options = Options() # create a browser configuration object
options.add_argument('--start-maximized') # window should start out fully maximised

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
) # launch chrome browser with the options i set up above

# Load download history
history = load_history()
total_storage = get_total_storage(history)
print(f"Loaded history: {history['total_downloads']} previous downloads ({total_storage / (1024*1024):.2f} MB used)")

# Multi-page scraping setup
BASE_URL = "https://www.sgx.com/securities/company-announcements?pagesize=100&ANNC=ANNC05%2CANNC30%2CANNC06%2CANNC07%2CANNC31%2CANNC29%2CANNC10%2CANNC17%2CANNC18%2CANNC21%2CANNC22%2CANNC13%2CANNC26%2CANNC27&value=KEPPEL%20DC%20REIT&type=securityname&page="
reached_2021 = False

# Overall statistics
pdf_count = 0
skipped_count = 0

# Sliding window for content-based duplicate detection (catches same PDFs with different names)
recent_hashes = []  # List of {"hash": "abc123...", "filename": "file.pdf"}

print(f"\nStarting PDF download (storage limit: {STORAGE_LIMIT_BYTES / (1024*1024):.0f} MB)...")
print(f"Will download from all pages until reaching announcements from 2021 or earlier.\n")

# Page loop - continue until reaching 2021 or running out of pages
page_num = 1
while not reached_2021:
    # Visit the announcements listing page
    url = f"{BASE_URL}{page_num}"
    print(f"\n{'='*60}")
    print(f"PAGE {page_num}")
    print(f"{'='*60}")
    print(f"Opening: {url}")
    driver.get(url) # launch the SGX website

    # Wait for page to load
    print("Waiting for announcements table to load...")
    time.sleep(10)

    # Extract announcement URLs from the table
    print("Extracting announcement URLs...")
    announcement_links = driver.find_elements(By.CSS_SELECTOR, 'table.widget-filter-listing-content-table tbody tr td a.website-link')
    announcement_urls = []

    # Every relevant link will have corporate-announcements as the signature. just search for that
    for link in announcement_links:
        href = link.get_attribute('href')
        if href and 'corporate-announcements' in href:
            announcement_urls.append(href)

    print(f"Found {len(announcement_urls)} announcement links on page {page_num}")

    # Check if page has no announcements (reached end of pages)
    if not announcement_urls:
        print("No announcements found on this page. Reached end of available pages.")
        break

    # Process announcements on this page
    announcement_index = 0

    while announcement_index < len(announcement_urls):
        # Check storage limit before processing next announcement
        current_storage = get_total_storage(history)
        if current_storage >= STORAGE_LIMIT_BYTES:
            print(f"\n⚠ Storage limit reached ({current_storage / (1024*1024):.2f} MB / {STORAGE_LIMIT_BYTES / (1024*1024):.0f} MB)")
            print("Stopping downloads to stay within limit.\n")
            reached_2021 = True  # Stop pagination
            break

        announcement_url = announcement_urls[announcement_index]
        announcement_index += 1

        try:
            print(f"[{announcement_index}/{len(announcement_urls)}] Visiting announcement...")
            driver.get(announcement_url) # Go into the announcements page
            time.sleep(5)  # Wait for announcement page to load

            # Extract announcement title
            title_element = driver.find_elements(By.CSS_SELECTOR, 'h1, .announcement-title, .title')
            announcement_title = title_element[0].text.strip() if title_element else "Unknown Announcement"

            # Extract date from announcement page
            date_element = driver.find_elements(By.CSS_SELECTOR, '.announcement-date, .date-time')
            date_str = ""
            if date_element:
                date_text = date_element[0].text.strip()
                # Parse date (format: "15 Oct 2025 08:30 PM")
                try:
                    date_obj = datetime.strptime(date_text.split()[0:3].__str__().replace("['", "").replace("']", "").replace("',", "").replace(" '", " "), '%d %b %Y')
                    date_str = date_obj.strftime('%Y-%m-%d')

                    # Check if this announcement is from 2021 or earlier
                    announcement_year = date_obj.year
                    if announcement_year <= 2021:
                        print(f"  📅 Found announcement from {announcement_year} - will stop after this page")
                        reached_2021 = True
                except:
                    # Fallback to extracting from URL or using current date
                    date_str = datetime.now().strftime('%Y-%m-%d')
            else:
                date_str = datetime.now().strftime('%Y-%m-%d')

            # Find ALL PDF links with class "announcement-attachment"
            pdf_links = driver.find_elements(By.CSS_SELECTOR, 'a.announcement-attachment')

            if not pdf_links:
                print(f"  No PDF attachments found. Skipping...\n")
                continue

            print(f"  Found {len(pdf_links)} PDF(s) in this announcement")

            # Track filenames downloaded in THIS announcement (to avoid same-page duplicates)
            downloaded_in_this_announcement = set()

            # Download ALL PDFs from this announcement
            for pdf_index, pdf_link in enumerate(pdf_links, 1):
                pdf_href = pdf_link.get_attribute('href')
                pdf_text = pdf_link.text.strip()

                # Construct full PDF URL if it's relative
                if pdf_href.startswith('/'):
                    pdf_url = f"https://links.sgx.com{pdf_href}"
                else:
                    pdf_url = pdf_href

                # Sanitize filename (jic the filename has something stupid like ?)
                original_filename = pdf_text if pdf_text else pdf_href.split('/')[-1]
                safe_filename = re.sub(r'[<>:"/\\|?*]', '_', original_filename) 

                # Create final filename with date prefix
                final_filename = f"{date_str}_{safe_filename}"
                file_path = os.path.join(DOWNLOAD_FOLDER, final_filename)

                # Check for same-page duplicates first (e.g., "click here if unable to view" fallback links)
                if final_filename in downloaded_in_this_announcement:
                    print(f"  [{pdf_index}/{len(pdf_links)}] Skipping (duplicate): Same file already downloaded from this announcement")
                    skipped_count += 1
                    continue

                # Check for global duplicates (history + disk)
                is_dup, dup_reason = is_duplicate(pdf_url, final_filename, history)
                if is_dup:
                    print(f"  [{pdf_index}/{len(pdf_links)}] Skipping (duplicate): {dup_reason}")
                    skipped_count += 1
                    continue

                # Download PDF using requests
                print(f"  [{pdf_index}/{len(pdf_links)}] Downloading: {final_filename}")
                try:
                    response = requests.get(pdf_url, timeout=30)
                    response.raise_for_status()

                    with open(file_path, 'wb') as f:
                        f.write(response.content)

                    file_size = len(response.content)

                    # Calculate file hash to check for content-based duplicates
                    file_hash = calculate_file_hash(file_path)

                    # Check if this exact content was downloaded recently (sliding window)
                    matching_hashes = [h for h in recent_hashes if h["hash"] == file_hash]
                    if matching_hashes:
                        # Same content already downloaded with different name - delete and skip
                        matching_file = matching_hashes[0]["filename"]
                        os.remove(file_path)
                        print(f"  ⏭ Skipping (duplicate content): Same as '{matching_file}' from recent announcement")
                        skipped_count += 1
                        continue

                    # File is unique - keep it and add to tracking
                    pdf_count += 1

                    # Add to history and save
                    add_to_history(history, pdf_url, final_filename, announcement_url,
                                  announcement_title, date_str, file_size)
                    save_history(history)

                    # Mark as downloaded in this announcement (only on success)
                    downloaded_in_this_announcement.add(final_filename)

                    # Add to sliding window for future content comparison
                    recent_hashes.append({"hash": file_hash, "filename": final_filename})
                    # Maintain window size
                    if len(recent_hashes) > SLIDING_WINDOW_SIZE:
                        recent_hashes.pop(0)

                    current_storage = get_total_storage(history)
                    print(f"  ✓ Downloaded ({pdf_count} total, {current_storage / (1024*1024):.2f} MB used)")

                except Exception as download_error:
                    print(f"  ✗ Failed to download: {str(download_error)}")
                    # Don't add to downloaded_in_this_announcement, so fallback link can be tried

            print()  # Blank line between announcements

        except Exception as e:
            print(f"  Error processing announcement: {str(e)}\n")
            continue

    # After processing all announcements on this page
    if reached_2021:
        print(f"\n{'='*60}")
        print("Reached announcements from 2021 or earlier. Stopping pagination.")
        print(f"{'='*60}\n")
        break

    # Move to next page
    page_num += 1
    print(f"\nMoving to page {page_num}...")

# Final summary
final_storage = get_total_storage(history)
print(f"\n{'='*60}")
print(f"Download Session Complete!")
print(f"{'='*60}")
print(f"📥 New PDFs downloaded this session: {pdf_count}")
print(f"⏭  Duplicates skipped: {skipped_count}")
print(f"📊 Total PDFs in history: {history['total_downloads']}")
print(f"💾 Total storage used: {final_storage / (1024*1024):.2f} MB / {STORAGE_LIMIT_BYTES / (1024*1024):.0f} MB")
print(f"📁 Files location: {DOWNLOAD_FOLDER}/")
print(f"📝 History file: {DOWNLOAD_FOLDER}/download_history.json")
print(f"{'='*60}\n")

driver.quit()