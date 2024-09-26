import os
import argparse
from scrapy.crawler import CrawlerProcess
from bookspider.spiders.gutenberg import GutenbergSpider
from bookspider.spiders.archive import ArchiveSpider
from bookspider.spiders.goodreads import GoodreadsSpider
from bookspider.settings import (
    BOT_NAME,
    USER_AGENT,
    ROBOTSTXT_OBEY,
    DOWNLOAD_DELAY,
    ITEM_PIPELINES,
    MONGODB_DB,
    RANDOMIZE_DOWNLOAD_DELAY,
    DOWNLOADER_MIDDLEWARES,
)


def command_line_arguments():
    """Define and handle command line interface"""
    parser = argparse.ArgumentParser(
        description="Crawl real estate in germany.", prog="bookspider"
    )
    parser.add_argument(
        "--crawler",
        "-c",
        help="Crawler.",
        choices=[
            "goodreads",
            "gutenberg",
            "archive",
        ],
        default="goodreads",
        type=str,
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = command_line_arguments()
    c = CrawlerProcess(
        {
            "BOT_NAME": BOT_NAME,
            "USER_AGENT": USER_AGENT,
            "DOWNLOAD_DELAY": DOWNLOAD_DELAY,
            "RANDOMIZE_DOWNLOAD_DELAY": RANDOMIZE_DOWNLOAD_DELAY,
            "ROBOTSTXT_OBEY": ROBOTSTXT_OBEY,
            "ITEM_PIPELINES": ITEM_PIPELINES,
            "MONGO_DB": MONGODB_DB,
            "DOWNLOADER_MIDDLEWARES": DOWNLOADER_MIDDLEWARES,
            "SCRAPEOPS_API_KEY": os.environ["SCRAPEOPS_API_KEY"],
            # "EXTENSIONS": EXTENSIONS,
        }
    )

    if args.crawler == "gutenberg":
        crawler = GutenbergSpider
    elif args.crawler == "archive":
        crawler = ArchiveSpider
    elif args.crawler == "goodreads":
        crawler = GoodreadsSpider
    else:
        raise Exception("No crawler selected!")

    c.crawl(crawler)
    c.start()
