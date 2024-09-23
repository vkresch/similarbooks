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
    # Create directory to save books, if it doesn't exist
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Path to the book file
    book_path = os.path.join(save_dir, f"{book_id}.txt")

    # Check if the book file already exists
    if os.path.exists(book_path):
        print(f"Book {book_id} already exists. Skipping download.")
        return

    # First URL format to try
    url_1 = f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt"
    # Second URL format if the first one fails
    url_2 = f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt"

    # Try to download using the first URL
    try:
        response = requests.get(url_1)
        response.raise_for_status()  # Check for HTTP errors (including 404)
        print(f"Successfully downloaded book {book_id} from {url_1}")

    except requests.exceptions.HTTPError as http_err:
        # If it's a 404 error, retry with the second URL
        if response.status_code == 404:
            print(f"404 error for {url_1}, retrying with {url_2}")
            try:
                response = requests.get(url_2)
                response.raise_for_status()  # Check for errors with the second URL
                print(f"Successfully downloaded book {book_id} from {url_2}")
            except requests.exceptions.HTTPError as http_err_2:
                print(f"Failed to download book {book_id} from both URLs: {http_err_2}")
                return
        else:
            print(f"HTTP error occurred for book {book_id} from {url_1}: {http_err}")
            return
    except Exception as err:
        print(f"An error occurred for book {book_id}: {err}")
        return

    # Save the book to a text file if successful
    with open(book_path, "w", encoding="utf-8") as book_file:
        book_file.write(response.text)
    print(f"Book {book_id} saved to {book_path}")


for i in range(0, 80000):
    download_gutenberg_book(f"{i}")
