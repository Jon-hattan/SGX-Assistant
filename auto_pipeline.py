"""
Automated SGX Scraper → File Search Upload Pipeline
Runs scraper to download new PDFs, then uploads them to File Search
"""

import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors."""
    print("\n" + "=" * 70)
    print(f"Running: {description}")
    print("=" * 70)

    try:
        result = subprocess.run(
            command,
            check=True,
            shell=True,
            capture_output=False,  # Show output in real-time
            text=True
        )
        print(f"\n✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with error code {e.returncode}")
        return False
    except Exception as e:
        print(f"\n❌ {description} failed: {e}")
        return False

def main():
    """Run the automated pipeline."""
    print("=" * 70)
    print("Automated SGX → File Search Pipeline")
    print("=" * 70)
    print("\nThis pipeline will:")
    print("1. Run the SGX scraper to download new announcements")
    print("2. Upload new PDFs to Gemini File Search")
    print("3. Ready for RAG queries\n")

    user_input = input("Continue? (yes/no): ").strip().lower()
    if user_input not in ['yes', 'y']:
        print("Pipeline cancelled.")
        return

    # Step 1: Run scraper
    scraper_success = run_command(
        f"{sys.executable} sgx_scraper_incremental.py",
        "SGX Scraper"
    )

    if not scraper_success:
        print("\n⚠ Scraper failed. Upload will not run.")
        print("Please check the error above and try again.")
        return

    # Step 2: Run upload manager
    upload_success = run_command(
        f"{sys.executable} upload_to_file_search.py",
        "File Search Upload Manager"
    )

    if not upload_success:
        print("\n⚠ Upload failed.")
        print("PDFs were downloaded but not uploaded to File Search.")
        print("You can run 'python upload_to_file_search.py' manually later.")
        return

    # Final summary
    print("\n" + "=" * 70)
    print("Pipeline Complete!")
    print("=" * 70)
    print("\n✓ All steps completed successfully")
    print("\nYou can now query your documents:")
    print("  python RAG.py")
    print("\nOr check what was uploaded:")
    print("  - downloads/download_history.json (download tracking)")
    print("  - file_search_uploads.json (upload tracking)")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
