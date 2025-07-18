import json
from typing import Any, Optional
import time
from src.backend.kr8.tools import Toolkit
from src.backend.kr8.utils.log import logger

try:
    from duckduckgo_search import DDGS
except ImportError:
    raise ImportError("`duckduckgo-search` not installed. Please install using `pip install duckduckgo-search`")


class DuckDuckGo(Toolkit):
    def __init__(
        self,
        search: bool = True,
        news: bool = True,
        fixed_max_results: Optional[int] = None,
        headers: Optional[Any] = None,
        proxy: Optional[str] = None,
        proxies: Optional[Any] = None,
        timeout: Optional[int] = 10,
    ):
        super().__init__(name="duckduckgo")
        
        self.last_search_time = 0
        self.min_search_interval = 5
        self.headers: Optional[Any] = headers
        self.proxy: Optional[str] = proxy
        self.proxies: Optional[Any] = proxies
        self.timeout: Optional[int] = timeout
        self.fixed_max_results: Optional[int] = fixed_max_results
        if search:
            self.register(self.duckduckgo_search)
        if news:
            self.register(self.duckduckgo_news)

    def rate_limited_search(func):
        def wrapper(self, *args, **kwargs):
            current_time = time.time()
            if current_time - self.last_search_time < self.min_search_interval:
                time.sleep(self.min_search_interval - (current_time - self.last_search_time))
            self.last_search_time = time.time()
            return func(self, *args, **kwargs)
        return wrapper
    @rate_limited_search
    def duckduckgo_search(self, query: str, max_results: int = 5) -> str:
        """Use this function to search DuckDuckGo for a query.

        Args:
            query(str): The query to search for.
            max_results (optional, default=5): The maximum number of results to return.

        Returns:
            The result from DuckDuckGo.
        """
        logger.debug(f"Searching DDG for: {query}")
        ddgs = DDGS(headers=self.headers, proxy=self.proxy, proxies=self.proxies, timeout=self.timeout)
        return json.dumps(ddgs.text(keywords=query, max_results=(self.fixed_max_results or max_results)), indent=2)

    @rate_limited_search
    def duckduckgo_news(self, query: str, max_results: int = 5) -> str:
        logger.debug(f"Starting DDG news search for: {query}")
        ddgs = DDGS(headers=self.headers, proxy=self.proxy, proxies=self.proxies, timeout=self.timeout)
        results = ddgs.news(keywords=query, max_results=(self.fixed_max_results or max_results))
        logger.debug(f"Completed DDG news search for: {query}. Got {len(results)} results.")
        return json.dumps(results, indent=2)
