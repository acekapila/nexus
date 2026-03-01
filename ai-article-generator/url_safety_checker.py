"""
url_safety_checker.py — Heuristic-based URL safety checker for the article pipeline.

No external API key required. Uses:
  - Trusted domain whitelist (injected from Crawl4AIURLBrowser.reliable_domains)
  - Suspicious TLD detection
  - Raw IP URL detection
  - URL shortener detection
  - Excessive subdomain detection
  - Typosquatting pattern matching
  - Free DNS blocklist queries (SURBL + SpamHaus DBL) via dnspython
  - Obfuscated/very-long URL detection
"""

import re
import logging
from urllib.parse import urlparse
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ── DNS blocklist support (optional — gracefully skipped if not installed) ────
try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

# Module-level DNS cache — avoids re-querying same domain in one pipeline run
_dns_cache: Dict[str, bool] = {}


class URLSafetyChecker:
    """
    Heuristic URL safety checker.

    Usage:
        checker = URLSafetyChecker(trusted_domains=set(browser.reliable_domains.keys()))
        result = checker.check_url("https://example.com/article")
        # result = {"safe": True, "risk_level": "low", "score": 1.0, "reasons": []}
    """

    SUSPICIOUS_TLDS: Set[str] = {
        ".xyz", ".tk", ".ml", ".cf", ".ga", ".gq", ".top",
        ".click", ".loan", ".win", ".download", ".work",
        ".party", ".racing", ".men", ".bid", ".trade",
        ".stream", ".science", ".accountant", ".review",
        ".date", ".faith", ".webcam", ".cricket",
    }

    URL_SHORTENERS: Set[str] = {
        "bit.ly", "tinyurl.com", "t.co", "ow.ly", "short.io",
        "goo.gl", "buff.ly", "is.gd", "rebrand.ly", "tiny.cc",
        "tr.im", "adf.ly", "bc.vc", "cutt.ly", "shorturl.at",
        "rb.gy", "t.ly", "clck.ru", "urlzs.com",
    }

    TYPOSQUAT_PATTERNS: List[str] = [
        r"g00gle", r"g0ogle", r"go0gle",
        r"micros0ft", r"microsoft",
        r"paypa1", r"paypa-l",
        r"amaz0n", r"amazzon",
        r"faceb00k", r"facebok",
        r"twltter", r"twiter",
        r"app1e",
        r"linkedln",  # lowercase L instead of I
        r"githb", r"githubb",
    ]

    DNSBL_ZONES: List[str] = [
        "multi.surbl.org",
        "dbl.spamhaus.org",
    ]

    # Fallback minimal trusted domains (used when none are injected)
    _FALLBACK_TRUSTED: Set[str] = {
        "thehackernews.com", "bleepingcomputer.com", "darkreading.com",
        "krebsonsecurity.com", "techcrunch.com", "wired.com", "arstechnica.com",
        "zdnet.com", "reuters.com", "bloomberg.com", "forbes.com",
        "microsoft.com", "google.com", "github.com", "cisa.gov", "nist.gov",
        "medium.com", "substack.com", "nature.com", "science.org",
    }

    def __init__(self, trusted_domains: Optional[Set[str]] = None):
        """
        Parameters
        ----------
        trusted_domains : Set of known-good domain strings (e.g. "thehackernews.com").
                          If None, falls back to a minimal built-in set.
                          Inject Crawl4AIURLBrowser.reliable_domains.keys() for full list.
        """
        self.trusted_domains: Set[str] = trusted_domains or self._FALLBACK_TRUSTED
        self._typosquat_compiled = [re.compile(p, re.IGNORECASE) for p in self.TYPOSQUAT_PATTERNS]

    # ── Public API ────────────────────────────────────────────────────────────

    def check_url(self, url: str) -> Dict:
        """
        Run all heuristic checks and return a safety verdict.

        Returns
        -------
        dict with keys:
          safe       : bool   — True if score >= 0.7
          risk_level : str    — "low" | "medium" | "high"
          score      : float  — 0.0–1.3 (starts at 1.0, trusted bonus = +0.3)
          reasons    : list   — human-readable list of flags triggered
        """
        reasons: List[str] = []
        score: float = 1.0

        if not url or not url.startswith(("http://", "https://")):
            return {"safe": False, "risk_level": "high", "score": 0.0,
                    "reasons": ["invalid or empty URL"]}

        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            domain = self._extract_root_domain(hostname)
        except Exception:
            return {"safe": False, "risk_level": "high", "score": 0.0,
                    "reasons": ["URL parse error"]}

        # ── Run each heuristic independently ──────────────────────────────
        delta, reason = self._check_trusted_domain(domain, hostname)
        if reason:
            score += delta
            reasons.append(reason)

        delta, reason = self._check_ip_based_url(hostname)
        if reason:
            score += delta
            reasons.append(reason)

        delta, reason = self._check_suspicious_tld(hostname)
        if reason:
            score += delta
            reasons.append(reason)

        delta, reason = self._check_url_shortener(domain)
        if reason:
            score += delta
            reasons.append(reason)

        delta, reason = self._check_excessive_subdomains(hostname)
        if reason:
            score += delta
            reasons.append(reason)

        delta, reason = self._check_typosquatting(domain)
        if reason:
            score += delta
            reasons.append(reason)

        delta, reason = self._check_dnsbl(domain)
        if reason:
            score += delta
            reasons.append(reason)

        delta, reason = self._check_obfuscated_url(url, parsed)
        if reason:
            score += delta
            reasons.append(reason)

        # ── Final verdict ──────────────────────────────────────────────────
        score = round(max(0.0, min(1.3, score)), 3)
        if score >= 0.7:
            risk_level = "low"
            safe = True
        elif score >= 0.4:
            risk_level = "medium"
            safe = False
        else:
            risk_level = "high"
            safe = False

        return {
            "safe": safe,
            "risk_level": risk_level,
            "score": score,
            "reasons": reasons,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_root_domain(self, hostname: str) -> str:
        """Extract registrable domain (e.g. 'sub.example.com' → 'example.com')."""
        parts = hostname.lower().lstrip("www.").split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return hostname.lower()

    def _check_trusted_domain(self, domain: str, hostname: str) -> tuple:
        """Bonus for known-good domains."""
        try:
            if domain in self.trusted_domains or hostname in self.trusted_domains:
                return +0.3, f"trusted domain: {domain}"
            # Also check if any trusted domain is a suffix of hostname
            for td in self.trusted_domains:
                if hostname.endswith("." + td) or hostname == td:
                    return +0.3, f"trusted domain: {td}"
        except Exception as e:
            logger.debug(f"trusted_domain check error: {e}")
        return 0.0, ""

    def _check_ip_based_url(self, hostname: str) -> tuple:
        """Flag raw IP addresses — legitimate article sources don't use bare IPs."""
        try:
            if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", hostname):
                return -0.5, f"raw IP address URL: {hostname}"
        except Exception as e:
            logger.debug(f"ip_check error: {e}")
        return 0.0, ""

    def _check_suspicious_tld(self, hostname: str) -> tuple:
        """Flag known scam/spam TLDs."""
        try:
            for tld in self.SUSPICIOUS_TLDS:
                if hostname.endswith(tld):
                    return -0.4, f"suspicious TLD: {tld}"
        except Exception as e:
            logger.debug(f"tld_check error: {e}")
        return 0.0, ""

    def _check_url_shortener(self, domain: str) -> tuple:
        """Flag URL shorteners — can hide destinations."""
        try:
            if domain in self.URL_SHORTENERS:
                return -0.35, f"URL shortener: {domain}"
        except Exception as e:
            logger.debug(f"shortener_check error: {e}")
        return 0.0, ""

    def _check_excessive_subdomains(self, hostname: str) -> tuple:
        """Flag hostnames with >3 dot-separated segments (after stripping www.)."""
        try:
            clean = hostname.lstrip("www.")
            segments = clean.split(".")
            if len(segments) > 4:  # e.g. a.b.c.d.example.com = 6 parts
                return -0.25, f"excessive subdomains ({len(segments)} levels): {hostname}"
        except Exception as e:
            logger.debug(f"subdomain_check error: {e}")
        return 0.0, ""

    def _check_typosquatting(self, domain: str) -> tuple:
        """Flag domains that pattern-match known typosquatting patterns."""
        try:
            for pattern in self._typosquat_compiled:
                if pattern.search(domain):
                    return -0.4, f"possible typosquatting: matched '{pattern.pattern}'"
        except Exception as e:
            logger.debug(f"typosquat_check error: {e}")
        return 0.0, ""

    def _check_dnsbl(self, domain: str) -> tuple:
        """Query free DNS blocklists (SURBL + SpamHaus DBL). Cached per domain."""
        if not DNS_AVAILABLE or not domain:
            return 0.0, ""
        global _dns_cache
        try:
            if domain in _dns_cache:
                if _dns_cache[domain]:
                    return -0.5, f"DNS blocklist listed: {domain}"
                return 0.0, ""

            resolver = dns.resolver.Resolver()
            resolver.lifetime = 2.0  # 2-second total timeout

            for zone in self.DNSBL_ZONES:
                query = f"{domain}.{zone}"
                try:
                    resolver.resolve(query, "A")
                    # Got a result → domain is blocklisted
                    _dns_cache[domain] = True
                    return -0.5, f"DNS blocklist listed ({zone}): {domain}"
                except dns.resolver.NXDOMAIN:
                    pass  # Clean — domain not in this list
                except (dns.resolver.NoAnswer, dns.resolver.NoNameservers,
                        dns.exception.Timeout, dns.resolver.LifetimeTimeout):
                    pass  # Inconclusive — don't penalise

            _dns_cache[domain] = False
        except Exception as e:
            logger.debug(f"dnsbl_check error for {domain}: {e}")
        return 0.0, ""

    def _check_obfuscated_url(self, url: str, parsed) -> tuple:
        """Flag suspiciously long URLs with high proportion of hex/random chars."""
        try:
            if len(url) > 200:
                path = parsed.path or ""
                if len(path) > 0:
                    hex_chars = sum(1 for c in path if c in "0123456789abcdefABCDEF-_")
                    ratio = hex_chars / len(path)
                    if ratio > 0.6:
                        return -0.2, f"obfuscated/long URL ({len(url)} chars, {ratio:.0%} hex)"
        except Exception as e:
            logger.debug(f"obfuscation_check error: {e}")
        return 0.0, ""


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    checker = URLSafetyChecker()
    test_urls = [
        "https://thehackernews.com/2026/02/clawjacked-flaw.html",
        "http://91.92.242.30/malware.exe",
        "https://cdn-fake-news.xyz/article/ai-scam",
        "https://bit.ly/3xYzAbC",
        "https://g00gle.com/redirect",
        "https://sub.sub.sub.sub.evil.example.com/page",
        "https://microsoft.com/security/blog/2026",
        "https://oasis.security/blog/openclaw-vulnerability",
    ]
    for url in test_urls:
        result = checker.check_url(url)
        icon = "✅" if result["safe"] else "⚠️"
        print(f"{icon} [{result['risk_level'].upper():<6}] score={result['score']:.2f}  {url[:70]}")
        if result["reasons"]:
            for r in result["reasons"]:
                print(f"    → {r}")
