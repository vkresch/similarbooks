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
from dateutil import parser
import socket
import uuid
import math
import json


def fix_string(value):
    if type(value) == str:
        value = value.replace("\n", "")
        value = value.replace("\t", "")
        value = value.strip()
    return value


class ArchiveSpider(scrapy.Spider):
    name = "archive"
    allowed_domains = ["archive.org"]
    start_urls = [
        "https://archive.org/details/texts"
    ]  # Starting from the Texts collection

    def parse(self, response):
        # Parse the main page for links to individual books
        book_links = response.xpath("//div[@class='item-ttl']/a/@href").extract()
        print("book_list", book_links)
        for book_link in book_links:
            # Extract the book identifier from the URL (last part of the path)
            book_identifier = book_link.split("/")[-1]

            # Use the Archive.org metadata API to get the book's metadata
            metadata_url = f"https://archive.org/metadata/{book_identifier}"
            yield scrapy.Request(metadata_url, callback=self.parse_item)

        # Follow pagination links to the next page of results
        next_page = response.xpath("//a[@title='Next Page']/@href").get()
        if next_page:
            yield response.follow(next_page, self.parse)

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
            l.add_value("author", fix_string(author))

        date_of_publish = metadata.get("date", None)
        if date_of_publish:
            l.add_value("release", datetime.datetime.strptime(date_of_publish, "%Y"))

        description = metadata.get("description", None)
        if description:
            l.add_value("summary", fix_string(description))

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
