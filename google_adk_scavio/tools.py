"""Scavio search and page-extraction tools for Google ADK (Agent Development Kit).

Build the tools with `create_scavio_tools()` and pass them to an ADK Agent:

    from google.adk.agents import Agent
    from google_adk_scavio import create_scavio_tools

    agent = Agent(name="search_assistant", model="gemini-2.5-flash", tools=create_scavio_tools())

The factory returns plain Python functions with typed parameters and docstrings;
ADK wraps each one in a FunctionTool automatically. Each provider is gated by an
``enable_*`` flag. Tools return the Scavio JSON response as a dict.

``enable_crawl=True`` adds the website tools of the Extract family: map a
site's URLs, crawl a site, batch-extract a URL list, and read a crawl or batch
job. Crawl and batch are background jobs: the start tools post the job, wait up
to ``wait_seconds`` for it to finish, and return its status with the first page
of results either way. A job still running when the wait ends keeps going.
"""

import os
import time
from typing import Any, Callable, Dict, List, Optional

try:
    from scavio import ScavioClient
except ImportError as exc:  # pragma: no cover
    raise ImportError("`scavio` not installed. Please install using `pip install scavio`") from exc


def _run(call: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    """Run a Scavio SDK call, returning its JSON dict or an {"error": ...} dict."""
    try:
        return call()
    except Exception as exc:  # noqa: BLE001 - surface errors to the agent
        return {"error": str(exc)}


WEB_JOB_POLL_INTERVAL = 3.0
WEB_JOB_MAX_WAIT = 300
_WEB_JOB_TERMINAL = frozenset({"completed", "failed", "cancelled"})


def _without_none(values: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in values.items() if v is not None}


def _wait_for_job(status: Callable[..., Dict[str, Any]], job_id: str, wait_seconds: float, query: Dict[str, Any]) -> Dict[str, Any]:
    """Poll a job until it finishes or the wait runs out; progress polls skip content."""
    deadline = time.monotonic() + max(0.0, min(float(wait_seconds), WEB_JOB_MAX_WAIT))
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(WEB_JOB_POLL_INTERVAL, remaining))
        probe = status(job_id, limit=1, include_content=False)
        if (probe.get("data") or {}).get("status") in _WEB_JOB_TERMINAL:
            break
    return status(job_id, **query)


def _start_job(start: Callable[..., Dict[str, Any]], status: Callable[..., Dict[str, Any]], first: Any, body: Dict[str, Any], wait_seconds: Optional[int], query: Dict[str, Any]) -> Dict[str, Any]:
    """Start a crawl/batch job, then wait (bounded) and return its status page."""
    created = start(first, **_without_none(body))
    job_id = (created.get("data") or {}).get("id") if isinstance(created, dict) else None
    wait = 45 if wait_seconds is None else wait_seconds
    if not job_id or wait <= 0:
        return created
    return _wait_for_job(status, job_id, wait, _without_none(query))


