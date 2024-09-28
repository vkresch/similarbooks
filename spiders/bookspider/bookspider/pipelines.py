# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import sys
from mongoengine import connect
from mongoengine.connection import disconnect
from bookspider.models import Book

MONGODB_SIMILARBOOKS_URL = os.environ.get("MONGODB_SIMILARBOOKS_URL")
MONGODB_SIMILARBOOKS_USER = os.environ.get("MONGODB_SIMILARBOOKS_USER")
MONGODB_SIMILARBOOKS_PWD = os.environ.get("MONGODB_SIMILARBOOKS_PWD")
MONGODB_SETTINGS = {
    "db": "similarbooks",
    "host": f"mongodb://{MONGODB_SIMILARBOOKS_USER}:{MONGODB_SIMILARBOOKS_PWD}@{MONGODB_SIMILARBOOKS_URL}:27017/similarbooks?authMechanism=DEFAULT&authSource=similarbooks&tls=true&tlsCAFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.crt&tlsCertificateKeyFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.pem",
    "port": 27017,
}


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
            book = Book(**dict(item))
            book.save()
        return item
