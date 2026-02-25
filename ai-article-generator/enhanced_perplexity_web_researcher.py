# enhanced_perplexity_web_researcher.py - Final fixed version with robust URL cleaning and extraction
import os
import json
import requests
import asyncio
import aiohttp
import openai
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
import time
from bs4 import BeautifulSoup
import logging
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BrowsedContent:
    """Container for content extracted from URLs"""
    url: str
    title: str
    content: str
    word_count: int
    author: str
    publish_date: str
    extraction_method: str
    success: bool
    error_message: str = ""

class EnhancedURLBrowser:
    """URL browser for extracting content from research URLs"""
    
    def __init__(self):
        self.session = None
        self.rate_limit_delay = 1.0  # Reduced delay
        self.max_content_length = 50000
        self.timeout = 15  # Reduced timeout
        self.max_retries = 2  # Reduced retries
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        # Reliable domains for content extraction
        self.reliable_domains = {
            'medium.com', 'towardsdatascience.com', 'hackernoon.com', 
            'techcrunch.com', 'wired.com', 'arstechnica.com', 'zdnet.com',
            'cnn.com', 'bbc.com', 'reuters.com', 'bloomberg.com',
            'forbes.com', 'businessinsider.com', 'nature.com', 'science.org',
            'keepnetlabs.com', 'knowbe4.com', 'techmagic.co', 'securelist.com',
            'fraud.com', 'alloy.com', 'arthurstatebank.com', 'acfe.com',
            'veriff.com', 'seon.io', 'pindrop.com'
        }
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=3, ssl=False)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': self.user_agents[0]}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def clean_url(self, raw_url: str) -> str:
        """Clean and fix malformed URLs"""
        if not raw_url:
            return ""
        
        # Remove common trailing characters that break URLs
        url = raw_url.strip()
        
        # Remove trailing punctuation and brackets
        while url and url[-1] in ').,;[]{}':
            url = url[:-1]
        
        # Handle concatenated URLs - take the first valid one
        if '),[' in url or '][' in url:
            # This looks like multiple URLs concatenated, extract the first valid one
            parts = re.split(r'\),[,\[\]]+', url)
            for part in parts:
                clean_part = part.strip('()[].,')
                if clean_part.startswith('http'):
                    return clean_part
        
        # Handle URLs with citation markers
        if ')[' in url:
            url = url.split(')[')[0]
        
        # Remove citation markers like "). " or ")."
        url = re.sub(r'\)[\.\,\s]*$', '', url)
        
        return url
    
    def extract_prioritized_urls(self, research_data: Dict) -> List[Dict]:
        """Extract and prioritize URLs from research data with enhanced cleaning"""
        urls_with_metadata = []
        seen_urls = set()
        
        print(f"DEBUG: Starting URL extraction from research data")
        
        # Extract from all sections
        sections = [
            ('individual_queries', research_data.get('individual_queries', {})),
            ('synthesis', {'sources': research_data.get('synthesis', {}).get('sources', [])}),
            ('total_sources', {'sources': research_data.get('total_sources', [])})
        ]
        
        for section_name, section_data in sections:
            if section_name == 'individual_queries':
                for query_key, query_data in section_data.items():
                    sources = query_data.get('sources', [])
                    self._extract_urls_from_sources(sources, urls_with_metadata, seen_urls, f"{section_name}_{query_key}")
            else:
                sources = section_data.get('sources', [])
                self._extract_urls_from_sources(sources, urls_with_metadata, seen_urls, section_name)
        
        # Sort by priority
        urls_with_metadata.sort(key=lambda x: x['priority'], reverse=True)
        
        print(f"DEBUG: Final URL extraction results:")
        print(f"DEBUG: Total clean URLs found: {len(urls_with_metadata)}")
        for i, url_data in enumerate(urls_with_metadata[:10]):  # Show top 10
            print(f"  {i+1}. {url_data['url'][:80]}... (priority: {url_data['priority']}, source: {url_data['source']})")
        
        return urls_with_metadata
    
    def _extract_urls_from_sources(self, sources: List[Dict], urls_with_metadata: List[Dict], 
                                 seen_urls: set, source_name: str):
        """Extract URLs from a list of sources"""
        print(f"DEBUG: Processing {len(sources)} sources from {source_name}")
        
        for i, source in enumerate(sources):
            raw_url = source.get('url', '').strip()
            title = source.get('title', 'Unknown')
            
            if not raw_url:
                continue
            
            # Clean the URL
            clean_url = self.clean_url(raw_url)
            print(f"DEBUG: Source {i+1}: Raw='{raw_url[:60]}...' -> Clean='{clean_url[:60]}...'")
            
            if clean_url and self._is_valid_article_url(clean_url) and clean_url not in seen_urls:
                priority = self._calculate_url_priority(clean_url, source)
                if source_name == 'synthesis':
                    priority += 1  # Synthesis bonus
                
                urls_with_metadata.append({
                    'url': clean_url,
                    'title': title,
                    'snippet': source.get('snippet', ''),
                    'priority': priority,
                    'source': source_name
                })
                seen_urls.add(clean_url)
                print(f"DEBUG: Added URL with priority {priority}")
            else:
                if not clean_url:
                    print(f"DEBUG: Skipped - URL cleaning failed")
                elif clean_url in seen_urls:
                    print(f"DEBUG: Skipped - duplicate URL")
                else:
                    print(f"DEBUG: Skipped - invalid URL")
    
    def _calculate_url_priority(self, url: str, source: Dict) -> int:
        """Calculate priority score for URL"""
        priority = 0
        domain = urlparse(url).netloc.lower().replace('www.', '')
        
        if domain in self.reliable_domains:
            priority += 3
        
        snippet = source.get('snippet', '')
        if len(snippet) > 200:
            priority += 3
        elif len(snippet) > 100:
            priority += 2
        elif len(snippet) > 50:
            priority += 1
        
        title = source.get('title', '')
        if len(title) > 20 and not title.lower().startswith('source'):
            priority += 1
        
        if any(keyword in url.lower() for keyword in ['blog', 'article', 'post', 'news', 'research', 'report']):
            priority += 1
        
        return priority
    
    def _is_valid_article_url(self, url: str) -> bool:
        """Enhanced URL validation with debugging"""
        if not url or not url.startswith(('http://', 'https://')):
            return False
        
        # Skip social media domains but be less restrictive
        skip_domains = {
            'youtube.com', 'youtu.be', 'twitter.com', 'x.com', 'facebook.com',
            'instagram.com', 'linkedin.com', 'reddit.com', 'pinterest.com',
            'tiktok.com', 'discord.com', 'telegram.org'
        }
        
        parsed_url = urlparse(url.lower())
        domain = parsed_url.netloc.replace('www.', '')
        
        if any(skip_domain in domain for skip_domain in skip_domains):
            return False
        
        # Only block obvious file extensions
        path = parsed_url.path.lower()
        skip_extensions = {'.pdf', '.doc', '.docx', '.zip', '.mp4', '.mp3', '.jpg', '.png', '.gif'}
        
        if any(path.endswith(ext) for ext in skip_extensions):
            return False
        
        return True
    
    async def browse_urls(self, urls_with_metadata: List[Dict], max_urls: int = 8) -> List[BrowsedContent]:
        """Browse URLs and extract content with enhanced debugging"""
        
        print(f"DEBUG: browse_urls called with {len(urls_with_metadata)} URLs, max_urls={max_urls}")
        
        if not urls_with_metadata:
            print("DEBUG: No URLs provided to browse_urls method")
            return []
        
        urls_to_browse = urls_with_metadata[:max_urls]
        print(f"DEBUG: Will attempt to browse {len(urls_to_browse)} URLs")
        
        browsed_contents = []
        
        async with self:
            for i, url_data in enumerate(urls_to_browse):
                url = url_data['url']
                print(f"DEBUG: Attempting URL {i+1}/{len(urls_to_browse)}: {url}")
                
                try:
                    content = await self._extract_content_from_url(url)
                    print(f"DEBUG: Extraction result - Success: {content.success}, Words: {content.word_count}, Method: {content.extraction_method}")
                    
                    if content.success and content.word_count > 20:  # Very low threshold
                        browsed_contents.append(content)
                        print(f"   SUCCESS: {content.word_count} words extracted using {content.extraction_method}")
                    else:
                        print(f"   FAILED: {content.error_message}")
                
                except Exception as e:
                    print(f"   EXCEPTION: {str(e)}")
                    continue
                
                await asyncio.sleep(self.rate_limit_delay)
        
        print(f"DEBUG: Final browsing result - {len(browsed_contents)} URLs successfully processed")
        return browsed_contents
    
    async def _extract_content_from_url(self, url: str) -> BrowsedContent:
        """Extract content from a single URL with enhanced error handling"""
        for attempt in range(self.max_retries):
            try:
                user_agent = self.user_agents[attempt % len(self.user_agents)]
                headers = {
                    'User-Agent': user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                
                async with self.session.get(url, headers=headers, allow_redirects=True) as response:
                    print(f"DEBUG: HTTP {response.status} for {url}")
                    
                    if response.status != 200:
                        if attempt == self.max_retries - 1:
                            return BrowsedContent(
                                url=url, title="", content="", word_count=0,
                                author="", publish_date="", extraction_method="failed",
                                success=False, error_message=f"HTTP {response.status}"
                            )
                        continue
                    
                    # Check content type
                    content_type = response.headers.get('content-type', '').lower()
                    if 'text/html' not in content_type and 'application/xhtml' not in content_type:
                        return BrowsedContent(
                            url=url, title="", content="", word_count=0,
                            author="", publish_date="", extraction_method="wrong_content_type",
                            success=False, error_message=f"Not HTML: {content_type}"
                        )
                    
                    try:
                        html_content = await response.text(encoding='utf-8', errors='ignore')
                    except:
                        html_content = await response.text(errors='ignore')
                    
                    print(f"DEBUG: Retrieved {len(html_content)} characters of HTML")
                    
                    if len(html_content) < 500:
                        return BrowsedContent(
                            url=url, title="", content="", word_count=0,
                            author="", publish_date="", extraction_method="insufficient_html",
                            success=False, error_message="HTML too short"
                        )
                    
                    soup = BeautifulSoup(html_content, 'html.parser')
                    return self._extract_content_from_soup(soup, url)
            
            except asyncio.TimeoutError:
                print(f"DEBUG: Timeout for {url} on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    return BrowsedContent(
                        url=url, title="", content="", word_count=0,
                        author="", publish_date="", extraction_method="timeout",
                        success=False, error_message="Request timeout"
                    )
            except Exception as e:
                print(f"DEBUG: Exception for {url} on attempt {attempt + 1}: {str(e)}")
                if attempt == self.max_retries - 1:
                    return BrowsedContent(
                        url=url, title="", content="", word_count=0,
                        author="", publish_date="", extraction_method="exception",
                        success=False, error_message=str(e)
                    )
        
        return BrowsedContent(
            url=url, title="", content="", word_count=0,
            author="", publish_date="", extraction_method="failed",
            success=False, error_message="Max retries exceeded"
        )
    
    def _extract_content_from_soup(self, soup: BeautifulSoup, url: str) -> BrowsedContent:
        """Extract content from BeautifulSoup object with aggressive strategies"""
        
        # Extract metadata first
        title = self._extract_title(soup)
        author = self._extract_author(soup)
        publish_date = self._extract_publish_date(soup)
        
        print(f"DEBUG: Metadata - Title: '{title[:50]}...' Author: '{author}' Date: '{publish_date}'")
        
        # Clean soup BEFORE content extraction
        self._clean_soup(soup)
        
        # Try multiple extraction strategies with debugging
        content = ""
        extraction_method = ""
        strategies = []
        
        # Strategy 1: JSON-LD structured data
        json_content = self._extract_from_json_ld(soup)
        if json_content:
            strategies.append(("json_ld", json_content, len(json_content.split())))
        
        # Strategy 2: Article tags
        article = soup.find('article')
        if article:
            article_content = article.get_text(separator=' ', strip=True)
            if article_content:
                strategies.append(("article_tag", article_content, len(article_content.split())))
        
        # Strategy 3: Main content area
        main = soup.find('main') or soup.find('[role="main"]')
        if main:
            main_content = main.get_text(separator=' ', strip=True)
            if main_content:
                strategies.append(("main_tag", main_content, len(main_content.split())))
        
        # Strategy 4: Common content selectors
        selectors = [
            '.post-content', '.entry-content', '.article-content', '.content',
            '.post-body', '.article-body', '.story-body', '.blog-content',
            '[class*="content"]', '[class*="article"]', '[class*="post"]',
            '.text', '.copy', '.editorial', '.story'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                temp_content = element.get_text(separator=' ', strip=True)
                if temp_content:
                    strategies.append((f"selector_{selector}", temp_content, len(temp_content.split())))
        
        # Strategy 5: Paragraph aggregation
        paragraphs = soup.find_all('p')
        if len(paragraphs) > 2:
            para_content = ' '.join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20)
            if para_content:
                strategies.append(("paragraph_aggregation", para_content, len(para_content.split())))
        
        # Strategy 6: Text nodes in common containers
        containers = soup.find_all(['div', 'section'], class_=re.compile(r'(content|article|post|story|body|text)', re.I))
        for container in containers:
            container_text = container.get_text(separator=' ', strip=True)
            if len(container_text) > 200:
                strategies.append(("container_text", container_text, len(container_text.split())))
        
        # Strategy 7: Aggressive fallback - get all text
        if not strategies:
            body = soup.find('body')
            if body:
                body_text = body.get_text(separator=' ', strip=True)
                strategies.append(("body_fallback", body_text, len(body_text.split())))
        
        # Choose the best strategy (most words)
        if strategies:
            strategies.sort(key=lambda x: x[2], reverse=True)  # Sort by word count
            extraction_method, content, word_count = strategies[0]
            print(f"DEBUG: Best strategy: {extraction_method} with {word_count} words")
            
            # Try other strategies if the best one is too short
            if word_count < 50 and len(strategies) > 1:
                for method, text, words in strategies[1:]:
                    if words > word_count:
                        extraction_method, content, word_count = method, text, words
                        print(f"DEBUG: Switched to: {extraction_method} with {word_count} words")
                        break
        
        # Clean content
        content = self._clean_extracted_content(content)
        final_word_count = len(content.split())
        success = len(content) >= 100 and final_word_count >= 20  # Very low threshold
        
        print(f"DEBUG: Final extraction - {final_word_count} words, {len(content)} chars, success: {success}")
        if not success:
            print(f"DEBUG: Content preview: '{content[:200]}...'")
        
        return BrowsedContent(
            url=url,
            title=title,
            content=content[:self.max_content_length],
            word_count=final_word_count,
            author=author,
            publish_date=publish_date,
            extraction_method=extraction_method,
            success=success,
            error_message="" if success else f"Insufficient content: {len(content)} chars, {final_word_count} words"
        )
    
    def _extract_from_json_ld(self, soup: BeautifulSoup) -> str:
        """Extract content from JSON-LD structured data"""
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                if script.string:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        data = data[0]
                    
                    if data.get('@type') in ['Article', 'NewsArticle', 'BlogPosting']:
                        content = data.get('articleBody', '')
                        if content and len(content) > 200:
                            print(f"DEBUG: JSON-LD found: {len(content)} chars")
                            return content
            except (json.JSONDecodeError, KeyError):
                continue
        
        return ""
    
    def _clean_soup(self, soup: BeautifulSoup):
        """Remove unwanted elements aggressively"""
        # Remove script, style, and other non-content elements
        for tag in soup(['script', 'style', 'noscript', 'iframe', 'embed', 'object', 'svg']):
            tag.decompose()
        
        # Remove navigation and UI elements
        noise_selectors = [
            'nav', 'header', 'footer', 'aside', 'form', 'button',
            '.navigation', '.nav', '.menu', '.sidebar', '.header', '.footer',
            '.advertisement', '.ad', '.ads', '.advert', '.banner',
            '.comments', '.comment', '.social-share', '.share', '.sharing',
            '.related', '.recommended', '.newsletter', '.popup', '.modal',
            '.cookie', '.gdpr', '.privacy', '.subscribe', '.signup',
            '[class*="ad-"]', '[id*="ad-"]', '[class*="social"]', '[class*="share"]',
            '[aria-label*="advertisement"]', '[aria-label*="banner"]'
        ]
        
        for selector in noise_selectors:
            for element in soup.select(selector):
                element.decompose()
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract title with multiple strategies"""
        selectors = [
            'h1.title', 'h1.article-title', 'h1.post-title', 'h1.entry-title',
            '.page-title h1', '.post-header h1', '.article-header h1',
            'h1', 'h2.title', '.title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                title = element.get_text(strip=True)
                if 5 < len(title) < 200:
                    return title
        
        # Fallback to <title> tag
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
            # Clean up title
            for separator in [' | ', ' - ', ' :: ', ' • ']:
                if separator in title:
                    title = title.split(separator)[0]
                    break
            return title
        
        return "Unknown Title"
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract author"""
        selectors = [
            '[rel="author"]', '.author-name', '.author', '.byline', 
            '.post-author', '.article-author', 'meta[name="author"]',
            '[class*="author"]', '[itemprop="author"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    author = element.get('content', '').strip()
                else:
                    author = element.get_text(strip=True)
                
                if author and 2 < len(author) < 100:
                    return author
        
        return ""
    
    def _extract_publish_date(self, soup: BeautifulSoup) -> str:
        """Extract publish date"""
        time_elem = soup.find('time')
        if time_elem and time_elem.get('datetime'):
            return time_elem['datetime']
        
        date_metas = soup.find_all('meta', attrs={'name': re.compile(r'date|time', re.I)})
        for meta in date_metas:
            if meta.get('content'):
                return meta['content']
        
        date_selectors = ['.publish-date', '.post-date', '.article-date', '.date']
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and len(text) < 50:
                    return text
        
        return ""
    
    def _clean_extracted_content(self, content: str) -> str:
        """Clean extracted content"""
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common patterns
        patterns = [
            r'Cookie Policy.*?(?=\w)', r'Privacy Policy.*?(?=\w)',
            r'Subscribe to.*?newsletter.*?(?=\w)', r'Follow us on.*?(?=\w)',
            r'Share this.*?(?=\w)', r'Related.*?(?=\w)',
            r'Advertisement.*?(?=\w)', r'Loading.*?(?=\w)',
            r'Continue reading.*?(?=\w)', r'Read more.*?(?=\w)',
            r'Skip to.*?(?=\w)', r'Jump to.*?(?=\w)'
        ]
        
        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Remove URLs and email addresses
        content = re.sub(r'http[s]?://\S+', '', content)
        content = re.sub(r'\S+@\S+\.\S+', '', content)
        
        # Remove excessive punctuation
        content = re.sub(r'[^\w\s.,!?;:\'"()-]', ' ', content)
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content


# Rest of the EnhancedPerplexityWebResearcher class remains the same as in the previous version
class EnhancedPerplexityWebResearcher:
    """Enhanced web research with URL browsing capabilities"""
    
    def __init__(self):
        self.api_key = os.getenv('PERPLEXITY_API_KEY')
        self.openai_client = openai.AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.url_browser = EnhancedURLBrowser()
        
        # Available models
        self.models = {
            "sonar": "sonar",
            "sonar-pro": "sonar-pro",
            "sonar-reasoning": "sonar-reasoning-pro"
        }

        # Default to sonar-reasoning-pro — benchmarks #1 for factual research
        # (statistically tied with Gemini 2.5 Pro Grounding, wins 53% head-to-head)
        # Cost: ~$5/M input, $8/M output — adds ~$0.14 per article vs sonar ($0.02)
        self.current_model = self.models["sonar-reasoning"]
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2
        
        if not self.api_key:
            logger.warning("PERPLEXITY_API_KEY not found in environment variables")
    
    def set_model(self, model_type: str = "sonar"):
        """Set the Sonar model to use"""
        if model_type in self.models:
            self.current_model = self.models[model_type]
            logger.info(f"Using Perplexity model: {model_type}")
        else:
            logger.warning(f"Unknown model type: {model_type}. Using default: sonar")
    
    async def deep_research_topic_with_browsing(self, topic: str, time_range: str = "6 months",
                                              max_articles: int = 8, max_urls_to_browse: int = 10,
                                              context: str = None) -> Dict:
        """
        Enhanced deep research with URL browsing.

        Parameters
        ----------
        topic           : Article topic
        time_range      : How far back to look (default "6 months")
        max_articles    : Unused (kept for API compat)
        max_urls_to_browse : How many URLs to actually browse
        context         : Optional research scope/angles to focus Perplexity queries
                          (e.g. "adversaries using AI in the cyber kill chain")
        """

        logger.info(f"Starting enhanced deep research on '{topic}' with URL browsing...")
        if context:
            logger.info(f"  Research context: {context[:120]}{'...' if len(context) > 120 else ''}")

        # Step 1: Get initial research with URLs
        print("Step 1: Conducting initial Perplexity research...")
        initial_research = await self.research_topic_comprehensive(topic, time_range, context=context)
        
        # Step 2: Extract and browse URLs from research
        print("Step 2: Extracting URLs from research data...")
        urls_with_metadata = self.url_browser.extract_prioritized_urls(initial_research)
        
        if not urls_with_metadata:
            print("WARNING: No URLs found for browsing, proceeding with basic research")
            return self.format_research_for_article_generation(initial_research)
        
        print(f"Step 3: Browsing top {max_urls_to_browse} URLs from {len(urls_with_metadata)} found...")
        
        # Step 3: Browse URLs for content
        browsed_contents = await self.url_browser.browse_urls(urls_with_metadata, max_urls_to_browse)
        
        if not browsed_contents:
            print("WARNING: No content extracted from URLs, using basic research")
            return self.format_research_for_article_generation(initial_research)
        
        print(f"Step 4: Successfully browsed {len(browsed_contents)} URLs")
        
        # Step 4: Analyze browsed content
        print("Step 5: Analyzing browsed content...")
        analyzed_contents = await self._analyze_browsed_content(browsed_contents, topic, context=context)

        # Step 5: Synthesize everything
        print("Step 6: Synthesizing enhanced research...")
        enhanced_synthesis = await self._synthesize_enhanced_research(
            initial_research, analyzed_contents, topic, context=context
        )
        
        # Step 6: Create comprehensive research data
        enhanced_research = {
            "topic": topic,
            "research_date": datetime.now().isoformat(),
            "research_type": "enhanced_deep_research_with_browsing",
            "research_context": context or "",
            "time_range": time_range,
            "model_used": self.current_model,
            "urls_found": len(urls_with_metadata),
            "urls_browsed": len(browsed_contents),
            "total_words_extracted": sum(content.word_count for content in browsed_contents),
            "initial_research": initial_research,
            "browsed_content": [
                {
                    "url": content.url,
                    "title": content.title,
                    "content_preview": content.content[:500],
                    "full_content": content.content,
                    "word_count": content.word_count,
                    "author": content.author,
                    "publish_date": content.publish_date,
                    "extraction_method": content.extraction_method
                }
                for content in browsed_contents
            ],
            "content_analysis": analyzed_contents,
            "enhanced_synthesis": enhanced_synthesis
        }
        
        # Save research
        self.save_research_data(enhanced_research, "enhanced_deep_research")
        
        return self.format_enhanced_research_for_generation(enhanced_research)
    
    async def _analyze_browsed_content(self, browsed_contents: List[BrowsedContent], topic: str,
                                        context: str = None) -> List[Dict]:
        """Analyze browsed content for insights, optionally focused by research context."""
        analyzed_contents = []

        context_instruction = (
            f"\nFocus your analysis specifically on content related to: {context}" if context else ""
        )

        for content in browsed_contents:
            if content.word_count < 20:  # Very low threshold
                continue

            logger.info(f"Analyzing content from {content.url[:50]}...")

            analysis_prompt = f"""Analyze this article content about "{topic}" and extract insights.{context_instruction}

ARTICLE CONTENT:
{content.content[:4000]}

Provide analysis in JSON format:
{{
  "main_insights": ["3-5 key insights from this article"],
  "unique_data": ["Specific statistics, numbers, or data points"],
  "expert_quotes": ["Notable quotes or expert opinions"],
  "methodologies": ["Approaches or frameworks mentioned"],
  "practical_applications": ["Actionable advice or real-world applications"],
  "credibility_score": "high|medium|low based on content quality",
  "content_type": "news|blog|research|academic|commercial"
}}"""
            
            try:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": analysis_prompt}],
                    max_tokens=1500,
                    temperature=0.1
                )
                
                analysis_text = response.choices[0].message.content.strip()
                
                # Clean JSON
                if analysis_text.startswith('```json'):
                    analysis_text = analysis_text.replace('```json', '').replace('```', '').strip()
                
                analysis_data = json.loads(analysis_text)
                analysis_data["source_url"] = content.url
                analysis_data["word_count"] = content.word_count
                
                analyzed_contents.append(analysis_data)
                logger.info(f"   Analysis complete")
                
            except Exception as e:
                logger.error(f"   Analysis failed: {str(e)}")
                continue
        
        return analyzed_contents
    
    async def _synthesize_enhanced_research(self, initial_research: Dict,
                                          analyzed_contents: List[Dict], topic: str,
                                          context: str = None) -> Dict:
        """Synthesize initial research with browsed content analysis."""

        logger.info("Synthesizing enhanced research findings...")

        # Combine insights from all sources
        all_insights = []
        all_data = []
        all_methodologies = []
        all_applications = []

        for analysis in analyzed_contents:
            all_insights.extend(analysis.get("main_insights", []))
            all_data.extend(analysis.get("unique_data", []))
            all_methodologies.extend(analysis.get("methodologies", []))
            all_applications.extend(analysis.get("practical_applications", []))

        context_line = (
            f"\nFocus the synthesis specifically on this angle: {context}\n" if context else ""
        )

        synthesis_prompt = f"""Synthesize comprehensive research about "{topic}" from multiple sources.{context_line}

INITIAL RESEARCH SUMMARY:
{initial_research.get('synthesis', {}).get('content', '')[:2000]}

INSIGHTS FROM BROWSED ARTICLES:
{all_insights[:15]}

UNIQUE DATA POINTS:
{all_data[:10]}

METHODOLOGIES:
{all_methodologies[:8]}

PRACTICAL APPLICATIONS:
{all_applications[:10]}

Create enhanced synthesis in JSON format:
{{
  "comprehensive_themes": ["5-7 main themes across all sources"],
  "evidence_based_findings": ["Key findings supported by multiple sources"],
  "novel_insights": ["Unique insights not commonly discussed"],
  "data_driven_points": ["Statistics and data with context"],
  "practical_framework": ["Synthesized actionable approach"],
  "content_gaps": ["Important gaps to address in new content"],
  "expert_perspectives": ["Key expert viewpoints and methodologies"],
  "implementation_strategies": ["How to practically apply the insights"],
  "future_considerations": ["Emerging trends and future directions"]
}}"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": synthesis_prompt}],
                max_tokens=2000,
                temperature=0.2
            )
            
            synthesis_text = response.choices[0].message.content.strip()
            
            if synthesis_text.startswith('```json'):
                synthesis_text = synthesis_text.replace('```json', '').replace('```', '').strip()
            
            synthesis_data = json.loads(synthesis_text)
            synthesis_data["synthesis_date"] = datetime.now().isoformat()
            synthesis_data["sources_analyzed"] = len(analyzed_contents)
            
            return synthesis_data
            
        except Exception as e:
            logger.error(f"Enhanced synthesis failed: {str(e)}")
            return {
                "comprehensive_themes": ["Current state analysis", "Best practices", "Implementation"],
                "synthesis_error": str(e),
                "sources_analyzed": len(analyzed_contents)
            }
    
    def format_enhanced_research_for_generation(self, research_data: Dict) -> Dict:
        """Format enhanced research for article generation"""
        
        enhanced_synthesis = research_data.get("enhanced_synthesis", {})
        browsed_content = research_data.get("browsed_content", [])
        content_analysis = research_data.get("content_analysis", [])
        
        # Extract high-quality insights
        all_insights = []
        all_data = []
        all_applications = []
        
        for analysis in content_analysis:
            if analysis.get("credibility_score") in ["high", "medium"]:
                all_insights.extend(analysis.get("main_insights", []))
                all_data.extend(analysis.get("unique_data", []))
                all_applications.extend(analysis.get("practical_applications", []))
        
        return {
            "web_research_enabled": True,
            "research_type": "enhanced_deep_research_with_browsing",
            "research_date": research_data.get("research_date"),
            "urls_analyzed": research_data.get("urls_browsed", 0),
            "total_words_browsed": research_data.get("total_words_extracted", 0),
            "comprehensive_themes": enhanced_synthesis.get("comprehensive_themes", []),
            "evidence_based_findings": enhanced_synthesis.get("evidence_based_findings", []),
            "novel_insights": enhanced_synthesis.get("novel_insights", []),
            "data_driven_points": enhanced_synthesis.get("data_driven_points", []),
            "practical_framework": enhanced_synthesis.get("practical_framework", []),
            "content_gaps": enhanced_synthesis.get("content_gaps", []),
            "expert_perspectives": enhanced_synthesis.get("expert_perspectives", []),
            "implementation_strategies": enhanced_synthesis.get("implementation_strategies", []),
            "browsed_insights": all_insights[:12],
            "unique_data_points": all_data[:8],
            "practical_applications": all_applications[:10],
            "research_summary": self._create_enhanced_research_summary(enhanced_synthesis, research_data),
            "browsed_sources": [
                {
                    "title": content.get("title", "Unknown"),
                    "url": content.get("url", ""),
                    "word_count": content.get("word_count", 0),
                    "author": content.get("author", ""),
                    "extraction_method": content.get("extraction_method", "")
                }
                for content in browsed_content[:6]
            ]
        }
    
    def _create_enhanced_research_summary(self, enhanced_synthesis: Dict, research_data: Dict) -> str:
        """Create comprehensive research summary"""
        
        summary_parts = []
        
        themes = enhanced_synthesis.get("comprehensive_themes", [])
        if themes:
            summary_parts.append(f"Themes: {', '.join(themes[:3])}")
        
        findings = enhanced_synthesis.get("evidence_based_findings", [])
        if findings:
            summary_parts.append(f"Key Findings: {'; '.join(findings[:2])}")
        
        novel = enhanced_synthesis.get("novel_insights", [])
        if novel:
            summary_parts.append(f"Novel Insights: {novel[0]}")
        
        urls_browsed = research_data.get("urls_browsed", 0)
        total_words = research_data.get("total_words_extracted", 0)
        
        summary_parts.append(f"Enhanced research: {urls_browsed} URLs browsed, {total_words} words analyzed")
        
        return " | ".join(summary_parts)
    
    # Keep existing methods for backward compatibility
    def _build_research_queries(self, topic: str, context: str = None, time_range: str = "6 months") -> tuple:
        """
        Build targeted research queries and synthesis query.

        If `context` is provided it is used to sharpen the queries so that
        Perplexity focuses on the exact angles and sub-topics the author cares
        about rather than generic coverage of the topic.

        Returns (research_queries: List[str], synthesis_query: str)
        """
        if context:
            # Context-aware queries — focus each query on a different facet of
            # the provided context so we get deep, targeted information.
            research_queries = [
                (
                    f"Research the following topic in depth: '{topic}'. "
                    f"Specifically focus on: {context}. "
                    f"Find recent authoritative sources from the past {time_range} covering these exact angles. "
                    f"Include complete URLs and links to original sources."
                ),
                (
                    f"What are the latest expert insights, real-world examples, and documented cases "
                    f"related to '{topic}' — specifically around: {context}? "
                    f"Provide URLs to studies, threat reports, and authoritative sources."
                ),
                (
                    f"Find specific technical details, statistics, attack patterns, methodologies, "
                    f"or frameworks related to '{topic}' with this focus: {context}. "
                    f"Include links to in-depth analyses, research papers, and industry reports."
                ),
                (
                    f"What are the most credible academic, government, and industry sources discussing "
                    f"'{topic}' with emphasis on: {context}? "
                    f"Provide specific URLs, publication names, and author details."
                ),
            ]
            synthesis_query = (
                f"Synthesize comprehensive research about '{topic}' with a specific focus on: {context}.\n\n"
                f"Structure your synthesis to cover:\n"
                f"1. Current expert consensus and key findings (with source URLs) directly related to {context}\n"
                f"2. Real-world documented examples, incidents, or case studies\n"
                f"3. Technical details, methodologies, and frameworks\n"
                f"4. Statistics and data points with citations\n"
                f"5. Knowledge gaps and emerging trends specific to this focus area\n\n"
                f"Please include all available complete URLs and links to authoritative sources."
            )
        else:
            # Generic queries — original behaviour
            research_queries = [
                f"Find recent authoritative articles about {topic} from the past {time_range}. Include complete URLs and links to original sources.",
                f"What are current expert insights and research findings related to {topic}? Provide URLs to studies and authoritative sources.",
                f"Identify emerging perspectives and industry reports on {topic}. Include links to in-depth analyses and research papers.",
                f"What are the most credible academic and industry sources discussing {topic}? Provide specific URLs and publication links.",
            ]
            synthesis_query = (
                f"Synthesize research about {topic} focusing on:\n"
                f"1. Current expert consensus and findings with complete source URLs\n"
                f"2. Advanced methodologies and frameworks with reference links\n"
                f"3. Evidence-based insights with citations and full URLs\n"
                f"4. Practical applications with reference links\n"
                f"5. Knowledge gaps and emerging considerations with source URLs\n\n"
                f"Please include all available complete URLs and links to authoritative sources in your response."
            )

        return research_queries, synthesis_query

    async def research_topic_comprehensive(self, topic: str, time_range: str = "6 months",
                                           context: str = None) -> Dict:
        """
        Comprehensive Perplexity research.

        Parameters
        ----------
        topic       : The article topic (e.g. "AI in cybersecurity")
        time_range  : How far back to search (default "6 months")
        context     : Optional free-text scope/angles to focus research on
                      (e.g. "adversaries using AI across the kill chain:
                       vulnerability scanning, exploit writing, C2 evasion")
        """

        logger.info(f"Conducting comprehensive research on '{topic}' using Perplexity...")
        if context:
            logger.info(f"  Research context: {context[:120]}{'...' if len(context) > 120 else ''}")

        research_queries, synthesis_query = self._build_research_queries(topic, context, time_range)

        research_results = {}

        for i, query in enumerate(research_queries, 1):
            logger.info(f"  Running query {i}/{len(research_queries)}...")
            result = await self._query_perplexity(query)
            research_results[f"query_{i}"] = {
                "question": query,
                "response": result.get("content", ""),
                "sources": result.get("sources", []),
                "timestamp": datetime.now().isoformat()
            }
            await asyncio.sleep(1)

        # Enhanced synthesis with URL focus
        logger.info("  Synthesizing findings...")
        synthesis = await self._query_perplexity(synthesis_query)
        
        return {
            "topic": topic,
            "research_context": context or "",
            "research_date": datetime.now().isoformat(),
            "time_range": time_range,
            "model_used": self.current_model,
            "research_type": "comprehensive",
            "individual_queries": research_results,
            "synthesis": {
                "content": synthesis.get("content", ""),
                "sources": synthesis.get("sources", [])
            },
            "total_sources": self._extract_unique_sources(research_results, synthesis)
        }

    async def _query_perplexity(self, query: str) -> Dict:
        """Query Perplexity API with enhanced URL extraction"""
        
        if not self.api_key:
            return {"content": "Error: No Perplexity API key configured", "sources": []}
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.current_model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are an expert research assistant. Always provide comprehensive information with proper citations and include all available complete URLs and links to original sources. When citing sources, include the full URL whenever possible and ensure URLs are complete and valid."
                },
                {
                    "role": "user", 
                    "content": query
                }
            ],
            "temperature": 0.1,
            "max_tokens": 4000
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                
                choices = data.get("choices", [])
                if choices and len(choices) > 0:
                    message = choices[0].get("message", {})
                    content = message.get("content", "")
                else:
                    content = data.get("content", str(data))
                
                # Extract citations with enhanced URL extraction
                citations = []
                if "citations" in data:
                    citations = data["citations"]
                elif "sources" in data:
                    citations = data["sources"]
                elif choices and "citations" in choices[0]:
                    citations = choices[0]["citations"]
                
                # Format sources with better URL handling
                sources = []
                if isinstance(citations, list):
                    for citation in citations:
                        if isinstance(citation, dict):
                            url = citation.get("url", "")
                            title = citation.get("title", "Unknown Title")
                            snippet = citation.get("text", citation.get("snippet", ""))
                            
                            # Only add if we have a valid URL
                            if url and url.startswith(('http://', 'https://')):
                                sources.append({
                                    "title": title,
                                    "url": url,
                                    "snippet": snippet[:300] + ("..." if len(snippet) > 300 else "")
                                })
                
                # Also extract URLs from content text as backup
                url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
                content_urls = re.findall(url_pattern, content)
                
                for url in content_urls:
                    # Add as source if not already included
                    if not any(source.get("url") == url for source in sources):
                        sources.append({
                            "title": "Source found in content",
                            "url": url,
                            "snippet": "Source found during research"
                        })
                
                print(f"DEBUG: Perplexity returned {len(sources)} sources with URLs")
                
                return {
                    "content": content,
                    "sources": sources,
                    "raw_response": data
                }
            else:
                error_msg = f"Perplexity API error: {response.status_code} - {response.text}"
                return {"content": f"Error: {error_msg}", "sources": []}
                
        except Exception as e:
            error_msg = f"Exception calling Perplexity API: {str(e)}"
            return {"content": f"Error: {error_msg}", "sources": []}
    
    def _extract_unique_sources(self, research_results: Dict, synthesis: Dict) -> List[Dict]:
        """Extract and deduplicate sources from all research queries"""
        
        all_sources = []
        
        for query_data in research_results.values():
            all_sources.extend(query_data.get("sources", []))
        
        all_sources.extend(synthesis.get("sources", []))
        
        unique_sources = {}
        for source in all_sources:
            url = source.get("url", "")
            if url and url not in unique_sources:
                unique_sources[url] = source
        
        return list(unique_sources.values())
    
    def save_research_data(self, research_data: Dict, research_type: str = "research", output_dir: str = "research_data") -> str:
        """Save research data to file"""
        
        Path(output_dir).mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_topic = "".join(c for c in research_data["topic"] if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_topic = clean_topic.replace(' ', '_')[:50]
        filename = f"{clean_topic}_{timestamp}_{research_type}.json"
        
        filepath = Path(output_dir) / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(research_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Research data saved: {filepath}")
        return str(filepath)
    
    def format_research_for_article_generation(self, research_data: Dict) -> Dict:
        """Format standard research data for article generation"""
        
        synthesis_content = research_data.get("synthesis", {}).get("content", "")
        total_sources = research_data.get("total_sources", [])
        
        return {
            "web_research_enabled": True,
            "research_date": research_data.get("research_date"),
            "sources_analyzed": len(total_sources),
            "web_sources_analyzed": total_sources[:10],
            "research_summary": synthesis_content,
            "research_insights": self._extract_insights(synthesis_content),
            "content_gaps": self._extract_content_gaps(synthesis_content),
            "unique_angles": self._extract_unique_angles(synthesis_content),
            "key_statistics": self._extract_statistics(synthesis_content),
            "recent_trends": self._extract_trends(synthesis_content)
        }
    
    # Legacy method for backward compatibility
    async def deep_research_topic(self, topic: str, time_range: str = "6 months", max_articles: int = 8) -> Dict:
        """Legacy deep research method - now enhanced with URL browsing"""
        return await self.deep_research_topic_with_browsing(
            topic, time_range, max_articles, max_urls_to_browse=max_articles
        )
    
    # Helper methods for backward compatibility
    def _extract_insights(self, content: str) -> List[str]:
        lines = content.split('\n')
        insights = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['insight:', 'key finding:', 'important:', 'notably:']):
                insights.append(line.strip())
        return insights[:5]
    
    def _extract_content_gaps(self, content: str) -> List[str]:
        gaps = []
        lines = content.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['gap:', 'missing:', 'lacking:', 'underexplored:']):
                gaps.append(line.strip())
        return gaps[:3]
    
    def _extract_unique_angles(self, content: str) -> List[str]:
        angles = []
        lines = content.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['angle:', 'perspective:', 'approach:', 'unique:']):
                angles.append(line.strip())
        return angles[:3]
    
    def _extract_statistics(self, content: str) -> List[str]:
        import re
        stats = []
        stat_patterns = [
            r'\d+\.?\d*%',
            r'\$\d+[.,]?\d*\s*(?:million|billion|thousand)?',
            r'\d+[.,]?\d*\s*(?:million|billion|thousand)',
        ]
        
        for pattern in stat_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            stats.extend(matches)
        
        return list(set(stats))[:5]
    
    def _extract_trends(self, content: str) -> List[str]:
        trends = []
        lines = content.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['trend:', 'trending:', 'emerging:', 'growing:']):
                trends.append(line.strip())
        return trends[:3]


# ── Gemini Research ────────────────────────────────────────────────────────────

class GeminiResearcher:
    """
    Research assistant powered by Google Gemini.

    Gemini excels at:
    - Deep synthesis of complex, multi-faceted topics
    - Technical depth (especially in cybersecurity, AI, engineering)
    - Connecting scattered facts across domains
    - Generating structured outlines and frameworks from raw knowledge

    Perplexity excels at:
    - Real-time web search with citations
    - Finding current news, reports, and recent publications
    - Returning source URLs for further browsing

    Best practice: use BOTH.  Run Perplexity first (real-time sources + URLs),
    then run Gemini on the same topic+context to get a deep synthesis layer.
    The two outputs are merged before article generation.

    Requires: GEMINI_API_KEY in .env
    Install:  pip install google-generativeai
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self._client = None
        self._model_name = "gemini-1.5-pro-latest"   # best for deep reasoning
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found — Gemini research disabled")

    def _get_client(self):
        """Lazy-init the Gemini client."""
        if self._client is None:
            try:
                import google.generativeai as genai  # type: ignore
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self._model_name)
            except ImportError:
                raise ImportError(
                    "google-generativeai not installed. "
                    "Run: pip install google-generativeai"
                )
        return self._client

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def research_topic(self, topic: str, context: str = None) -> Dict:
        """
        Deep-research a topic using Gemini.

        Returns a dict compatible with the format expected by
        `format_enhanced_research_for_generation` so it can be merged with
        Perplexity results or used standalone.
        """
        if not self.available:
            return {"gemini_available": False, "error": "GEMINI_API_KEY not set"}

        logger.info(f"[Gemini] Starting deep research on '{topic}'...")
        context_line = f"\n\nFocus specifically on: {context}" if context else ""

        prompt = f"""You are an expert research analyst. Conduct deep, structured research on the following topic and return your findings as a JSON object.

TOPIC: {topic}{context_line}

Return ONLY a valid JSON object (no markdown fences) with this exact structure:
{{
  "comprehensive_themes": ["5-7 major themes with detailed descriptions"],
  "evidence_based_findings": ["6-10 key findings with specifics — include data, events, or named tools/techniques"],
  "novel_insights": ["3-5 unique angles or lesser-known insights worth covering"],
  "data_driven_points": ["Specific statistics, percentages, or quantified facts (cite source or year where known)"],
  "practical_framework": ["4-6 actionable steps or a structured framework an audience can apply"],
  "expert_perspectives": ["Named experts, researchers, or organisations and their viewpoints"],
  "implementation_strategies": ["Concrete implementation steps or real-world applications"],
  "content_gaps": ["What most articles miss about this topic"],
  "real_world_examples": ["Named incidents, case studies, tools, or documented events with dates where possible"],
  "recommended_sections": ["Suggested H2 section headings for a high-quality article"]
}}

Be specific. Avoid vague generalisations. Include real names, dates, tool names, and documented incidents where possible."""

        try:
            model = self._get_client()
            # Run blocking call in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.2,
                        "max_output_tokens": 4096,
                    }
                )
            )
            raw = response.text.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw.strip())

            data = json.loads(raw)
            data["gemini_available"] = True
            data["model"] = self._model_name
            data["topic"] = topic
            data["research_context"] = context or ""
            data["research_date"] = datetime.now().isoformat()
            logger.info(f"[Gemini] Research complete — {len(data.get('evidence_based_findings', []))} findings")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"[Gemini] JSON parse error: {e}")
            return {"gemini_available": True, "error": f"JSON parse failed: {e}", "raw": raw[:500]}
        except Exception as e:
            logger.error(f"[Gemini] Research failed: {e}")
            return {"gemini_available": False, "error": str(e)}

    @staticmethod
    def merge_with_perplexity(perplexity_data: Dict, gemini_data: Dict) -> Dict:
        """
        Merge Gemini deep-research output into Perplexity-format research data.

        The merged dict is compatible with `format_enhanced_research_for_generation`
        and carries all the richer Gemini fields alongside Perplexity URL sources.
        """
        if not gemini_data.get("gemini_available"):
            return perplexity_data   # fall back to Perplexity-only

        merged = dict(perplexity_data)  # start with Perplexity base

        def _merge_list(key: str):
            existing = merged.get(key, [])
            new = gemini_data.get(key, [])
            combined = list(existing) + [x for x in new if x not in existing]
            merged[key] = combined

        for field in [
            "comprehensive_themes", "evidence_based_findings", "novel_insights",
            "data_driven_points", "practical_framework", "expert_perspectives",
            "implementation_strategies", "content_gaps",
        ]:
            _merge_list(field)

        # Gemini-only extras
        merged["real_world_examples"] = gemini_data.get("real_world_examples", [])
        merged["recommended_sections"] = gemini_data.get("recommended_sections", [])
        merged["gemini_enriched"] = True
        merged["gemini_model"] = gemini_data.get("model", "")

        logger.info(
            f"[Gemini] Merged into Perplexity data — "
            f"{len(merged.get('evidence_based_findings', []))} findings, "
            f"{len(merged.get('novel_insights', []))} novel insights"
        )
        return merged


