"""Tests for google-adk-scavio. The Scavio SDK client is mocked; no key or network used,
except the env-gated live test at the bottom."""

import os

import pytest

import google_adk_scavio.tools as tools_mod
from google_adk_scavio import create_scavio_tools

ALL_TOOL_NAMES = {
    "scavio_extract",
    "scavio_google_search",
    "scavio_google_news",
    "scavio_youtube_search",
    "scavio_youtube_video",
    "scavio_youtube_comments",
    "scavio_youtube_channel",
    "scavio_youtube_transcript",
    "scavio_youtube_streams",
    "scavio_amazon_search",
    "scavio_amazon_product",
    "scavio_amazon_offers",
    "scavio_walmart_search",
    "scavio_walmart_product",
    "scavio_reddit_search",
    "scavio_reddit_post",
}


class _Recorder:
    def __init__(self, calls):
        self._calls = calls

    def __getattr__(self, method):
        def _call(*args, **kwargs):
            self._calls.append((method, args, kwargs))
            return {"ok": True, "method": method, "args": args, "kwargs": kwargs}

        return _call


class _FakeClient:
    def __init__(self, *args, **kwargs):
        self.calls = []
        for ns in ("google", "youtube", "amazon", "walmart", "reddit"):
            setattr(self, ns, _Recorder(self.calls))

    # extract is a TOP-LEVEL method on the client, never a namespace:
    # client.extract(url), never client.extract.extract(). A tool calling the
    # latter would blow up here, which is the point.
    def extract(self, url, **kwargs):
        self.calls.append(("extract", (url,), kwargs))
        return {"ok": True, "method": "extract", "args": (url,), "kwargs": kwargs}


class _RaisingClient:
    def __init__(self, *args, **kwargs):
        class _Boom:
            def __getattr__(self, method):
                def _call(*a, **kw):
                    raise RuntimeError("scavio exploded")

                return _call

        for ns in ("google", "youtube", "amazon", "walmart", "reddit"):
            setattr(self, ns, _Boom())

    def extract(self, url, **kwargs):
        raise RuntimeError("scavio exploded")


def _build(monkeypatch, **kwargs):
    monkeypatch.setattr(tools_mod, "ScavioClient", _FakeClient)
    return create_scavio_tools(api_key="test", **kwargs)


def _get(tools, name):
    return next(t for t in tools if t.__name__ == name)


def test_all_tools_register(monkeypatch):
    tools = _build(monkeypatch)
    names = [t.__name__ for t in tools]
    assert len(names) == len(set(names)) == 16
    assert set(names) == ALL_TOOL_NAMES


def test_deprecated_youtube_metadata_alias_not_registered(monkeypatch):
    """/youtube/metadata is a deprecated alias of /youtube/video, not a peer tool."""
    names = {t.__name__ for t in _build(monkeypatch)}
    assert "scavio_youtube_metadata" not in names
    assert "scavio_youtube_video" in names


def test_provider_gating(monkeypatch):
    tools = _build(
        monkeypatch,
        enable_extract=False,
        enable_google=False,
        enable_youtube=False,
        enable_amazon=False,
        enable_walmart=False,
        enable_reddit=True,
    )
    assert {t.__name__ for t in tools} == {"scavio_reddit_search", "scavio_reddit_post"}


def test_extract_is_gated_on_its_own_flag(monkeypatch):
    """extract gates no platform - it reads any URL - but it stays switchable."""
    assert "scavio_extract" not in {t.__name__ for t in _build(monkeypatch, enable_extract=False)}
    tools = _build(
        monkeypatch,
        enable_google=False,
        enable_youtube=False,
        enable_amazon=False,
        enable_walmart=False,
        enable_reddit=False,
    )
    assert {t.__name__ for t in tools} == {"scavio_extract"}


def test_extract_is_a_top_level_method_not_a_namespace(monkeypatch):
    """client.extract(url, ...), never client.extract.extract()."""
    e = _get(_build(monkeypatch), "scavio_extract")
    out = e("https://example.com/pricing")
    assert out["method"] == "extract"
    assert out["args"] == ("https://example.com/pricing",)
    assert out["kwargs"] == {}


def test_extract_sends_format_and_mode_and_drops_none(monkeypatch):
    """mode is the PRICE-BEARING param (normal 1, advanced 1, ultra 2)."""
    e = _get(_build(monkeypatch), "scavio_extract")
    out = e("https://example.com", format="text", mode="ultra")
    assert out["kwargs"] == {"format": "text", "mode": "ultra"}
    assert e("https://example.com", mode="advanced")["kwargs"] == {"mode": "advanced"}


