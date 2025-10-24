from dataclasses import dataclass, field
from typing import Optional
from xml.etree import ElementTree
import time, random

import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException
from lxml import etree
from requests import Response, TooManyRedirects

from app.utils.utils import trim
from app.utils.xpath import Pagination


@dataclass
class TransfermarktBase:
    """
    Base class for making HTTP requests to Transfermarkt and extracting data from the web pages.
    """

    URL: str
    page: ElementTree = field(default_factory=lambda: None, init=False)
    response: dict = field(default_factory=lambda: {}, init=False)

    def make_request(self, url: Optional[str] = None) -> Response:
        """
        Make an HTTP GET request to the specified URL.
        Includes a small random delay to avoid triggering Transfermarkt rate limits.
        """
        url = self.URL if not url else url
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/15.5 Safari/605.1.15"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Connection": "keep-alive"
            }

            # 🕒 Smart rate-limiting delay (prevents 403 Forbidden)
            time.sleep(random.uniform(1.5, 3.0))

            response: Response = requests.get(url=url, headers=headers, timeout=15)

        except TooManyRedirects:
            raise HTTPException(status_code=404, detail=f"Not found for url: {url}")
        except ConnectionError:
            raise HTTPException(status_code=500, detail=f"Connection error for url: {url}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error for url: {url}. {e}")

        if 400 <= response.status_code < 500:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Client Error. {response.reason} for url: {url}",
            )
        elif 500 <= response.status_code < 600:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Server Error. {response.reason} for url: {url}",
            )
        return response

    def request_url_bsoup(self) -> BeautifulSoup:
        """
        Fetch the web page content and parse it using BeautifulSoup.
        """
        response: Response = self.make_request()
        return BeautifulSoup(markup=response.content, features="html.parser")

    @staticmethod
    def convert_bsoup_to_page(bsoup: BeautifulSoup) -> ElementTree:
        """
        Convert a BeautifulSoup object to an ElementTree.
        """
        return etree.HTML(str(bsoup))

    def request_url_page(self) -> ElementTree:
        """
        Fetch and parse the web page, returning an ElementTree.
        """
        bsoup: BeautifulSoup = self.request_url_bsoup()
        return self.convert_bsoup_to_page(bsoup=bsoup)

    def raise_exception_if_not_found(self, xpath: str):
        """
        Raise an exception if a given XPath yields no results.
        """
        if not self.get_text_by_xpath(xpath):
            raise HTTPException(status_code=404, detail=f"Invalid request (url: {self.URL})")

    def get_list_by_xpath(self, xpath: str, remove_empty: Optional[bool] = True) -> Optional[list]:
        """
        Extracts a list of elements by XPath.
        """
        elements: list = self.page.xpath(xpath)
        if remove_empty:
            elements_valid: list = [trim(e) for e in elements if trim(e)]
        else:
            elements_valid: list = [trim(e) for e in elements]
        return elements_valid or []

    def get_text_by_xpath(
        self,
        xpath: str,
        pos: int = 0,
        iloc: Optional[int] = None,
        iloc_from: Optional[int] = None,
        iloc_to: Optional[int] = None,
        join_str: Optional[str] = None,
    ) -> Optional[str]:
        """
        Extracts text content from the web page using XPath.
        """
        element = self.page.xpath(xpath)

        if not element:
            return None

        if isinstance(element, list):
            element = [trim(e) for e in element if trim(e)]

        if isinstance(iloc, int):
            element = element[iloc]

        if isinstance(iloc_from, int) and isinstance(iloc_to, int):
            element = element[iloc_from:iloc_to]

        if isinstance(iloc_to, int):
            element = element[:iloc_to]

        if isinstance(iloc_from, int):
            element = element[iloc_from:]

        if isinstance(join_str, str):
            return join_str.join([trim(e) for e in element])

        try:
            return trim(element[pos])
        except IndexError:
            return None

    def get_last_page_number(self, xpath_base: str = "") -> int:
        """
        Retrieve the last page number for a paginated result based on the provided base XPath.
        """
        for xpath in [Pagination.PAGE_NUMBER_LAST, Pagination.PAGE_NUMBER_ACTIVE]:
            url_page = self.get_text_by_xpath(xpath_base + xpath)
            if url_page:
                return int(url_page.split("=")[-1].split("/")[-1])
        return 1
