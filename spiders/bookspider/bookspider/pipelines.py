# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import sys
import pymongo
import numpy as np
from mongoengine import connect
import time
from pathlib import Path
import requests
from PIL import Image
from io import BytesIO
from mongoengine.connection import disconnect
from bookspider.models import Book
from som.utils import model_dict, get_top_bmus
from app.similarbooks.main.constants import (
    MIN_SUMMARY_LENGTH,
)

MONGODB_SIMILARBOOKS_URL = os.environ.get("MONGODB_SIMILARBOOKS_URL")
MONGODB_SIMILARBOOKS_USER = os.environ.get("MONGODB_SIMILARBOOKS_USER")
MONGODB_SIMILARBOOKS_PWD = os.environ.get("MONGODB_SIMILARBOOKS_PWD")
MONGODB_SETTINGS = {
    "db": "similarbooks",
    "host": f"mongodb://{MONGODB_SIMILARBOOKS_USER}:{MONGODB_SIMILARBOOKS_PWD}@{MONGODB_SIMILARBOOKS_URL}:27017/similarbooks?authMechanism=DEFAULT&authSource=similarbooks&tls=true&tlsCAFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.crt&tlsCertificateKeyFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.pem",
    "port": 27017,
}

PARENT_DIR = Path(__file__).resolve().parent

# Connect to the MongoDB server
CLIENT = pymongo.MongoClient(MONGODB_SETTINGS["host"])

# Get the appartment database and the appartment collection
DB = CLIENT["similarbooks"]

LDA_WEBSOM_COLLECTION = DB["lda_websom"]


def download_book_cover(spider, sha, url, retries=3, timeout=10, max_width=200):
    savedir = PARENT_DIR / Path(f"../../../app/similarbooks/static/covers/{sha}.png")

    if os.path.exists(savedir):
        spider.logger.info(f"Image {sha} already exists!")
        return True

    for attempt in range(retries):
        try:
            # Send an HTTP request to the URL
            response = requests.get(url)

            # Check if the request was successful (status code 200)
            if response.status_code == 200:
                # Read the image data from the response content
                img_data = response.content

                # Use BytesIO to open the image data as a PIL image
                img = Image.open(BytesIO(img_data))

                # Check if the image is in CMYK mode and convert it to RGB
                if img.mode == "CMYK":
                    img = img.convert("RGB")
                    spider.logger.info(f"Image {sha} converted from CMYK to RGB.")

                # Resize the image to a maximum width of 200px while maintaining aspect ratio
                width_percent = max_width / float(img.size[0])
                new_height = int((float(img.size[1]) * float(width_percent)))
                img = img.resize((max_width, new_height), Image.LANCZOS)

                # Save the image locally
                img.save(savedir, optimize=True, quality=85)
                spider.logger.info(f"Image {sha} downloaded and saved successfully!")
                time.sleep(1)
                return True  # Download succeeded, exit the loop
            else:
                spider.logger.error(
                    f"Failed to download image {sha}. Status code: {response.status_code}"
                )

        except requests.exceptions.ConnectionError as e:
            spider.logger.error(
                f"Connection error: {e}. Retrying ({attempt + 1}/{retries})..."
            )
            time.sleep(2)  # Wait before retrying
        except requests.exceptions.Timeout:
            spider.logger.error(
                f"Request timed out. Retrying ({attempt + 1}/{retries})..."
            )
            time.sleep(2)  # Wait before retrying

    spider.logger.error(f"Failed to download the image {sha} after multiple attempts.")
    return False


def add_book_bmu(spider, item):
    text = (item.get("title") or "") + " " + (item.get("summary") or "")
    sha = item["sha"]
    if len(text) < MIN_SUMMARY_LENGTH:
        return item
    tasks_vectorized = model_dict["vectorizer"].transform([text])
    tasks_topic_dist = model_dict["lda"].transform(tasks_vectorized)[0]
    active_map = model_dict.get("lda_websom").get_surface_state(
        data=np.array([tasks_topic_dist])
    )
    bmu_node = get_top_bmus(model_dict.get("lda_websom"), active_map, top_n=1)

    item["bmu_col"] = int(bmu_node[0][0])
    item["bmu_row"] = int(bmu_node[0][1])

    bmu_update = {"bmu_col": item["bmu_col"], "bmu_row": item["bmu_row"]}

    matched_documents = LDA_WEBSOM_COLLECTION.find(bmu_update)
    matched_list = [sha]
    for doc in matched_documents:
        matched_list.extend(doc["matched_list"])

    LDA_WEBSOM_COLLECTION.update_one(
        bmu_update, {"$set": {"matched_list": matched_list}}
    )
    spider.logger.info(f"Appended new book {sha} to bmu node {bmu_update} in websom")

    return item


class BookspiderMongoDBPipeline:
    def __init__(self, mongo_db):
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(mongo_db=crawler.settings.get("MONGO_DB", "items"))

    def open_spider(self, spider):
        self.db = connect(**MONGODB_SETTINGS)

    def close_spider(self, spider):
        self.db.close()
        disconnect(self.mongo_db)

    def process_item(self, item, spider):
        image_url = item.get("image_url")
        if image_url:
            download_book_cover(spider, item["sha"], image_url)
        existing_item = Book.objects(book_id=item["book_id"]).first()
        if existing_item:
            # Do not save again if it exists already
            spider.logger.info(
                f"Book with id {item['book_id']} already saved into the database!"
            )
            if hasattr(spider, "start_urls"):
                for key, value in item.items():
                    setattr(existing_item, key, value)
                spider.logger.info(f"Book with id {item['book_id']} overridden!")
                existing_item.save()
        else:
            item = add_book_bmu(spider, item)  # Add only new bmu to new books parsed
            book = Book(**dict(item))
            book.save()
        return item
