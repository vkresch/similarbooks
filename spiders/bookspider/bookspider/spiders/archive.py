# -*- coding: utf-8 -*-
import scrapy
from scrapy.loader import ItemLoader
from bookspider.items import BookItem
from scrapy.http import Request
from itemloaders.processors import TakeFirst
import uuid
import socket
import datetime
import json

# Scraping API endpoint
SCRAPING_API_URL = "https://archive.org/services/search/v1/scrape"


def fix_string(value):
    if isinstance(value, str):
        value = value.replace("\n", "").replace("\t", "").strip()
    return value


class ArchiveSpider(scrapy.Spider):
    name = "archive"
    allowed_domains = ["archive.org"]

    def start_requests(self):
        query = (
            "collection:(texts) AND mediatype:(texts)"  # Adjust this query if needed
        )
        fields = "identifier,title,creator,subject,description,language,year,publisher"  # Fields you want to retrieve
        count = 100  # Number of results per request, you can increase if necessary

        # Initial request without cursor
        yield scrapy.Request(
            url=self.build_scrape_url(query, fields, count),
            callback=self.parse_search_results,
            meta={"query": query, "fields": fields, "count": count, "cursor": None},
        )

    def build_scrape_url(self, query, fields, count, cursor=None):
        """Constructs the API URL for scraping book data."""
        params = {
            "q": query,
            "fields": fields,
            "count": count,
        }
        if cursor:
            params["cursor"] = cursor  # If a cursor exists, add it to the request

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{SCRAPING_API_URL}?{query_string}"

    def parse_search_results(self, response):
        # Parse JSON response from the Scraping API
        data = json.loads(response.text)

        # Check if the response contains items (books)
        if "items" in data:
            books = data["items"]

            # For each book, fetch its metadata using its identifier
            for book in books:
                identifier = book["identifier"]
                metadata_url = f"https://archive.org/metadata/{identifier}"

                # Request the metadata for each book
                yield scrapy.Request(metadata_url, callback=self.parse_item)

        # If a cursor is present in the response, continue the scraping process
        cursor = data.get("cursor")
        if cursor:
            query = response.meta["query"]
            fields = response.meta["fields"]
            count = response.meta["count"]

            # Yield another request to continue scraping with the cursor
            yield scrapy.Request(
                url=self.build_scrape_url(query, fields, count, cursor),
                callback=self.parse_search_results,
                meta={
                    "query": query,
                    "fields": fields,
                    "count": count,
                    "cursor": cursor,
                },
            )

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
        l = ItemLoader(item=BookItem(), response=response)
        l.default_output_processor = TakeFirst()
        l = self.parse_metadata(response, l)
        l = self.housekeeping(response, l)
        return l.load_item()