# Test functions
async def test_enhanced_research():
    """Test the enhanced research with URL browsing"""
    
    researcher = EnhancedPerplexityWebResearcher()
    
    topic = input("Enter a topic for enhanced research: ").strip()
    if not topic:
        topic = "AI in cybersecurity"
    
    model_choice = input("Choose model (sonar/sonar-pro/sonar-reasoning, default=sonar): ").strip().lower()
    if model_choice in researcher.models:
        researcher.set_model(model_choice)
    
    max_urls = input("Max URLs to browse (default=10): ").strip()
    max_urls = int(max_urls) if max_urls.isdigit() else 10
    
    print(f"\nStarting enhanced research on: {topic}")
    print(f"Will browse up to {max_urls} URLs for content")
    
    # Conduct enhanced research with URL browsing
    research_data = await researcher.deep_research_topic_with_browsing(
        topic, max_urls_to_browse=max_urls
    )
    
    # Show results
    print(f"\nEnhanced Research Results:")
    print("-" * 50)
    print(f"URLs browsed: {research_data.get('urls_analyzed', 0)}")
    print(f"Words extracted: {research_data.get('total_words_browsed', 0)}")
    print(f"Comprehensive themes: {len(research_data.get('comprehensive_themes', []))}")
    print(f"Novel insights: {len(research_data.get('novel_insights', []))}")
    print(f"Data-driven points: {len(research_data.get('data_driven_points', []))}")
    
    if research_data.get('comprehensive_themes'):
        print(f"\nKey themes discovered:")
        for theme in research_data['comprehensive_themes'][:3]:
            print(f"• {theme}")
    
    if research_data.get('novel_insights'):
        print(f"\nNovel insights:")
        for insight in research_data['novel_insights'][:2]:
            print(f"• {insight}")


if __name__ == "__main__":
    import sys
    
    api_key = os.getenv('PERPLEXITY_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("Setup required:")
        print("1. Get API key from: https://www.perplexity.ai/settings/api")
        print("2. Add to .env file: PERPLEXITY_API_KEY=your_key_here")
        print("3. Also need OpenAI key: OPENAI_API_KEY=your_openai_key")
    elif not openai_key:
        print("OpenAI API key required for content analysis:")
        print("Add to .env file: OPENAI_API_KEY=your_openai_key")
    else:
        asyncio.run(test_enhanced_research())