def create_scavio_tools(
    api_key: Optional[str] = None,
    *,
    enable_extract: bool = True,
    enable_google: bool = True,
    enable_youtube: bool = True,
    enable_amazon: bool = True,
    enable_walmart: bool = True,
    enable_reddit: bool = True,
    enable_crawl: bool = False,
) -> list:
    """Build Scavio search tools for a Google ADK Agent.

    Args:
        api_key: Scavio API key. Falls back to the SCAVIO_API_KEY env var.
        enable_extract: Register the read-any-URL tool. Defaults to True. Unlike
            the flags below it gates no platform: ``extract`` is a core endpoint
            that works on any URL.
        enable_google: Register the Google tools. Defaults to True.
        enable_youtube: Register the YouTube tools. Defaults to True.
        enable_amazon: Register the Amazon tools. Defaults to True.
        enable_walmart: Register the Walmart tools. Defaults to True.
        enable_reddit: Register the Reddit tools. Defaults to True.
        enable_crawl: Register the 5 website tools (map, crawl, crawl status,
            batch extract, batch status). OPT-IN, defaults to False, because a
            crawl bills per page.

    Returns:
        A list of plain functions ready to pass as ``tools=`` to an ADK Agent.
    """
    client = ScavioClient(api_key=api_key or os.getenv("SCAVIO_API_KEY"))
    tools: list = []

    if enable_extract:
        # Registered first on purpose: extract is the read-this-page primitive an
        # agent reaches for most, and the only tool here tied to no platform.
        # `extract` is a TOP-LEVEL method on the client, never a namespace --
        # client.extract(url), not client.extract.extract().
        def scavio_extract(url: str, format: Optional[str] = None, mode: Optional[str] = None) -> dict:
            """Read any web page and return it as clean Markdown, plain text, or raw HTML. Costs 1 credit on normal and advanced, 2 on ultra, and only a successful read is billed.

            Args:
                url: The page to read (1-2048 characters). http(s) only; a bare host is upgraded to https, and loopback, private, link-local and metadata hosts are rejected.
                format: Output format: markdown (the default) is a readability extraction with the page chrome stripped, text is that flattened to plain text, html is the raw page.
                mode: Fetch tier, and the parameter that sets the price: normal (the default) is the standard fetch and costs 1 credit, advanced renders JavaScript-built pages and costs 1, ultra reaches the hardest pages and costs 2. Start on normal.
            """
            _p = {"format": format, "mode": mode}
            return _run(lambda: client.extract(url, **{k: v for k, v in _p.items() if v is not None}))
        tools.append(scavio_extract)

    if enable_google:
        def scavio_google_search(query: str, gl: Optional[str] = None, hl: Optional[str] = None) -> dict:
            """Search Google for real-time web results (organic results, knowledge graph, AI overview). Costs 1 credit.

            Args:
                query: The search query.
                gl: Two-letter ISO country code for the search, e.g. us.
                hl: Two-letter language code for the results, e.g. en.
            """
            _p = {"gl": gl, "hl": hl}
            return _run(lambda: client.google.search(query, **{k: v for k, v in _p.items() if v is not None}))
        tools.append(scavio_google_search)

        def scavio_google_news(query: str, gl: Optional[str] = None, hl: Optional[str] = None) -> dict:
            """Search Google News for current news articles on a topic. Costs 1 credit.

            Args:
                query: The news search query.
                gl: Two-letter ISO country code for the search, e.g. us.
                hl: Two-letter language code for the results, e.g. en.
            """
            _p = {"query": query, "gl": gl, "hl": hl}
            return _run(lambda: client.google.news(**{k: v for k, v in _p.items() if v is not None}))
        tools.append(scavio_google_news)

    if enable_youtube:
        def scavio_youtube_search(query: str, upload_date: Optional[str] = None, type: Optional[str] = None, duration: Optional[str] = None, sort_by: Optional[str] = None, cursor: Optional[str] = None) -> dict:
            """Search YouTube for videos, channels, or playlists. Costs 2 credits.

            Args:
                query: The video search query.
                upload_date: Upload date filter: last_hour, today, this_week, this_month, this_year.
                type: Result type: video, channel, playlist, movie.
                duration: Duration filter: short, medium, long.
                sort_by: Sort order: relevance, date, view_count, rating.
                cursor: Pagination cursor from a previous response.
            """
            _p = {"upload_date": upload_date, "type": type, "duration": duration, "sort_by": sort_by, "cursor": cursor}
            return _run(lambda: client.youtube.search(query, **{k: v for k, v in _p.items() if v is not None}))
        tools.append(scavio_youtube_search)

        def scavio_youtube_video(video_id: str) -> dict:
            """Fetch full metadata for a YouTube video by id or watch URL. Costs 1 credit.

            Args:
                video_id: YouTube video id or full watch URL, e.g. dQw4w9WgXcQ.
            """
            return _run(lambda: client.youtube.video(video_id))
        tools.append(scavio_youtube_video)

        # /youtube/metadata is a deprecated alias of /youtube/video; it is not
        # registered as a peer tool so a model never has to pick between two
        # identical endpoints. Call client.youtube.metadata() directly if needed.

        def scavio_youtube_comments(video_id: str, cursor: Optional[str] = None) -> dict:
            """List the top-level comments on a YouTube video. Costs 1 credit.

            Args:
                video_id: YouTube video id.
                cursor: Pagination cursor from a previous response.
            """
            _p = {"cursor": cursor}
            return _run(lambda: client.youtube.comments(video_id, **{k: v for k, v in _p.items() if v is not None}))
        tools.append(scavio_youtube_comments)

        def scavio_youtube_channel(channel_id: str) -> dict:
            """Fetch details for a YouTube channel by id, @handle, or URL. Costs 1 credit.

            Args:
                channel_id: YouTube channel id, @handle, or channel URL.
            """
            return _run(lambda: client.youtube.channel(channel_id))
        tools.append(scavio_youtube_channel)

        def scavio_youtube_transcript(video_id: str, language: Optional[str] = None, format: Optional[str] = None) -> dict:
            """Fetch the transcript or timed subtitles for a YouTube video. Costs 8 credits.

            Args:
                video_id: YouTube video id.
                language: Caption language code (default en).
                format: text for a plain transcript or srt for timed subtitles.
            """
            _p = {"language": language, "format": format}
            return _run(lambda: client.youtube.transcript(video_id, **{k: v for k, v in _p.items() if v is not None}))
        tools.append(scavio_youtube_transcript)

        def scavio_youtube_streams(video_id: str) -> dict:
            """Get playable and downloadable stream formats for a YouTube video. Costs 3 credits.

            Args:
                video_id: YouTube video id.
            """
            return _run(lambda: client.youtube.streams(video_id))
        tools.append(scavio_youtube_streams)

    if enable_amazon:
        # Amazon moved upstream in 2026-07. sort_by is a verified no-op (every
        # sort value returns the identical unordered set) and start_page was
        # renamed to page, so both are gone rather than kept as dead params.
        # domain still works on the wire as a deprecated alias but is not
        # offered here: a model should see one spelling of a param.
        def scavio_amazon_search(query: str, country: Optional[str] = None, page: Optional[int] = None) -> dict:
            """Search Amazon for products matching a query. Costs 1 credit. Results are unsorted and cannot be filtered.

            Args:
                query: The product search query.
                country: Marketplace country code (ISO 3166-1 alpha-2), not a domain: us (default), gb (the UK is gb, not uk), ca, de, fr, es, it, jp, in, au, br, mx, nl, pl, se, sg, ae, sa, eg, cn, be, tr. An unknown code falls back to us.
                page: Result page, 1-based. One page per call, 1 credit each.
            """
            _p = {"country": country, "page": page}
            return _run(lambda: client.amazon.search(query, **{k: v for k, v in _p.items() if v is not None}))
        tools.append(scavio_amazon_search)

        def scavio_amazon_product(asin: str, country: Optional[str] = None) -> dict:
            """Fetch full Amazon product details by ASIN. Costs 1 credit. price is the buy-box price only.

            Args:
                asin: Amazon Standard Identification Number, e.g. B09XS7JWHH.
                country: Marketplace country code (ISO 3166-1 alpha-2), not a domain: us (default), gb (the UK is gb, not uk), ca, de, fr, es, it, jp, in, au, br, mx, nl, pl, se, sg, ae, sa, eg, cn, be, tr. An unknown code falls back to us.
            """
            _p = {"country": country}
            return _run(lambda: client.amazon.product(asin, **{k: v for k, v in _p.items() if v is not None}))
        tools.append(scavio_amazon_product)

        def scavio_amazon_offers(asin: str, country: Optional[str] = None) -> dict:
            """List every seller offer for an Amazon ASIN: price, seller, condition, shipping, buy box. Costs 1 credit. Page 1 only.

            Args:
                asin: Amazon Standard Identification Number, e.g. B09XS7JWHH.
                country: Marketplace country code (ISO 3166-1 alpha-2), not a domain: us (default), gb (the UK is gb, not uk), ca, de, fr, es, it, jp, in, au, br, mx, nl, pl, se, sg, ae, sa, eg, cn, be, tr. An unknown code falls back to us.
            """
            _p = {"country": country}
            return _run(lambda: client.amazon.offers(asin, **{k: v for k, v in _p.items() if v is not None}))
        tools.append(scavio_amazon_offers)

    if enable_walmart:
        def scavio_walmart_search(query: str, sort_by: Optional[str] = None, min_price: Optional[int] = None, max_price: Optional[int] = None, start_page: Optional[int] = None) -> dict:
            """Search Walmart for products matching a query. Costs 1 credit.

            Args:
                query: The product search query.
                sort_by: Sort order: best_match, price_low, price_high, best_seller.
                min_price: Minimum price filter in USD.
                max_price: Maximum price filter in USD.
                start_page: First result page to return (1-based).
            """
            _p = {"sort_by": sort_by, "min_price": min_price, "max_price": max_price, "start_page": start_page}
            return _run(lambda: client.walmart.search(query, **{k: v for k, v in _p.items() if v is not None}))
        tools.append(scavio_walmart_search)

        def scavio_walmart_product(product_id: str) -> dict:
            """Fetch full Walmart product details by product id. Costs 1 credit.

            Args:
                product_id: Walmart product id.
            """
            return _run(lambda: client.walmart.product(product_id))
        tools.append(scavio_walmart_product)

    if enable_reddit:
        # Reddit moved upstream in 2026-07: 1 credit, not 2. /reddit/search
        # takes query + cursor only. type and sort never reached the provider,
        # so a model that set them believed it had filtered when it had not;
        # they are removed rather than kept as silent no-ops.
        def scavio_reddit_search(query: str, cursor: Optional[str] = None) -> dict:
            """Search Reddit posts. Costs 1 credit. Results are relevance-ordered and cannot be sorted or filtered by type.

            Args:
                query: The Reddit search query.
                cursor: Pagination cursor: the next_cursor of a previous response.
            """
            _p = {"cursor": cursor}
            return _run(lambda: client.reddit.search(query, **{k: v for k, v in _p.items() if v is not None}))
        tools.append(scavio_reddit_search)

        def scavio_reddit_post(url: str) -> dict:
            """Fetch a single Reddit post by URL as a flat post object. Costs 1 credit. Returns no comments: use the Reddit comments endpoints for those.

            Args:
                url: Full URL of the Reddit post.
            """
            return _run(lambda: client.reddit.post(url))
        tools.append(scavio_reddit_post)

    if enable_crawl:
        # Map, crawl and batch hang off the callable client.extract namespace
        # (scavio>=0.23.0): client.extract.map / .crawl / .crawl_status /
        # .batch / .batch_status. Cancellation, webhooks and idempotency keys
        # stay on the SDK and REST API, not on agent tools.
        def scavio_map_website(url: str, search: Optional[str] = None, limit: Optional[int] = None, sitemap: Optional[str] = None, include_subdomains: Optional[bool] = None, include_paths: Optional[List[str]] = None, exclude_paths: Optional[List[str]] = None, mode: Optional[str] = None) -> dict:
            """List a website's page URLs from its sitemaps and start page, deduplicated, filtered by path or search words and limited. Pages the site's robots.txt disallows are left out. Use it to find the right pages before extracting or crawling. Costs 1 credit on normal; advanced costs up to 2 and ultra up to 10, priced by what the call needed.

            Args:
                url: The site to map. A bare host is upgraded to https.
                search: Only return URLs containing every word of this text (case-insensitive).
                limit: Maximum links to return, 1-5000. Server default 1000 (or the plan's limit if lower).
                sitemap: include (the default) combines the sitemaps with the start page's links, only uses sitemaps alone, skip uses page links alone.
                include_subdomains: Also return URLs on subdomains of the site. Default false.
                include_paths: Keep only URLs matching these path globs (max 20), e.g. ["/blog/**"].
                exclude_paths: Drop URLs matching these path globs (max 20).
                mode: normal (the default) is the standard fetch, advanced renders JavaScript-built pages, ultra reaches the hardest pages.
            """
            _p = {"search": search, "limit": limit, "sitemap": sitemap, "include_subdomains": include_subdomains, "include_paths": include_paths, "exclude_paths": exclude_paths, "mode": mode}
            return _run(lambda: client.extract.map(url, **_without_none(_p)))
        tools.append(scavio_map_website)

        def scavio_crawl_website(url: str, max_pages: Optional[int] = None, max_depth: Optional[int] = None, include_paths: Optional[List[str]] = None, exclude_paths: Optional[List[str]] = None, format: Optional[str] = None, mode: Optional[str] = None, wait_seconds: Optional[int] = None, limit: Optional[int] = None) -> dict:
            """Crawl a website from one start URL: same-site pages are discovered and extracted breadth-first within the page, depth and path limits, each returned as Markdown, text or HTML. Pages the site's robots.txt disallows are skipped. Waits up to wait_seconds (default 45) and returns the job id, status, page counts, credits used and the first page of results; if status is still queued or running, call scavio_crawl_status with the id later. Billed per SUCCESSFUL page at the extract price for the mode: 1 credit on normal and advanced, 2 on ultra. Failed and skipped pages are free, and if the balance runs out the crawl stops cleanly.

            Args:
                url: Where the crawl starts. Only pages on the same site are crawled.
                max_pages: Maximum pages to fetch (server default 100). Plan limits: Free 10, PAYG 100, Project 500, Bootstrap 2,000, Startup 5,000, Growth 10,000.
                max_depth: How many links away from the start page to follow, 0-10 (server default 3). 0 fetches only the start page.
                include_paths: Crawl only paths matching these globs (max 20), e.g. ["/docs/**"].
                exclude_paths: Skip paths matching these globs (max 20).
                format: Format for each page: markdown (the default), text or html.
                mode: normal (the default) is the standard fetch, advanced renders JavaScript-built pages, ultra reaches the hardest pages. Sets the per-page price.
                wait_seconds: Seconds to wait for the crawl to finish, 0-300 (default 45). 0 returns the queued job at once.
                limit: Results in the returned page, 1-100 (default 10); page on with scavio_crawl_status.
            """
            body = {"max_pages": max_pages, "max_depth": max_depth, "include_paths": include_paths, "exclude_paths": exclude_paths, "format": format, "mode": mode}
            query = {"limit": 10 if limit is None else limit}
            return _run(lambda: _start_job(client.extract.crawl, client.extract.crawl_status, url, body, wait_seconds, query))
        tools.append(scavio_crawl_website)

        def scavio_crawl_status(id: str, cursor: Optional[str] = None, limit: Optional[int] = None, status: Optional[str] = None, include_content: Optional[bool] = None) -> dict:
            """Read a crawl's progress and its page results by job id, paged by cursor: status, stopped_reason, page counts, credits used, results and next_cursor. Results are kept for 3 days after the crawl finishes. Free: costs 0 credits.

            Args:
                id: The crawl id returned by scavio_crawl_website.
                cursor: next_cursor from the previous response.
                limit: Results per response, 1-100 (default 10).
                status: Only results with this status: succeeded, failed or skipped.
                include_content: Set false to list results without page content. Default true.
            """
            _q = {"cursor": cursor, "limit": 10 if limit is None else limit, "status": status, "include_content": include_content}
            return _run(lambda: client.extract.crawl_status(id, **_without_none(_q)))
        tools.append(scavio_crawl_status)

        def scavio_batch_extract(urls: List[str], format: Optional[str] = None, mode: Optional[str] = None, wait_seconds: Optional[int] = None, limit: Optional[int] = None) -> dict:
            """Extract a list of URLs (up to 1,000, plan-limited) in one job, each returned as Markdown, text or HTML exactly like scavio_extract, results in input order. Waits up to wait_seconds (default 45) and returns the job id, status and the first page of results; if status is still queued or running, call scavio_batch_status with the id later. Billed per SUCCESSFUL page at the extract price for the mode: 1 credit on normal and advanced, 2 on ultra. Failed pages and invalid URLs are free.

            Args:
                urls: The pages to extract (duplicates removed). Plan limits: Free 10, PAYG 50, Project 100, Bootstrap 500, Startup and Growth 1,000.
                format: Format for each page: markdown (the default), text or html.
                mode: normal (the default) is the standard fetch, advanced renders JavaScript-built pages, ultra reaches the hardest pages. Sets the per-page price.
                wait_seconds: Seconds to wait for the batch to finish, 0-300 (default 45). 0 returns the queued job at once.
                limit: Results in the returned page, 1-100 (default 10); page on with scavio_batch_status.
            """
            body = {"format": format, "mode": mode}
            query = {"limit": 10 if limit is None else limit}
            return _run(lambda: _start_job(client.extract.batch, client.extract.batch_status, urls, body, wait_seconds, query))
        tools.append(scavio_batch_extract)

        def scavio_batch_status(id: str, cursor: Optional[str] = None, limit: Optional[int] = None, status: Optional[str] = None, include_content: Optional[bool] = None) -> dict:
            """Read a batch extract's progress and its page results by job id, in input order, paged by cursor. Results are kept for 3 days after the batch finishes. Free: costs 0 credits.

            Args:
                id: The batch id returned by scavio_batch_extract.
                cursor: next_cursor from the previous response.
                limit: Results per response, 1-100 (default 10).
                status: Only results with this status: succeeded, failed or skipped.
                include_content: Set false to list results without page content. Default true.
            """
            _q = {"cursor": cursor, "limit": 10 if limit is None else limit, "status": status, "include_content": include_content}
            return _run(lambda: client.extract.batch_status(id, **_without_none(_q)))
        tools.append(scavio_batch_status)

    return tools
