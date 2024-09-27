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


# Source: https://en.wikipedia.org/wiki/Goodreads
GOODREADS_BOOK_COUNT = 10_000_000


class GoodreadsSpider(scrapy.Spider):
    name = "goodreads"
    allowed_domains = ["web", "goodreads.com"]
    url = "https://www.goodreads.com/book/show/{0}"

    def start_requests(self):
        url = self.url.format(1)
        yield Request(url)

    def parse(self, response):
        urls = [
            f"https://www.goodreads.com/book/show/{i}"
            for i in range(1, GOODREADS_BOOK_COUNT)
        ]
        for url in urls:
            yield Request(url, callback=self.parse_item)

    def metadata(self, response, l, root):
        work_data = root.get("Work")
        book_data = root.get("Book")
        if work_data is None:
            return
        work_details = work_data.get("details")

        release_ms = work_details.get("publicationTime")
        if release_ms:
            # Convert milliseconds to seconds by dividing by 1000
            l.add_value(
                "release", datetime.datetime.utcfromtimestamp(release_ms / 1000)
            )

        title = work_details.get("originalTitle")
        if title:
            l.add_value("title", title)
        else:
            title = book_data.get("title")
            if title:
                l.add_value("title", title)

        web_url = work_details.get("webUrl")
        if web_url:
            l.add_value("web_url", web_url)

        # Book Stats
        stats = work_data.get("stats")

        average_rating = stats.get("averageRating")
        if average_rating:
            l.add_value("average_rating", average_rating)

        ratings_count = stats.get("ratingsCount")
        if ratings_count:
            l.add_value("ratings_count", ratings_count)

        ratings_count_dist = stats.get("ratingsCountDist")
        if ratings_count_dist:
            rating_one_count = ratings_count_dist[0]
            if rating_one_count:
                l.add_value("rating_one_count", rating_one_count)

            rating_two_count = ratings_count_dist[1]
            if rating_two_count:
                l.add_value("rating_two_count", rating_two_count)

            rating_three_count = ratings_count_dist[2]
            if rating_three_count:
                l.add_value("rating_three_count", rating_three_count)

            rating_four_count = ratings_count_dist[3]
            if rating_one_count:
                l.add_value("rating_one_count", rating_one_count)

            rating_five_count = ratings_count_dist[4]
            if rating_five_count:
                l.add_value("rating_five_count", rating_five_count)

        text_reviews_count = stats.get("textReviewsCount")
        if text_reviews_count:
            l.add_value("text_reviews_count", text_reviews_count)

        # General Book Info
        summary = book_data.get("description")
        if summary:
            l.add_value("summary", summary)

        image_url = book_data.get("imageUrl")
        if image_url:
            l.add_value("image_url", image_url)

        book_series = book_data.get("bookSeries")
        if book_series and len(book_series) > 0:
            l.add_value("is_series", True)

            series_position = book_series[0].get("userPosition")
            if series_position:
                l.add_value("series_position", series_position)

        is_series = book_data.get("imageUrl")
        if is_series:
            l.add_value("is_series", is_series)

        genres = book_data.get("bookGenres")
        if len(genres) > 0:
            processed_genres = [genre.get("genre").get("webUrl") for genre in genres]
            l.add_value("genres", processed_genres)

        # Book Details
        details = book_data.get("details")
        num_pages = details.get("numPages")
        if num_pages:
            l.add_value("num_pages", int(num_pages))

        editor = details.get("publisher")
        if editor:
            l.add_value("editor", editor)

        language = details.get("language")
        if language:
            l.add_value("language", language.get("name"))

        book_format = details.get("format")
        if book_format:
            l.add_value("format", book_format)

        # Author Data
        contributor_key = (
            book_data.get("primaryContributorEdge").get("node").get("__ref")
        )
        author_data = root.get(contributor_key)
        author = author_data.get("name")
        if author:
            l.add_value("author", author)

        author_description = author_data.get("description")
        if author_description:
            l.add_value("author_description", author_description)

        author_url = author_data.get("webUrl")
        if author_url:
            l.add_value("author_url", author_url)

        author_image_url = author_data.get("profileImageUrl")
        if author_image_url:
            l.add_value("author_image_url", author_image_url)

        author_followers = author_data.get("followers")
        if author_followers:
            l.add_value(
                "author_follower_count", int(author_followers.get("totalCount"))
            )

        is_gr_author = author_data.get("isGrAuthor")
        if is_gr_author:
            l.add_value("is_gr_author", bool(is_gr_author))

        # Book Links
        links = book_data.get("links({})")
        primary_affiliate_link = links.get("primaryAffiliateLink")
        if primary_affiliate_link:
            kindle_link = primary_affiliate_link.get("url")
            if kindle_link:
                if primary_affiliate_link.get("__typename") == "KindleLink":
                    l.add_value("kindle_link", kindle_link)
                else:
                    if primary_affiliate_link.get("name") == "Amazon":
                        l.add_value("amazon_link", kindle_link)

        secondary_affiliate_links = links.get("secondaryAffiliateLinks")
        if len(secondary_affiliate_links) > 0:
            for link in secondary_affiliate_links:
                if link.get("name") == "Amazon":
                    l.add_value("amazon_link", link.get("url"))
                elif link.get("name") == "Audible":
                    l.add_value("audible_link", link.get("url"))
                elif link.get("name") == "Barnes & Noble":
                    l.add_value("barnes_and_noble_link", link.get("url"))
                elif link.get("name") == "AbeBooks":
                    l.add_value("abe_books_link", link.get("url"))
                elif link.get("name") == "Kobo":
                    l.add_value("kobo_link", link.get("url"))
                elif link.get("name") == "Google Play":
                    l.add_value("google_play_link", link.get("url"))
                elif link.get("name") == "Alibris":
                    l.add_value("alibris_link", link.get("url"))
                elif link.get("name") == "Indigo":
                    l.add_value("indigo_link", link.get("url"))
                elif link.get("name") == "Better World Books":
                    l.add_value("better_world_books_link", link.get("url"))
                elif link.get("name") == "IndieBound":
                    l.add_value("indie_bounds_link", link.get("url"))
                elif link.get("name") == "Thriftbooks":
                    l.add_value("thrift_books_link", link.get("url"))
        return l

    def housekeeping(self, response, l):
        book_id = response.url.split("/")[-1]
        l.add_value("book_id", f"gr_{book_id}")
        l.add_value("url", f"https://www.goodreads.com/book/show/{book_id}")
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
        json_text = response.xpath("//*[@id='__NEXT_DATA__']/text()").get()
        json_text_cleaned = re.sub(r'(?<!Contributor)(:kca://[^"]+)', "", json_text)
        data = json.loads(json_text_cleaned)
        root = data.get("props").get("pageProps").get("apolloState")
        if root is None:
            self.logger.info(f"Skipping {response.url} due to 404 status")
            return  # Skips the site without failing

        l = self.metadata(response, l, root)

        if l is None:
            return

        l = self.housekeeping(response, l)
        return l.load_item()
