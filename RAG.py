from google import genai
from google.genai import types
import time
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv() 

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# stores = client.file_search_stores.list()

# for store in stores:
#     print(store.name, store.display_name)

# # Create the File Search store with an optional display name
# file_search_store = client.file_search_stores.create(config={'display_name': 'keppel_dc_reit'})

# # Upload and import a file into the File Search store, supply a file name which will be visible in citations
# operation = client.file_search_stores.upload_to_file_search_store(
#   file='downloads/2025-11-18_Keppel DC REIT - Acquisition Announcement 16 September 2019.pdf',
#   file_search_store_name=file_search_store.name,
#   config={
#       'display_name' : '2025-11-18_Keppel DC REIT - Acquisition Announcement 16 September 2019.pdf',
#   }
# )

# # Wait until import is complete
# while not operation.done:
#     time.sleep(5)
#     operation = client.operations.get(operation)


# Interactive Q&A with File Search
file_search_store_name = 'fileSearchStores/sgxkeppeldcreitannouncement-73mjajo0c7d7'

print("\n" + "="*70)
print("File Search RAG - Interactive Mode")
print("="*70)
print("Ask questions about Keppel DC REIT announcements")
print("Type 'quit' or 'exit' to end the session")
print("="*70 + "\n")

while True:
    # Get question from user
    question = input("Your question: ").strip()

    if not question:
        continue

    # Check for exit commands
    if question.lower() in ['quit', 'exit', 'q']:
        print("Goodbye!")
        break

    # Query the file search store
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=question,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[file_search_store_name]
                        )
                    )
                ]
            )
        )

        print("\nAnswer:")
        print("-" * 70)
        print(response.text)
        print("-" * 70 + "\n")

    except Exception as e:
        print(f"\nError: {e}\n")