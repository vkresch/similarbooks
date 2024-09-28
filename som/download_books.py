import os
import logging
import time
import argparse
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from pymongo import MongoClient

PARENT_DIR = Path(__file__).resolve().parent

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Scraping API endpoint
SCRAPING_API_URL = "https://archive.org/services/search/v1/scrape"


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
        logging.info(f"Book {book_id} already exists. Skipping download.")
        return

    # First URL format to try
    url_1 = f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt"
    # Second URL format if the first one fails
    url_2 = f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt"

    # Try to download using the first URL
    try:
        response = requests.get(url_1)
        response.raise_for_status()  # Check for HTTP errors (including 404)
        logging.info(f"Successfully downloaded book {book_id} from {url_1}")

    except requests.exceptions.HTTPError as http_err:
        # If it's a 404 error, retry with the second URL
        if response.status_code == 404:
            logging.info(f"404 error for {url_1}, retrying with {url_2}")
            try:
                response = requests.get(url_2)
                response.raise_for_status()  # Check for errors with the second URL
                logging.info(f"Successfully downloaded book {book_id} from {url_2}")
            except requests.exceptions.HTTPError as http_err_2:
                logging.info(
                    f"Failed to download book {book_id} from both URLs: {http_err_2}"
                )
                return
        else:
            logging.info(
                f"HTTP error occurred for book {book_id} from {url_1}: {http_err}"
            )
            return
    except Exception as err:
        logging.info(f"An error occurred for book {book_id}: {err}")
        return

    # Save the book to a text file if successful
    with open(book_path, "w", encoding="utf-8") as book_file:
        book_file.write(response.text)
    logging.info(f"Book {book_id} saved to {book_path}")


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
        logging.info("Failed to query archive.org")
        return None


# Function to query the Scraping API using cursor-based pagination
def scrape_books(query, fields, count=100, cursor=None):
    params = {
        "q": query,
        "fields": fields,
        "count": count,
    }
    if cursor:
        params["cursor"] = cursor

    response = requests.get(SCRAPING_API_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        logging.info("Failed to query Archive.org")
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
    file_path = os.path.join(save_dir, book_title + ".txt")

    # Check if the file already exists
    if os.path.exists(file_path):
        logging.info(f"Book already exists: {book_title}. Skipping download.")
        return

    # If the file doesn't exist, proceed with downloading
    response = requests.get(text_url, stream=True)
    if response.status_code == 200:
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        logging.info(f"Downloaded: {book_title}")
    else:
        logging.info(f"Failed to download: {book_title}")


# Step 4: Main loop to fetch and download all free books
def download_all_books(save_dir=PARENT_DIR / Path(f"data/archive_books"), delay=1):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    query = "collection:(texts) AND mediatype:(texts)"
    fields = "identifier,title"
    count = 100  # Number of results to return per query
    cursor = None  # Initialize cursor

    while True:
        # Fetch books using the Scraping API
        result = scrape_books(query=query, fields=fields, count=count, cursor=cursor)
        if result and "items" in result:
            for book in result["items"]:
                identifier = book["identifier"]
                title = book.get("title", identifier).replace("/", "_")
                logging.info(f"Processing book: {title}")

                # Step 2: Find the plain text URL
                text_url = get_plain_text_url(identifier)
                if text_url:
                    # Step 3: Download the plain text version
                    download_plain_text(text_url, save_dir, identifier)
                else:
                    logging.info(f"No plain text available for {title}")

                # Step 5: Throttle requests to avoid overwhelming the server
                time.sleep(delay)

            # Update cursor for the next batch of results
            cursor = result.get("cursor")
            if not cursor:
                break  # Stop if there are no more results
        else:
            logging.info("No more results or failed to fetch results.")
            break


def download_book_cover(sha, url):
    # Send an HTTP request to the URL
    response = requests.get(url)

    savedir = PARENT_DIR / Path(f"../app/similarbooks/static/covers/{sha}.png")

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Read the image data from the response content
        img_data = response.content

        # Use BytesIO to open the image data as a PIL image
        img = Image.open(BytesIO(img_data))

        # Save the image locally
        img.save(savedir)
        logging.info(f"Image {sha} downloaded and saved successfully!")
    else:
        logging.info(
            f"Failed to download image {sha}. Status code: {response.status_code}"
        )

    time.sleep(1)


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
            "goodreadscovers",
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
        download_all_books()
    elif args.website == "goodreadscovers":
        MONGODB_SIMILARBOOKS_URL = os.environ.get("MONGODB_SIMILARBOOKS_URL")
        MONGODB_SIMILARBOOKS_USER = os.environ.get("MONGODB_SIMILARBOOKS_USER")
        MONGODB_SIMILARBOOKS_PWD = os.environ.get("MONGODB_SIMILARBOOKS_PWD")
        MONGODB_SIMILARBOOKS_URI = f"mongodb://{MONGODB_SIMILARBOOKS_USER}:{MONGODB_SIMILARBOOKS_PWD}@{MONGODB_SIMILARBOOKS_URL}:27017/similarbooks?authMechanism=DEFAULT&authSource=similarbooks&tls=true&tlsCAFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.crt&tlsCertificateKeyFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.pem"
        client = MongoClient(MONGODB_SIMILARBOOKS_URI)
        db = client["similarbooks"]
        collection = db["book"]
        filter_query = {"title": {"$exists": False}, "spider": "goodreads"}
        pipeline = [
            {"$match": filter_query},
            {"$sample": {"size": 10_000_000}},  # Adjust the size as needed
        ]
        result = collection.aggregate(pipeline)
        for item in result:
            image_url = item.get("image_url")
            if image_url:
                download_book_cover(item["sha"], image_url)