def test_extract_signature_offers_only_url_format_mode(monkeypatch):
    """The route takes url, format and mode; anything else is stripped server-side."""
    import inspect

    e = _get(_build(monkeypatch), "scavio_extract")
    assert set(inspect.signature(e).parameters) == {"url", "format", "mode"}


def test_extract_is_never_advertised_at_a_flat_credit_cost(monkeypatch):
    """Extract is TIER-PRICED by mode; a flat "Costs 1 credit." would be a lie."""
    doc = _get(_build(monkeypatch), "scavio_extract").__doc__
    assert "Costs 1 credit on normal and advanced, 2 on ultra" in doc
    assert "Costs 1 credit." not in doc


def test_google_search_sends_gl_hl(monkeypatch):
    g = _get(_build(monkeypatch), "scavio_google_search")
    out = g("ai agents", gl="fr", hl="fr")
    assert isinstance(out, dict)
    assert out["method"] == "search"
    assert out["args"] == ("ai agents",)
    assert out["kwargs"] == {"gl": "fr", "hl": "fr"}


def test_google_search_drops_none(monkeypatch):
    g = _get(_build(monkeypatch), "scavio_google_search")
    out = g("ai agents")
    assert out["args"] == ("ai agents",)
    assert out["kwargs"] == {}


def test_google_news_sends_query_kwarg(monkeypatch):
    n = _get(_build(monkeypatch), "scavio_google_news")
    out = n("openai", gl="us")
    assert out["method"] == "news"
    assert out["args"] == ()
    assert out["kwargs"] == {"query": "openai", "gl": "us"}


def test_amazon_product_uses_asin(monkeypatch):
    p = _get(_build(monkeypatch), "scavio_amazon_product")
    out = p("B000000000")
    assert out["method"] == "product"
    assert out["args"] == ("B000000000",)


def test_reddit_search_only_takes_query_and_cursor(monkeypatch):
    """/reddit/search accepts query + cursor only; type and sort do not exist."""
    import inspect

    r = _get(_build(monkeypatch), "scavio_reddit_search")
    assert set(inspect.signature(r).parameters) == {"query", "cursor"}
    out = r("serpapi alternative", cursor="t3_abc")
    assert out["method"] == "search"
    assert out["args"] == ("serpapi alternative",)
    assert out["kwargs"] == {"cursor": "t3_abc"}


def test_reddit_tools_priced_at_one_credit(monkeypatch):
    """Reddit dropped from 2 credits to 1 when it moved to its current upstream source."""
    tools = _build(monkeypatch)
    for name in ("scavio_reddit_search", "scavio_reddit_post"):
        doc = _get(tools, name).__doc__
        assert "Costs 1 credit." in doc
        assert "2 credits" not in doc


def test_youtube_search_priced_at_two_credits(monkeypatch):
    doc = _get(_build(monkeypatch), "scavio_youtube_search").__doc__
    assert "Costs 2 credits." in doc


def test_errors_wrapped_not_raised(monkeypatch):
    monkeypatch.setattr(tools_mod, "ScavioClient", _RaisingClient)
    tools = create_scavio_tools(api_key="test")
    g = _get(tools, "scavio_google_search")
    assert g("boom") == {"error": "scavio exploded"}
    e = _get(tools, "scavio_extract")
    assert e("https://example.com") == {"error": "scavio exploded"}


def test_package_version_matches_pyproject():
    """The version is declared twice - pyproject.toml and __init__.__version__."""
    import pathlib
    import re

    import google_adk_scavio

    pyproject = (pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    declared = re.search(r'^version = "([^"]+)"', pyproject, re.M).group(1)
    assert google_adk_scavio.__version__ == declared == "0.3.0"


def test_adk_function_tool_wraps(monkeypatch):
    """ADK must be able to wrap every tool function as a FunctionTool."""
    from google.adk.tools import FunctionTool

    tools = _build(monkeypatch)
    wrapped = [FunctionTool(t) for t in tools]
    assert {w.name for w in wrapped} == ALL_TOOL_NAMES
    assert all(w.description for w in wrapped)


@pytest.mark.skipif("SCAVIO_API_KEY" not in os.environ, reason="requires live API key")
def test_live_google_search():
    """One live call against api.scavio.dev (set SCAVIO_API_KEY to run)."""
    tools = create_scavio_tools(
        enable_extract=False,
        enable_youtube=False,
        enable_amazon=False,
        enable_walmart=False,
        enable_reddit=False,
    )
    g = _get(tools, "scavio_google_search")
    out = g("scavio search api for ai agents", gl="us", hl="en")
    assert "error" not in out, out.get("error")
    assert out.get("organic_results"), out
    first = out["organic_results"][0]
    assert first["link"].startswith("http")
    assert first["title"]
