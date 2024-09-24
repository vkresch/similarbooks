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


class GutenbergSpider(scrapy.Spider):
    name = "gutenberg"
    allowed_domains = ["web", "gutenberg.org"]
    url = "https://www.gutenberg.org/ebooks/{0}"

    def start_requests(self):
        url = self.url.format(1)
        yield Request(url)

    def parse(self, response):
        urls = [f"https://www.gutenberg.org/ebooks/{i}" for i in range(1, 74463)]
        for url in urls:
            yield Request(url, callback=self.parse_item)

    def metadata(self, response, l):
        table_elements = response.xpath("//table[contains(@class, 'bibrec')]/tr")
        for element in table_elements:
            header = element.xpath("th/text()").extract_first()
            if header and "Author" in header:
                author = element.xpath("td/a/text()").extract_first()
                if author:
                    l.add_value("author", fix_string(author))

                author_url = element.xpath("td/a/@href").extract_first()
                if author_url:
                    l.add_value("author_url", f"https://gutenberg.org{author_url}")

            if header and "Title" in header:
                title = element.xpath("td/text()").extract_first()
                if title:
                    l.add_value("title", fix_string(title))

            if header and "Summary" in header:
                summary = element.xpath("td/text()").extract_first()
                if summary:
                    l.add_value("summary", fix_string(summary))

            if header and "Credits" in header:
                credits = element.xpath("td/text()").extract_first()
                if credits:
                    l.add_value("credits", fix_string(credits))

            if header and "Language" in header:
                language = element.xpath("td/text()").extract_first()
                if language:
                    l.add_value("language", fix_string(language))

            if header and "Editor" in header:
                editor = element.xpath("td/text()").extract_first()
                if editor:
                    l.add_value("editor", fix_string(editor))

            if header and "Release Date" in header:
                release = element.xpath("td/text()").extract_first()
                if release:
                    l.add_value(
                        "release", datetime.datetime.strptime(release, "%b %d, %Y")
                    )

        return l

    def housekeeping(self, response, l):
        book_id = response.url.split("/")[-1]
        l.add_value("book_id", f"gb_{book_id}")
        l.add_value("url", f"https://www.gutenberg.org/ebooks/{book_id}")
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
        l = self.metadata(response, l)
        l = self.housekeeping(response, l)
        return l.load_item()
