import requests
from pathlib import Path
from bs4 import BeautifulSoup
import os

PARENT_DIR = Path(__file__).resolve().parent


# Function to download a book from Project Gutenberg
def download_gutenberg_book(
    book_id,
    save_dir=PARENT_DIR / Path(f"data/gutenberg_books"),
):
    # Construct the URL for the plain text version of the book
    url = f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt"

    # Try to request the page
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors

        # Create directory to save books, if not exists
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # Save the book as a .txt file
        book_path = os.path.join(save_dir, f"{book_id}.txt")
        with open(book_path, "w", encoding="utf-8") as book_file:
            book_file.write(response.text)
        print(f"Book {book_id} downloaded successfully and saved to {book_path}")

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred for book {book_id}: {http_err}")
    except Exception as err:
        print(f"An error occurred for book {book_id}: {err}")


# Example usage: Download a few books by their Project Gutenberg IDs
book_ids = [
    "1342",
    "11",
    "84",
    "5200",
]  # Example book IDs (Pride and Prejudice, Alice in Wonderland, etc.)
# for book_id in book_ids:
#     download_gutenberg_book(book_id)

for i in range(100):
    download_gutenberg_book(f"{i}")
