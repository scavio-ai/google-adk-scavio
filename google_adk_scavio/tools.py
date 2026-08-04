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

    return tools
