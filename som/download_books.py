import time
import argparse
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


# Step 1: Archive.org API endpoint to search for free books
BASE_API_URL = "https://archive.org/advancedsearch.php"


# Function to query the API for public domain books
def search_books(page=1):
    query = {
        "q": "collection:(texts) AND mediatype:(texts)",
        "fl[]": "identifier,title",
        "rows": 50,  # Number of results per page (adjust if needed)
        "page": page,
        "output": "json",
    }
    response = requests.get(BASE_API_URL, params=query)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to query Archive.org")
        return None


# Step 2: Get the plain text URL for each book
def get_plain_text_url(identifier):
    metadata_url = f"https://archive.org/metadata/{identifier}"
    response = requests.get(metadata_url)
    if response.status_code == 200:
        metadata = response.json()
        if "files" in metadata:
            for file in metadata["files"]:
                if file["format"] == "DjVuTXT":
                    return f"https://archive.org/download/{identifier}/{file['name']}"
    return None


# Step 3: Download the plain text file
def download_plain_text(text_url, save_dir, book_title):
    response = requests.get(text_url, stream=True)
    if response.status_code == 200:
        file_path = os.path.join(save_dir, book_title + ".txt")
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"Downloaded: {book_title}")
    else:
        print(f"Failed to download: {book_title}")


# Step 4: Main loop to fetch and download all free books
def download_all_books(
    save_dir=PARENT_DIR / Path(f"data/archive_books"), min_pages=1, max_pages=5, delay=1
):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    page = min_pages
    while page <= max_pages:
        books = search_books(page)
        if books and "response" in books and "docs" in books["response"]:
            for book in books["response"]["docs"]:
                identifier = book["identifier"]
                title = book.get("title", identifier).replace(
                    "/", "_"
                )  # Clean up the title for filenames
                print(f"Processing book: {title}")

                # Step 2: Find the plain text URL
                text_url = get_plain_text_url(identifier)
                if text_url:
                    # Step 3: Download the plain text version
                    download_plain_text(text_url, save_dir, identifier)
                else:
                    print(f"No plain text available for {title}")

                # Step 5: Throttle requests to avoid overwhelming the server
                time.sleep(delay)

        # Step 6: Move to the next page of results
        page += 1
        print(f"Moving to page {page}")


def command_line_arguments():
    """Define and handle command line interface"""
    parser = argparse.ArgumentParser(
        description="Crawl real estate in germany.", prog="bookspider"
    )
    parser.add_argument(
        "--website",
        "-w",
        help="Website to download books from",
        choices=[
            "gutenberg",
            "archive",
        ],
        default="gutenberg",
        type=str,
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = command_line_arguments()
    if args.website == "gutenberg":
        for i in range(0, 80000):
            download_gutenberg_book(f"{i}")
    elif args.website == "archive":
        download_all_books(min_pages=1, max_pages=1_000_000)
