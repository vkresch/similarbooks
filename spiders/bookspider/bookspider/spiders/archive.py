# -*- coding: utf-8 -*-
import scrapy
from scrapy.loader import ItemLoader
from bookspider.items import (
    BookItem,
)
from scrapy.http import Request
from itemloaders.processors import MapCompose, TakeFirst, Join

from w3lib.html import replace_escape_chars
import numpy as np
import re
import datetime
import time
from dateutil import parser
import socket
import uuid
import math
import json

# Constants
BASE_API_URL = "https://archive.org/advancedsearch.php"


def fix_string(value):
    if type(value) == str:
        value = value.replace("\n", "")
        value = value.replace("\t", "")
        value = value.strip()
    return value


class ArchiveSpider(scrapy.Spider):
    name = "archive"
    allowed_domains = ["archive.org"]

    def start_requests(self):
        # Specify the page range (you can adjust this to suit your needs)
        min_page = 1
        max_page = 1_000_000

        # Loop through pages and yield API requests for each page
        for page in range(min_page, max_page + 1):
            yield scrapy.Request(
                url=self.build_search_url(page),
                callback=self.parse_search_results,
                meta={"page": page},
            )

    def build_search_url(self, page):
        """Constructs the API URL for querying book data."""
        query_params = {
            "q": "collection:(texts) AND mediatype:(texts)",  # Search query for texts
            "fl[]": "identifier,title",  # Fields to retrieve
            "rows": 50,  # Number of results per page
            "page": page,  # Page number
            "output": "json",  # JSON output
        }
        query_string = "&".join(f"{k}={v}" for k, v in query_params.items())
        return f"{BASE_API_URL}?{query_string}"

    def parse_search_results(self, response):
        # Parse JSON response from the search API
        data = json.loads(response.text)

        # Check if the response contains books
        if "response" in data and "docs" in data["response"]:
            books = data["response"]["docs"]

            # For each book, fetch its metadata using its identifier
            for book in books:
                identifier = book["identifier"]
                metadata_url = f"https://archive.org/metadata/{identifier}"

                # Request the metadata for each book
                yield scrapy.Request(metadata_url, callback=self.parse_item)

    def parse_metadata(self, response, l):
        # Parse the JSON response from the metadata API
        metadata_json = json.loads(response.body)
        metadata = metadata_json.get("metadata", {})

        book_id = metadata.get("identifier", None)
        if book_id:
            l.add_value("book_id", fix_string(book_id))
            l.add_value("url", f"http://archive.org/details/{book_id}")

        # Extract relevant fields from the JSON
        title = metadata.get("title", None)
        if title:
            l.add_value("title", fix_string(title))

        author = metadata.get("creator", None)
        if author:
            if isinstance(author, list):
                author = " ".join(author)
            l.add_value("author", fix_string(author))

        date_of_publish = metadata.get("date", None)
        if date_of_publish:
            processed_date = date_of_publish
            if len(date_of_publish) == 4:
                processed_date = datetime.datetime.strptime(date_of_publish, "%Y")
            elif len(date_of_publish) > 4:
                processed_date = datetime.datetime.strptime(date_of_publish[-4:], "%Y")
            l.add_value("release", processed_date)

        description = metadata.get("description", None)
        if description:
            if isinstance(description, list):
                description = " ".join(description)
            l.add_value("summary", fix_string(description))

        subject = metadata.get("subject", None)
        if subject:
            if isinstance(subject, list):
                subject = " ".join(subject)
            l.add_value("subject", fix_string(subject))

        language = metadata.get("language", None)
        if language:
            l.add_value("language", fix_string(language))

        isbn_10 = metadata.get("isbn", None)
        if isbn_10:
            l.add_value("isbn_10", fix_string(isbn_10))

        editor = metadata.get("publisher", None)
        if editor:
            l.add_value("editor", fix_string(editor))
        return l

    def housekeeping(self, response, l):
        l.add_value("sha", uuid.uuid4().hex)
        l.add_value("project", self.settings.get("BOT_NAME"))
        l.add_value("spider", self.name)
        l.add_value("server", socket.gethostname())
        l.add_value("date", datetime.datetime.now())
        return l

    def parse_item(self, response):
        self.log("Visited %s" % response.url)
        # TODO: Make this argument dependent
        l = ItemLoader(item=BookItem(), response=response)
        l.default_output_processor = TakeFirst()
        l = self.parse_metadata(response, l)
        l = self.housekeeping(response, l)
        return l.load_item()
