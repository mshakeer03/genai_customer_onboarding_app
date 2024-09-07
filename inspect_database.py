import argparse
import os
# from langchain_community.vectorstores import Chroma
from langchain_chroma import Chroma
from get_embedding_function import get_embedding_function

CHROMA_PATH = "chroma"

def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Show metadata for all entries.")
    args = parser.parse_args()

    # Inspect the database
    inspect_database(args.all)

def inspect_database(show_all):
    if not os.path.exists(CHROMA_PATH):
        print("❗ Database does not exist.")
        return

    # Load the existing database
    db = Chroma(
        persist_directory=CHROMA_PATH, embedding_function=get_embedding_function()
    )

    # Retrieve metadata for all documents
    metadata_items = db.get(include=["metadata"])  # Include metadata in the retrieval
    metadata = metadata_items.get("metadata", [])

    if show_all:
        print("Metadata for all entries:")
        for entry in metadata:
            print(entry)
    else:
        print(f"Number of entries in database: {len(metadata)}")
        for entry in metadata:
            # Print basic information (modify as needed for more details)
            print(f"ID: {entry.get('id')}")
            print(f"Source: {entry.get('source')}")
            print(f"Role: {entry.get('role')}")
            print(f"Account: {entry.get('account')}")
            print("---")

if __name__ == "__main__":
    main()
