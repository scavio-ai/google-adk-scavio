# google-adk-scavio

[Scavio](https://scavio.dev) real-time search tools for [Google ADK](https://google.github.io/adk-docs/) (Agent Development Kit) — Google, YouTube, Amazon, Walmart, and Reddit, with one API key.

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

Expose only the providers you need:

```python
tools = create_scavio_tools(
    enable_google=True,
    enable_reddit=True,
    enable_youtube=False,
    enable_amazon=False,
    enable_walmart=False,
)
```

## Tools

`create_scavio_tools()` returns plain typed Python functions; ADK wraps each one in a `FunctionTool` automatically. Each returns the structured Scavio JSON response as a dict; errors come back as `{"error": "..."}` rather than raising, so a failed call never crashes the run.

| Tool | Description | Credits |
|---|---|---|
| `scavio_google_search` | Google web results (organic, knowledge graph, AI overview) | 1 |
| `scavio_google_news` | Google News articles | 1 |
| `scavio_youtube_search` | YouTube videos, channels, playlists | 1 |
| `scavio_youtube_metadata` | Full metadata for a video by id | 1 |
| `scavio_amazon_search` | Amazon product search | 1 |
| `scavio_amazon_product` | Amazon product details by ASIN | 1 |
| `scavio_walmart_search` | Walmart product search | 1 |
| `scavio_walmart_product` | Walmart product details by product id | 1 |
| `scavio_reddit_search` | Reddit posts or comments search | 2 |
| `scavio_reddit_post` | Reddit post with threaded comments by URL | 2 |

## Use every endpoint via MCP

For the full Scavio API (TikTok, Instagram, Google Maps, Shopping, Trends, and more), point ADK at the hosted MCP server. Requires ADK's MCP extra: `pip install "google-adk[mcp]"`.

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
