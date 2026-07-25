"""Scavio search tools for Google ADK (Agent Development Kit).

Build the tools with `create_scavio_tools()` and pass them to an ADK Agent:

    from google.adk.agents import Agent
    from google_adk_scavio import create_scavio_tools

    agent = Agent(name="search_assistant", model="gemini-2.5-flash", tools=create_scavio_tools())

The factory returns plain Python functions with typed parameters and docstrings;
ADK wraps each one in a FunctionTool automatically. Each provider is gated by an
``enable_*`` flag. Tools return the Scavio JSON response as a dict.
"""

import os
from typing import Any, Callable, Dict, Optional

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


def create_scavio_tools(
    api_key: Optional[str] = None,
    *,
    enable_google: bool = True,
    enable_youtube: bool = True,
    enable_amazon: bool = True,
    enable_walmart: bool = True,
    enable_reddit: bool = True,
) -> list:
    """Build Scavio search tools for a Google ADK Agent.

    Args:
        api_key: Scavio API key. Falls back to the SCAVIO_API_KEY env var.
        enable_google: Register the Google tools. Defaults to True.
        enable_youtube: Register the YouTube tools. Defaults to True.
        enable_amazon: Register the Amazon tools. Defaults to True.
        enable_walmart: Register the Walmart tools. Defaults to True.
        enable_reddit: Register the Reddit tools. Defaults to True.

    Returns:
        A list of plain functions ready to pass as ``tools=`` to an ADK Agent.
    """
    client = ScavioClient(api_key=api_key or os.getenv("SCAVIO_API_KEY"))
    tools: list = []

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

        def scavio_youtube_metadata(video_id: str) -> dict:
            """Fetch full metadata for a YouTube video by id. Deprecated alias of scavio_youtube_video. Costs 1 credit.

            Args:
                video_id: YouTube video id, e.g. dQw4w9WgXcQ.
            """
            return _run(lambda: client.youtube.metadata(video_id))
        tools.append(scavio_youtube_metadata)

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
        def scavio_amazon_search(query: str, domain: Optional[str] = None, country: Optional[str] = None, sort_by: Optional[str] = None, start_page: Optional[int] = None) -> dict:
            """Search Amazon for products matching a query. Costs 1 credit.

            Args:
                query: The product search query.
                domain: Amazon domain suffix, e.g. com or co.uk.
                country: Two-letter country code for localization.
                sort_by: Sort order: featured, price_low_to_high, price_high_to_low, average_review, most_recent, bestsellers.
                start_page: First result page to return (1-based).
            """
            _p = {"domain": domain, "country": country, "sort_by": sort_by, "start_page": start_page}
            return _run(lambda: client.amazon.search(query, **{k: v for k, v in _p.items() if v is not None}))
        tools.append(scavio_amazon_search)

        def scavio_amazon_product(asin: str, domain: Optional[str] = None, country: Optional[str] = None) -> dict:
            """Fetch full Amazon product details by ASIN. Costs 1 credit.

            Args:
                asin: Amazon Standard Identification Number, e.g. B09XS7JWHH.
                domain: Amazon domain suffix, e.g. com or co.uk.
                country: Two-letter country code for localization.
            """
            _p = {"domain": domain, "country": country}
            return _run(lambda: client.amazon.product(asin, **{k: v for k, v in _p.items() if v is not None}))
        tools.append(scavio_amazon_product)

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
        def scavio_reddit_search(query: str, type: Optional[str] = None, sort: Optional[str] = None) -> dict:
            """Search Reddit posts or comments. Costs 2 credits.

            Args:
                query: The Reddit search query.
                type: Result type: posts or comments.
                sort: Sort order: relevance, new, hot, top, comments.
            """
            _p = {"type": type, "sort": sort}
            return _run(lambda: client.reddit.search(query, **{k: v for k, v in _p.items() if v is not None}))
        tools.append(scavio_reddit_search)

        def scavio_reddit_post(url: str) -> dict:
            """Fetch a Reddit post and its threaded comments by URL. Costs 2 credits.

            Args:
                url: Full URL of the Reddit post.
            """
            return _run(lambda: client.reddit.post(url))
        tools.append(scavio_reddit_post)

    return tools
