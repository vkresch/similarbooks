import os
import logging
import time
from pathlib import Path
from pymongo import MongoClient

PARENT_DIR = Path(__file__).resolve().parent

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
base_url = "https://findsimilarbooks.com/book/"
chunk_size = 25000  # Maximum number of URLs per sitemap
sitemap_dir = PARENT_DIR / Path(
    f"../app/similarbooks/static/"
)  # Directory to save the sitemap files

# Static URLs to be included in the first sitemap
static_urls = [
    {
        "loc": "https://www.findsimilarbooks.com/",
        "lastmod": "2024-06-29T14:43:21+00:00",
        "priority": "1.00",
    },
    {
        "loc": "https://www.findsimilarbooks.com/about",
        "lastmod": "2024-06-29T14:43:21+00:00",
        "priority": "0.80",
    },
    {
        "loc": "https://www.findsimilarbooks.com/legal",
        "lastmod": "2024-06-29T14:43:21+00:00",
        "priority": "0.80",
    },
    {
        "loc": "https://www.findsimilarbooks.com/impressum",
        "lastmod": "2024-06-29T14:43:21+00:00",
        "priority": "0.80",
    },
]


def write_sitemap(file_num, urls):
    filename = sitemap_dir / Path(f"sitemap_books_{file_num}.xml")
    with open(filename, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for url in urls:
            f.write(
                f'  <url>\n    <loc>{url["loc"]}</loc>\n    <lastmod>{url["lastmod"]}</lastmod>\n    <priority>{url["priority"]}</priority>\n  </url>\n'
            )
        f.write("</urlset>\n")
    logging.info(f"{filename} created!")


if __name__ == "__main__":
    MONGODB_SIMILARBOOKS_URL = os.environ.get("MONGODB_SIMILARBOOKS_URL")
    MONGODB_SIMILARBOOKS_USER = os.environ.get("MONGODB_SIMILARBOOKS_USER")
    MONGODB_SIMILARBOOKS_PWD = os.environ.get("MONGODB_SIMILARBOOKS_PWD")
    MONGODB_SIMILARBOOKS_URI = f"mongodb://{MONGODB_SIMILARBOOKS_USER}:{MONGODB_SIMILARBOOKS_PWD}@{MONGODB_SIMILARBOOKS_URL}:27017/similarbooks?authMechanism=DEFAULT&authSource=similarbooks&tls=true&tlsCAFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.crt&tlsCertificateKeyFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.pem"
    client = MongoClient(MONGODB_SIMILARBOOKS_URI)
    db = client["similarbooks"]
    collection = db["book"]
    pipeline = [
        {"$sample": {"size": 10_000_000}},  # Adjust the size as needed
    ]
    result = collection.aggregate(pipeline)

    # Ensure the sitemap directory exists
    if not os.path.exists(sitemap_dir):
        os.makedirs(sitemap_dir)

    # Iterate over MongoDB result cursor and create sitemaps
    urls = static_urls.copy()  # Start with static URLs
    file_num = 1

    for i, item in enumerate(result):
        sha = item["sha"]  # Extract the book id (sha)
        book_url = {
            "loc": f"{base_url}{sha}",
            "lastmod": "2024-09-30",  # Adjust last modified date
            "priority": "0.70",
        }
        urls.append(book_url)

        # If we have reached the chunk size, write to a new sitemap file
        if len(urls) == chunk_size:
            write_sitemap(file_num, urls)
            file_num += 1
            urls = []  # Reset the list for the next batch

    # Write any remaining URLs that didn't make it into a full chunk
    if urls:
        write_sitemap(file_num, urls)

    # Generate the sitemap index file
    sitemap_index_path = sitemap_dir / Path(f"sitemap_index.xml")
    with open(sitemap_index_path, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')

        for n in range(1, file_num + 1):
            f.write(f"  <sitemap>\n")
            f.write(
                f"    <loc>https://findsimilarbooks.com/sitemap_books_{n}.xml</loc>\n"
            )
            f.write(f"    <lastmod>2024-09-30</lastmod>\n")
            f.write(f"  </sitemap>\n")

        f.write("</sitemapindex>\n")

    logging.info(f"Sitemap index created at {sitemap_index_path}")
