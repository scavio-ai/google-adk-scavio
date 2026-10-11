# google-adk-scavio

[Scavio](https://scavio.dev) real-time search and page-extraction tools for [Google ADK](https://google.github.io/adk-docs/) (Agent Development Kit) — Google, YouTube, Amazon, Walmart, Reddit, `scavio_extract` (read any URL), and opt-in website tools that map, crawl and batch-extract whole sites, with one API key.

> **New in 0.4.0: map, crawl and batch (opt-in).** `create_scavio_tools(enable_crawl=True)`
> adds `scavio_map_website`, `scavio_crawl_website`, `scavio_crawl_status`,
> `scavio_batch_extract` and `scavio_batch_status`. Requires `scavio>=0.23.0`.
> See [Map, crawl and batch](#map-crawl-and-batch).

> **Amazon changed (breaking).** The upstream provider moved in 2026-07:
> `domain` is replaced by `country`, a two-letter marketplace code (`us`, `gb`
> -- the UK is `gb`, not `uk` -- `de`, `jp`, ...), and `sort_by`, `pages`,
> `category_id`, `merchant_id`, `language`, `currency`, `device`, `zip_code`
> and `autoselect_variant` are gone. The marketplace ignores all of them
> (`sort_by` returns the identical unordered set for every value), so they are
> removed rather than kept as silent no-ops. Rank and filter results yourself.

> **Reddit changed (breaking).** Reddit moved upstream in 2026-07 and now costs
> **1 credit**, not 2. `scavio_reddit_search` takes `query` and `cursor` only:
> `type` and `sort` never reached the provider and are gone rather than kept as
> silent no-ops. `scavio_reddit_post` returns a flat post object and **no
> comments** -- fetch those from the Reddit comments endpoints via MCP or the
> `scavio` SDK.

## Install

```bash
pip install google-adk-scavio
```

## Setup

Get a Scavio API key from the [Scavio Dashboard](https://dashboard.scavio.dev) (new accounts get 50 free signup credits, no credit card). Set `SCAVIO_API_KEY` or pass `api_key=` to the factory.

## Usage

```python
from google.adk.agents import Agent
from google_adk_scavio import create_scavio_tools

root_agent = Agent(
    name="search_assistant",
    model="gemini-2.5-flash",
    instruction="Search the web, news, shopping sites, and Reddit with the Scavio tools.",
    tools=create_scavio_tools(),  # reads SCAVIO_API_KEY
)
```

Expose only the tools you need:

```python
tools = create_scavio_tools(
    enable_extract=True,
    enable_google=True,
    enable_reddit=True,
    enable_youtube=False,
    enable_amazon=False,
    enable_walmart=False,
)
```

`enable_extract` is the odd flag out: every other flag gates a platform, while
`scavio_extract` is a core endpoint that reads any URL and belongs to none.
`enable_crawl` (off by default, because a crawl bills per page) adds the five
website tools.

## Tools

`create_scavio_tools()` returns plain typed Python functions; ADK wraps each one in a `FunctionTool` automatically. Each returns the structured Scavio JSON response as a dict; errors come back as `{"error": "..."}` rather than raising, so a failed call never crashes the run.

| Tool | Description | Credits |
|---|---|---|
| `scavio_extract` | Read any URL as Markdown, plain text, or raw HTML *(core endpoint, not a platform)* | 1 / 1 / 2 by `mode` |
| `scavio_google_search` | Google web results (organic, knowledge graph, AI overview) | 1 |
| `scavio_google_news` | Google News articles | 1 |
| `scavio_youtube_search` | YouTube videos, channels, playlists | 2 |
| `scavio_youtube_video` | Full metadata for a video by id or watch URL | 1 |
| `scavio_youtube_comments` | Top-level comments on a video | 1 |
| `scavio_youtube_channel` | Channel details by id, @handle, or URL | 1 |
| `scavio_youtube_transcript` | Transcript or timed subtitles for a video | 8 |
| `scavio_youtube_streams` | Playable and downloadable stream formats | 3 |
| `scavio_amazon_search` | Amazon product search | 1 |
| `scavio_amazon_product` | Amazon product details by ASIN | 1 |
| `scavio_amazon_offers` | Every seller offer for an ASIN, including the buy-box winner | 1 |
| `scavio_walmart_search` | Walmart product search | 1 |
| `scavio_walmart_product` | Walmart product details by product id | 1 |
| `scavio_reddit_search` | Reddit post search (relevance-ordered, no sort or type filter) | 1 |
| `scavio_reddit_post` | A single Reddit post by URL, as a flat object with no comments | 1 |
| `scavio_map_website` | A site's page URLs from its sitemaps and start page *(`enable_crawl`)* | 1 on normal (up to 2 advanced, 10 ultra) |
| `scavio_crawl_website` | Crawl a site from one URL; every page as Markdown, text or HTML *(`enable_crawl`)* | 1 / 1 / 2 per successful page by `mode` |
| `scavio_crawl_status` | A crawl's progress and page results, cursor-paged *(`enable_crawl`)* | free |
| `scavio_batch_extract` | Extract a list of URLs in one job *(`enable_crawl`)* | 1 / 1 / 2 per successful page by `mode` |
| `scavio_batch_status` | A batch's progress and page results, cursor-paged *(`enable_crawl`)* | free |

### Reading a page

`scavio_extract` is the one tool here that is not tied to a platform: give it any
URL and it returns the page as `data.content`, alongside `data.url`,
`data.format`, `data.mode` and `data.content_length`.

Its price is a function of `mode`, not a per-call constant. `normal` (the
default) is the standard fetch and costs **1** credit, `advanced` renders
JavaScript-built pages and costs **1**, and `ultra` reaches the hardest pages
and costs **2**. Start on `normal`.
Only a successful read is billed — a dead link, a bot wall or a timeout costs
nothing. See [the extract docs](https://scavio.dev/docs/extract).

`format` picks the shape: `markdown` (the default) is a readability extraction
with the page chrome stripped, `text` is that flattened to plain text, and `html`
is the raw page.

### Map, crawl and batch

When one page is not enough, `enable_crawl=True` adds five website tools.
`scavio_map_website` answers in one call. `scavio_crawl_website` and
`scavio_batch_extract` start a background job, **wait up to `wait_seconds`
(default 45, max 300)** for it to finish, and return the job's status with its
first page of results (10 by default) either way. A job that is still `queued`
or `running` when the wait ends keeps going: the agent reads the rest, free,
with `scavio_crawl_status` / `scavio_batch_status` and the job id. That keeps
an agent turn bounded while a large crawl (up to 6 hours) runs on.

```python
root_agent = Agent(
    name="docs_reader",
    model="gemini-2.5-flash",
    instruction="Map the site first, then crawl only the section you need.",
    tools=create_scavio_tools(enable_crawl=True, enable_youtube=False, enable_amazon=False,
                              enable_walmart=False, enable_reddit=False),
)

# Or call the functions directly:
tools = {t.__name__: t for t in create_scavio_tools(enable_crawl=True)}
tools["scavio_map_website"]("https://hono.dev/docs", limit=50)
job = tools["scavio_crawl_website"]("https://hono.dev/docs", max_pages=25, include_paths=["/docs/**"])
tools["scavio_crawl_status"](job["data"]["id"], cursor=job["data"]["next_cursor"])
tools["scavio_batch_extract"](["https://example.com/", "https://hono.dev/docs"])
```

**Pricing.** Map costs 1 credit in normal mode (advanced up to 2, ultra up to
10, priced by what the call needed). Crawl and batch bill **per successful
page** at extract's price for the mode -- normal and advanced 1 credit, ultra 2
-- while failed and skipped pages are free; if your balance runs out the job
stops cleanly with `stopped_reason: "insufficient_credits"`. Reading a job is
free. Crawl and map obey the site's robots.txt; results are kept for 3 days.
Plan limits (pages per crawl / active jobs / URLs per batch): Free 10/1/10,
PAYG 100/1/50, Project 500/2/100, Bootstrap 2,000/3/500, Startup
5,000/5/1,000, Growth 10,000/10/1,000. Webhooks, idempotency keys, cancellation
and the rarer crawl options (subdomains, sitemap mode, query-string handling)
are on the [REST API](https://scavio.dev/docs/extract) and the `scavio` SDK
(`client.extract.crawl(...)`, `client.extract.cancel_crawl(...)`), not exposed
as agent tools.

## Use every endpoint via MCP

This package is a **curated subset** of the Scavio API, not the whole thing: 21 tools — 15 across 5 platforms, plus the core `extract` endpoint and the 5 opt-in website tools. For full coverage — all 195 endpoints across 31 platforms (Google, YouTube, Amazon, Walmart, Reddit, TikTok, TikTok Shop, Instagram, X, LinkedIn, eBay, Target, Home Depot, Zillow, Redfin, Booking, Airbnb, Tripadvisor, Yelp, Indeed, Glassdoor, the App Store, Google Play, SEC, Companies House, G2, Capterra, Google Ads, Meta Ad Library, Threads and Kuaishou) — point ADK at the hosted MCP server at `mcp.scavio.dev`, which exposes 191 tools. Requires ADK's MCP extra: `pip install "google-adk[mcp]"`.

```python
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

scavio = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://mcp.scavio.dev/mcp",
        headers={"x-api-key": "sk_live_..."},
    )
)

root_agent = Agent(name="search_assistant", model="gemini-2.5-flash", tools=[scavio])
```

## Links

- Scavio: https://scavio.dev
- Docs: https://scavio.dev/docs/google-adk
- Dashboard: https://dashboard.scavio.dev

## License

MIT
