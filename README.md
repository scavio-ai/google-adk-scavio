# google-adk-scavio

[Scavio](https://scavio.dev) real-time search and page-extraction tools for [Google ADK](https://google.github.io/adk-docs/) (Agent Development Kit) — Google, YouTube, Amazon, Walmart, Reddit, and `scavio_extract` (read any URL), with one API key.

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

### Reading a page

`scavio_extract` is the one tool here that is not tied to a platform: give it any
URL and it returns the page as `data.content`, alongside `data.url`,
`data.format`, `data.mode` and `data.content_length`.

Its price is a function of `mode`, not a per-call constant. `normal` (the
default) is a plain fetch and costs **1** credit, `advanced` renders the page in
a browser for JS-built sites and costs **1**, and `ultra` routes through
residential proxies for the hardest bot walls and costs **2**. Start on `normal`.
Only a successful read is billed — a dead link, a bot wall or a timeout costs
nothing. See [the extract docs](https://scavio.dev/docs/extract).

`format` picks the shape: `markdown` (the default) is a readability extraction
with the page chrome stripped, `text` is that flattened to plain text, and `html`
is the raw page.

## Use every endpoint via MCP

This package is a **curated subset** of the Scavio API, not the whole thing: 16 tools — 15 across 5 platforms, plus the core `extract` endpoint. For full coverage — all 195 endpoints across 31 platforms (Google, YouTube, Amazon, Walmart, Reddit, TikTok, TikTok Shop, Instagram, X, LinkedIn, eBay, Target, Home Depot, Zillow, Redfin, Booking, Airbnb, Tripadvisor, Yelp, Indeed, Glassdoor, the App Store, Google Play, SEC, Companies House, G2, Capterra, Google Ads, Meta Ad Library, Threads and Kuaishou) — point ADK at the hosted MCP server at `mcp.scavio.dev`, which exposes 191 tools. Requires ADK's MCP extra: `pip install "google-adk[mcp]"`.

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
