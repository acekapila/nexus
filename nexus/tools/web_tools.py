import requests
from bs4 import BeautifulSoup
import json
import urllib.parse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ── Search ───────────────────────────────────────────────────────────────────
def search_web(query: str, max_results: int = 6) -> str:
    """
    Search the web. Tries multiple backends in order until one works.
    """
    # Try 1: DuckDuckGo Lite (more stable than HTML)
    try:
        result = _ddg_lite(query, max_results)
        if result and "No results" not in result:
            return result
    except Exception:
        pass

    # Try 2: DuckDuckGo JSON API
    try:
        result = _ddg_json(query, max_results)
        if result and "No results" not in result:
            return result
    except Exception:
        pass

    # Try 3: Bing scrape fallback
    try:
        result = _bing_scrape(query, max_results)
        if result and "No results" not in result:
            return result
    except Exception:
        pass

    return f"⚠️ Could not find web results for: `{query}`\nTry rephrasing or use scrape_page with a direct URL."


def _ddg_lite(query: str, max_results: int) -> str:
    """DuckDuckGo Lite — simpler HTML, more stable."""
    url = "https://lite.duckduckgo.com/lite/"
    r = requests.post(url, data={"q": query}, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    results = []
    rows = soup.select("tr")
    i = 0
    while i < len(rows) and len(results) < max_results:
        link_cell = rows[i].select_one("a.result-link")
        if link_cell:
            title = link_cell.get_text(strip=True)
            href = link_cell.get("href", "")
            # Get snippet from next row
            snippet = ""
            if i + 1 < len(rows):
                snippet_cell = rows[i + 1].select_one("td.result-snippet")
                if snippet_cell:
                    snippet = snippet_cell.get_text(strip=True)
            results.append(f"**{title}**\n{snippet}\n🔗 {href}")
        i += 1

    if not results:
        return "No results"
    return f"🔍 Results for `{query}`:\n\n" + "\n\n---\n\n".join(results)


def _ddg_json(query: str, max_results: int) -> str:
    """DuckDuckGo Instant Answer API — great for factual queries."""
    url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
    r = requests.get(url, headers=HEADERS, timeout=10)
    data = r.json()

    results = []

    # Abstract (main answer)
    if data.get("AbstractText"):
        results.append(f"**{data.get('Heading', query)}**\n{data['AbstractText']}\n🔗 {data.get('AbstractURL', '')}")

    # Related topics
    for topic in data.get("RelatedTopics", [])[:max_results]:
        if isinstance(topic, dict) and topic.get("Text"):
            url_link = topic.get("FirstURL", "")
            results.append(f"**Related:** {topic['Text']}\n🔗 {url_link}")

    if not results:
        return "No results"
    return f"🔍 Results for `{query}`:\n\n" + "\n\n---\n\n".join(results[:max_results])


def _bing_scrape(query: str, max_results: int) -> str:
    """Bing search scrape fallback."""
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    results = []
    for li in soup.select("li.b_algo")[:max_results]:
        title_el = li.select_one("h2 a")
        snippet_el = li.select_one(".b_caption p")
        if title_el:
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            results.append(f"**{title}**\n{snippet}\n🔗 {href}")

    if not results:
        return "No results"
    return f"🔍 Results for `{query}`:\n\n" + "\n\n---\n\n".join(results)


# ── Scrape ───────────────────────────────────────────────────────────────────
def scrape_page(url: str, max_chars: int = 4000) -> str:
    """Scrape text from a URL. Handles JS-rendered sites gracefully."""
    JS_ONLY_SITES = ["cve.mitre.org", "twitter.com", "x.com", "instagram.com", "linkedin.com"]
    API_ALTERNATIVES = {
        "cve.mitre.org": "Use lookup_cve tool instead",
        "nvd.nist.gov":  "Use lookup_cve tool instead",
    }

    for site in JS_ONLY_SITES:
        if site in url:
            alt = API_ALTERNATIVES.get(site, "Try search_web instead")
            return f"⚠️ `{site}` requires JavaScript — cannot scrape.\n💡 {alt}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()

        content_type = r.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                return json.dumps(r.json(), indent=2)[:max_chars]
            except Exception:
                pass

        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
            tag.decompose()

        main = (
            soup.find("main") or soup.find("article") or
            soup.find(id="content") or soup.find(class_="content") or
            soup.find(class_="post-content") or soup.body
        )

        text = main.get_text(separator="\n", strip=True) if main else soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        text = "\n".join(lines)

        js_indicators = ["enable javascript", "javascript is required", "please enable javascript"]
        if any(i in text.lower() for i in js_indicators) and len(text) < 500:
            return f"⚠️ Page requires JavaScript. Try search_web instead.\n🔗 URL: {url}"

        return f"📄 Content from {url}:\n\n{text[:max_chars]}"

    except requests.exceptions.Timeout:
        return f"⚠️ Timed out fetching {url}"
    except requests.exceptions.HTTPError as e:
        return f"⚠️ HTTP {e.response.status_code} for {url}"
    except Exception as e:
        return f"❌ Scrape error: {str(e)}"


# ── API caller ───────────────────────────────────────────────────────────────
def call_api(url: str, method: str = "GET", payload: dict = {}, headers: dict = {}) -> str:
    try:
        merged_headers = {**HEADERS, **headers}
        r = requests.request(method, url, json=payload or None, headers=merged_headers, timeout=15)
        content_type = r.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                return json.dumps(r.json(), indent=2)[:3000]
            except Exception:
                pass
        return r.text[:3000]
    except Exception as e:
        return f"❌ API error: {str(e)}"


# ── NVD CVE lookup ───────────────────────────────────────────────────────────
def lookup_cve(cve_id: str) -> str:
    """Look up a CVE directly from NVD API. No JS required."""
    try:
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
        r = requests.get(url, timeout=15)
        data = r.json()
        vulns = data.get("vulnerabilities", [])
        if not vulns:
            return f"No NVD data found for {cve_id}"
        cve = vulns[0]["cve"]
        desc = cve.get("descriptions", [{}])[0].get("value", "No description")
        metrics = cve.get("metrics", {})
        cvss = ""
        if "cvssMetricV31" in metrics:
            score = metrics["cvssMetricV31"][0]["cvssData"]["baseScore"]
            severity = metrics["cvssMetricV31"][0]["cvssData"]["baseSeverity"]
            cvss = f"\nCVSS v3.1: {score} ({severity})"
        return f"**{cve_id}**{cvss}\n{desc}"
    except Exception as e:
        return f"❌ CVE lookup error: {str(e)}"
