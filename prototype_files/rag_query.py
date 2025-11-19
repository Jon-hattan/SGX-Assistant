"""
Interactive RAG query interface using Gemini File Search
Query your SGX announcement PDFs with natural language.
"""

import json
from google import genai
from google.genai import types
from gemini_config import *

class SGXRAGAssistant:
    def __init__(self):
        """Initialize the RAG assistant."""
        # Check API key
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not set. Please set it as an environment variable.")

        # Initialize client
        self.client = genai.Client(api_key=GOOGLE_API_KEY)

        # Load File Search Store
        self.file_search_store = self._load_store()

    def _load_store(self):
        """Load the File Search Store from saved ID."""
        if not STORE_ID_FILE.exists():
            raise FileNotFoundError(
                f"File Search Store not found: {STORE_ID_FILE}\n"
                "Please run 'python setup_file_search.py' first to upload your PDFs."
            )

        with open(STORE_ID_FILE, 'r') as f:
            store_data = json.load(f)
            store_id = store_data.get('store_id')

        if not store_id:
            raise ValueError("No store_id found in file_search_store.json")

        print(f"Loaded File Search Store: {store_id}")
        return store_id

    def query(self, question, metadata_filter=None, show_citations=True):
        """
        Query the File Search Store with a question.

        Args:
            question: User's question
            metadata_filter: Optional metadata filter (e.g., "date=2024-01-15")
            show_citations: Whether to display source citations

        Returns:
            Dictionary with answer and citation info
        """
        try:
            # Build File Search tool config
            file_search_config = types.FileSearch(
                file_search_store_names=[self.file_search_store]
            )

            if metadata_filter:
                file_search_config.metadata_filter = metadata_filter

            # Generate response
            response = self.client.models.generate_content(
                model=DEFAULT_MODEL,
                contents=question,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(file_search=file_search_config)]
                )
            )

            # Extract answer
            answer = response.text if response.text else "No answer generated."

            # Extract grounding metadata (citations)
            citations = []
            if show_citations and hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                    grounding = candidate.grounding_metadata

                    # Extract grounding chunks
                    if hasattr(grounding, 'grounding_chunks') and grounding.grounding_chunks:
                        for chunk in grounding.grounding_chunks:
                            citation_info = {}

                            # Extract document metadata
                            if hasattr(chunk, 'web') and chunk.web:
                                citation_info['source'] = chunk.web.uri if hasattr(chunk.web, 'uri') else 'Unknown'

                            # Try to get file metadata from the chunk
                            if hasattr(chunk, 'retrieved_context'):
                                context = chunk.retrieved_context
                                if hasattr(context, 'title'):
                                    citation_info['filename'] = context.title
                                if hasattr(context, 'text'):
                                    citation_info['excerpt'] = context.text[:200] + "..." if len(context.text) > 200 else context.text

                            if citation_info:
                                citations.append(citation_info)

            return {
                'answer': answer,
                'citations': citations
            }

        except Exception as e:
            return {
                'answer': f"Error querying the system: {str(e)}",
                'citations': []
            }

    def interactive_mode(self):
        """Run interactive query mode."""
        print("\n" + "=" * 70)
        print("SGX RAG Assistant - Interactive Mode")
        print("=" * 70)
        print("Ask questions about Keppel DC REIT announcements")
        print("\nCommands:")
        print("  'quit' or 'exit' - Exit the program")
        print("  'filter DATE' - Filter by date (e.g., 'filter 2024-01-15')")
        print("  'clear filter' - Remove date filter")
        print("=" * 70 + "\n")

        current_filter = None

        while True:
            try:
                # Get user input
                user_input = input("\nYour question: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break

                if user_input.lower().startswith('filter '):
                    date = user_input[7:].strip()
                    current_filter = f"date={date}"
                    print(f"✓ Filter set: {current_filter}")
                    continue

                if user_input.lower() == 'clear filter':
                    current_filter = None
                    print("✓ Filter cleared")
                    continue

                # Query the system
                print("\nSearching...")
                result = self.query(
                    user_input,
                    metadata_filter=current_filter,
                    show_citations=ENABLE_CITATIONS
                )

                # Display answer
                print("\n" + "-" * 70)
                print("ANSWER:")
                print("-" * 70)
                print(result['answer'])

                # Display citations if available
                if result['citations']:
                    print("\n" + "-" * 70)
                    print(f"SOURCES ({len(result['citations'])} documents):")
                    print("-" * 70)
                    for i, citation in enumerate(result['citations'], 1):
                        print(f"\n[{i}]")
                        if 'filename' in citation:
                            print(f"  File: {citation['filename']}")
                        if 'source' in citation:
                            print(f"  Source: {citation['source']}")
                        if 'excerpt' in citation:
                            print(f"  Excerpt: {citation['excerpt']}")

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

def example_queries():
    """Run some example queries to demonstrate the system."""
    assistant = SGXRAGAssistant()

    examples = [
        "What acquisitions did Keppel DC REIT make in 2024?",
        "What were the financial results in the most recent quarter?",
        "Summarize any divestments or asset sales",
        "What is the current dividend policy?",
        "Where are Keppel DC REIT's data centres located?"
    ]

    print("\n" + "=" * 70)
    print("Running Example Queries")
    print("=" * 70)

    for i, question in enumerate(examples, 1):
        print(f"\n[Example {i}] {question}")
        print("-" * 70)

        result = assistant.query(question)
        print(result['answer'][:500] + "..." if len(result['answer']) > 500 else result['answer'])

        if result['citations']:
            print(f"\nCitations: {len(result['citations'])} sources")

        input("\nPress Enter to continue...")

def main():
    """Main entry point."""
    import sys

    try:
        assistant = SGXRAGAssistant()

        # Check if user wants to run examples
        if len(sys.argv) > 1 and sys.argv[1] == "--examples":
            example_queries()
        else:
            assistant.interactive_mode()

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease run the setup script first:")
        print("  python setup_file_search.py")

    except ValueError as e:
        print(f"\n❌ Error: {e}")

    except KeyboardInterrupt:
        print("\n\nGoodbye!")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
