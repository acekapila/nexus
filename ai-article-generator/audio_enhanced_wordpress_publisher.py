# audio_enhanced_wordpress_publisher.py - FIXED: Enhanced WordPress publisher with correct URL extraction
import os
import requests
from pathlib import Path
from typing import Dict, List
import mimetypes
# from wordpress_publisher import WordPressPublisher
from http.server import HTTPServer, BaseHTTPRequestHandler
import markdown

class WordPressPublisher:
    """WordPress publisher that handles separate title and content variables"""
    
    def __init__(self):
        self.client_id = os.getenv('WORDPRESS_CLIENT_ID')
        self.client_secret = os.getenv('WORDPRESS_CLIENT_SECRET')
        self.site_id = os.getenv('WORDPRESS_SITE_ID', '248582144')
        self.access_token = os.getenv('WORDPRESS_ACCESS_TOKEN')
        
        self.base_url = "https://public-api.wordpress.com/rest/v1.1"
        self.auth_url = "https://public-api.wordpress.com/oauth2/authorize"
        self.token_url = "https://public-api.wordpress.com/oauth2/token"
        
        self.redirect_uri = "http://localhost:8080/callback"
        
        # Check configuration
        self._check_configuration()
    
    def _check_configuration(self):
        """Check if WordPress.com is properly configured"""
        if self.access_token:
            print("✅ WordPress.com access token found")
        elif self.client_id and self.client_secret:
            print("⚠️ WordPress.com app configured but no access token")
            print("   Run setup to get access token")
        else:
            print("❌ WordPress.com not configured")
            print("   Need Client ID, Client Secret, and Access Token")
    
    def get_authorization_url(self):
        """Generate WordPress.com authorization URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'global'  # Full access scope
        }
        return f"{self.auth_url}?{urlencode(params)}"
    
    def exchange_code_for_token(self, authorization_code):
        """Exchange authorization code for access token"""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'code': authorization_code,
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=30)
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get('access_token')
                
                if access_token:
                    self.access_token = access_token
                    print(f"✅ Access token obtained!")
                    return access_token
                else:
                    print(f"❌ No access token in response: {token_data}")
                    return None
            else:
                print(f"❌ Token exchange failed: {response.status_code}")
                print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Token exchange error: {str(e)}")
            return None
    
    def test_api_access(self):
        """Test API access with current token"""
        if not self.access_token:
            return {"success": False, "error": "No access token"}
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Test getting site info
            response = requests.get(
                f"{self.base_url}/sites/{self.site_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                site_data = response.json()
                site_name = site_data.get('name', 'Unknown')
                can_publish = site_data.get('capabilities', {}).get('publish_post', False)
                
                print(f"✅ Connected to: {site_name}")
                print(f"📝 Can publish: {'Yes' if can_publish else 'No'}")
                
                return {
                    "success": True,
                    "site_name": site_name,
                    "can_publish": can_publish,
                    "site_data": site_data
                }
            else:
                error_msg = f"API test failed: {response.status_code} - {response.text}"
                print(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"API test exception: {str(e)}"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
    
    def _convert_markdown_to_html(self, markdown_content: str) -> str:
        """Convert markdown content to clean HTML for WordPress"""
        
        # Configure markdown with extensions for better HTML output
        md = markdown.Markdown(extensions=[
            'markdown.extensions.extra',      # Tables, footnotes, etc.
            'markdown.extensions.codehilite', # Code highlighting
            'markdown.extensions.toc',        # Table of contents
            'markdown.extensions.nl2br'      # Newline to <br>
        ])
        
        # Convert markdown to HTML
        html_content = md.convert(markdown_content)
        
        # Clean up the HTML for WordPress
        html_content = self._clean_html_for_wordpress(html_content)
        
        return html_content
    
    def _clean_html_for_wordpress(self, html_content: str) -> str:
        """Clean and optimize HTML for WordPress publishing"""
        
        # Replace markdown-style headers with proper HTML headers
        html_content = html_content.replace('<h1>', '<h2>')  # Convert h1 to h2 for blog posts
        
        # Ensure proper paragraph spacing
        html_content = html_content.replace('</p>\n<p>', '</p>\n\n<p>')
        
        # Clean up any remaining markdown artifacts
        html_content = html_content.replace('**', '').replace('__', '')
        
        # Ensure lists are properly formatted
        html_content = html_content.replace('<ul>\n<li>', '<ul>\n  <li>')
        html_content = html_content.replace('</li>\n<li>', '</li>\n  <li>')
        
        return html_content

    async def publish_article(self, article_data: Dict, status: str = "publish") -> Dict:
        """Publish article to WordPress.com using separate title and content variables"""
        
        if not self.access_token:
            return {"success": False, "error": "No access token configured"}
        
        print(f"📤 Publishing article to WordPress...")
        
        try:
            # Extract title and content as separate variables
            article_title = article_data.get('article_title') or article_data.get('unified_title') or article_data.get('title_options', ['Untitled'])[0]
            article_content = article_data.get('article_content', '')
            
            print(f"   📋 Title: {article_title}")
            print(f"   📝 Content length: {len(article_content)} characters")
            print(f"   📖 Content starts with: {article_content[:100]}...")
            
            # No title cleaning needed since content was generated without title
            excerpt = article_data.get('meta_description', '')
            
            # Convert markdown to HTML
            html_content = self._convert_markdown_to_html(article_content)
            
            # Prepare post data - title and content are completely separate
            post_data = {
                'title': article_title,        # Clean title variable
                'content': html_content,       # Clean content variable
                'excerpt': excerpt,
                'status': status,
                'type': 'post',
                'format': 'standard'
            }
            
            # Add categories and tags if available
            research_data = article_data.get('research_data', {})
            if 'categories' in research_data:
                post_data['categories'] = research_data['categories']
            
            # Add tags based on topic
            topic = article_data.get('topic', '')
            if topic:
                # Extract key words as tags
                topic_words = topic.replace(' ', ',').split(',')
                topic_tags = [word.strip().title() for word in topic_words if len(word.strip()) > 2]
                post_data['tags'] = ','.join(topic_tags[:5])  # Limit to 5 tags
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Debug: Show what we're sending to WordPress
            print(f"   🎯 WordPress Title: {article_title}")
            print(f"   📄 HTML Content length: {len(html_content)} characters")
            
            response = requests.post(
                f"{self.base_url}/sites/{self.site_id}/posts/new",
                headers=headers,
                json=post_data,
                timeout=60
            )
            
            if response.status_code == 200:
                post_response = response.json()
                post_id = post_response.get('ID')
                post_url = post_response.get('URL')
                
                print(f"   ✅ Article published successfully!")
                print(f"   🆔 Post ID: {post_id}")
                print(f"   🔗 URL: {post_url}")
                
                return {
                    "success": True,
                    "post_id": post_id,
                    "post_url": post_url,
                    "title_used": article_title,
                    "content_length": len(article_content),
                    "html_length": len(html_content),
                    "response": post_response
                }
            else:
                error_msg = f"WordPress API error: {response.status_code} - {response.text}"
                print(f"   ❌ Publishing failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"WordPress publishing exception: {str(e)}"
            print(f"   ❌ Publishing failed: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def create_social_media_post_with_link(self, article_data: Dict, post_url: str) -> Dict:
        """Create LinkedIn post content using separate title variable"""
        
        # Use the separate title variable
        title = article_data.get('article_title') or article_data.get('unified_title') or article_data.get('title_options', ['Untitled'])[0]
        excerpt = article_data.get('meta_description', '')[:150]
        topic = article_data.get('topic', '')
        
        # Create engaging LinkedIn post
        post_text = f"""New Article: {title}

{excerpt}

🔗 Read the full article: {post_url}

What's your experience with {topic.lower()}? Share your thoughts below!

#AI #Technology #Innovation #ProfessionalDevelopment"""
        
        return {
            "text": post_text,
            "article_url": post_url,
            "article_title": title,  # Include separate title for reference
            "call_to_action": f"Read more: {post_url}"
        }
    
    def save_publishing_log(self, article_data: Dict, wordpress_result: Dict, output_dir: str = "generated_articles"):
        """Save WordPress publishing log"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        topic = article_data.get("topic", "unknown")
        clean_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_topic = clean_topic.replace(' ', '_')[:40]
        
        log_data = {
            "article_info": {
                "topic": topic,
                "title": article_data.get('article_title') or article_data.get("unified_title", "Untitled"),
                "content_length": len(article_data.get('article_content', '')),
                "created_at": article_data.get("metrics", {}).get("created_at", datetime.now().isoformat())
            },
            "publishing_timestamp": datetime.now().isoformat(),
            "wordpress_result": wordpress_result,
            "site_id": self.site_id,
            "separate_title_content": True
        }
        
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(exist_ok=True)
        
        # Save log file
        log_file = Path(output_dir) / f"{clean_topic}_{timestamp}_wordpress_log.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        print(f"📋 WordPress publishing log saved: {log_file.name}")

class AudioEnhancedWordPressPublisher(WordPressPublisher):
    """Enhanced WordPress publisher that can upload and embed audio files"""
    
    async def upload_audio_file(self, audio_file_path: str, title: str) -> Dict:
        """Upload audio file to WordPress.com media library"""
        
        if not self.access_token:
            return {"success": False, "error": "No access token configured"}
        
        # Add basic file validation
        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            return {"success": False, "error": f"Audio file not found: {audio_file_path}"}
        
        try:
            # Get proper MIME type
            mime_type, _ = mimetypes.guess_type(str(audio_path))
            if not mime_type or not mime_type.startswith('audio/'):
                mime_type = 'audio/mpeg'  # Default for MP3
            
            print(f"   Uploading: {audio_path.name} ({mime_type})")
            
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'media[]': (os.path.basename(audio_file_path), audio_file, mime_type)
                }
                
                data = {
                    'title': f"Audio: {title}",
                    'description': f"Audio version of: {title}"
                }
                
                response = requests.post(
                    f"{self.base_url}/sites/{self.site_id}/media/new",
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=120  # Extended timeout for file upload
                )
            
            if response.status_code == 200:
                media_response = response.json()
                
                # FIXED: Handle the correct WordPress.com API response structure
                # The response has a 'media' array with media objects inside
                media_url = None
                media_id = None
                actual_mime_type = mime_type
                
                if 'media' in media_response and len(media_response['media']) > 0:
                    # Get the first (and usually only) media object
                    media_object = media_response['media'][0]
                    
                    # Try multiple possible URL field names within the media object
                    url_candidates = ['URL', 'url', 'source_url', 'link', 'guid']
                    
                    for field_name in url_candidates:
                        if field_name in media_object:
                            potential_url = media_object[field_name]
                            
                            # Handle nested objects (like guid.rendered)
                            if isinstance(potential_url, dict):
                                if 'rendered' in potential_url:
                                    potential_url = potential_url['rendered']
                            
                            # Validate it's a proper URL
                            if potential_url and isinstance(potential_url, str) and potential_url.startswith(('http://', 'https://')):
                                media_url = potential_url
                                print(f"   ✅ Found URL in field '{field_name}': {media_url}")
                                break
                    
                    # Extract other useful information
                    media_id = media_object.get('ID')
                    actual_mime_type = media_object.get('mime_type', mime_type)
                    
                else:
                    # Fallback: try direct response structure (in case API changes)
                    url_candidates = ['URL', 'url', 'source_url', 'link', 'guid']
                    
                    for field_name in url_candidates:
                        if field_name in media_response:
                            potential_url = media_response[field_name]
                            
                            # Handle nested objects (like guid.rendered)
                            if isinstance(potential_url, dict):
                                if 'rendered' in potential_url:
                                    potential_url = potential_url['rendered']
                            
                            # Validate it's a proper URL
                            if potential_url and isinstance(potential_url, str) and potential_url.startswith(('http://', 'https://')):
                                media_url = potential_url
                                print(f"   ✅ Found URL in fallback field '{field_name}': {media_url}")
                                break
                    
                    media_id = media_response.get('ID')
                    actual_mime_type = media_response.get('mime_type', mime_type)
                
                if not media_url:
                    # Debug: Show what we actually got
                    print(f"   ❌ No valid URL found in response")
                    print(f"   🔍 Response structure:")
                    if 'media' in media_response:
                        print(f"   📋 Media array length: {len(media_response['media'])}")
                        if len(media_response['media']) > 0:
                            print(f"   📋 First media object keys: {list(media_response['media'][0].keys())}")
                            for key in ['URL', 'url', 'source_url', 'link', 'guid']:
                                if key in media_response['media'][0]:
                                    print(f"   🔍 {key}: {media_response['media'][0][key]}")
                    else:
                        print(f"   📋 Direct response keys: {list(media_response.keys())}")
                        for key in ['URL', 'url', 'source_url', 'link', 'guid']:
                            if key in media_response:
                                print(f"   🔍 {key}: {media_response[key]}")
                    
                    return {"success": False, "error": "Upload succeeded but no valid URL found in response"}
                
                return {
                    "success": True,
                    "media_id": media_id,
                    "media_url": media_url,
                    "mime_type": actual_mime_type,
                    "media_response": media_response
                }
            else:
                error_msg = f"Audio upload failed: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('message', 'Unknown error')}"
                except:
                    error_msg += f" - {response.text[:200]}"
                
                print(f"   ❌ Upload failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"Audio upload exception: {str(e)}"
            print(f"   ❌ Upload exception: {error_msg}")
            return {"success": False, "error": error_msg}
    
    async def publish_article_with_audio(self, article_data: Dict, audio_files: List[str] = None, 
                                       status: str = "publish") -> Dict:
        """Publish article and embed audio players if audio files provided"""
        
        print("Publishing article with audio integration...")
        
        # Upload audio files first if provided
        uploaded_audio = []
        if audio_files:
            article_title = article_data.get('article_title', 'Untitled')
            
            for i, audio_file in enumerate(audio_files):
                if os.path.exists(audio_file):
                    print(f"   🔤 Uploading audio file {i+1}/{len(audio_files)}: {Path(audio_file).name}")
                    upload_result = await self.upload_audio_file(audio_file, f"{article_title} - Part {i+1}")
                    
                    if upload_result["success"]:
                        uploaded_audio.append(upload_result)
                        print(f"   ✅ Successfully uploaded: {upload_result['media_url']}")
                    else:
                        print(f"   ❌ Failed to upload {audio_file}: {upload_result.get('error')}")
        
        # Add audio player to content if audio was uploaded
        if uploaded_audio:
            original_content = article_data.get('article_content', '')
            audio_html = self._create_audio_player_html(uploaded_audio, article_data)
            
            # Create modified article data with audio player
            modified_article_data = article_data.copy()
            modified_article_data['article_content'] = audio_html + "\n\n" + original_content
            
            print(f"   🎵 Created audio player HTML with {len(uploaded_audio)} files")
        else:
            modified_article_data = article_data
            print("   ⚠️ No audio player added - no valid uploads")
        
        # Use existing publish_article method
        publish_result = await self.publish_article(modified_article_data, status)
        
        # Add audio info to result
        if publish_result["success"]:
            publish_result["audio_files_uploaded"] = len(uploaded_audio)
            publish_result["audio_urls"] = [audio["media_url"] for audio in uploaded_audio]
            publish_result["has_audio"] = len(uploaded_audio) > 0
        
        return publish_result
    
    def _create_audio_player_html(self, uploaded_audio: List[Dict], article_data: Dict) -> str:
        """Create HTML for embedded audio player"""
        
        if not uploaded_audio:
            return ""
        
        article_title = article_data.get('article_title', 'Article')
        
        if len(uploaded_audio) == 1:
            # Single audio file
            audio_url = uploaded_audio[0]["media_url"]
            mime_type = uploaded_audio[0].get("mime_type", "audio/mpeg")
            
            return f'''<div style="background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; text-align: center;">
<h3 style="margin-top: 0; color: #333;">🎧 Listen to This Article</h3>
<p style="color: #666; margin-bottom: 15px;">Prefer audio? Listen to "{article_title}" below:</p>
<figure class="wp-block-audio"><audio controls src="{audio_url}"></audio></figure>
<p style="margin-bottom: 0; font-size: 14px; color: #888;">Audio generated using AI voice synthesis</p>
</div>'''
        else:
            # Multiple audio files
            audio_players = []
            for i, audio in enumerate(uploaded_audio, 1):
                audio_url = audio["media_url"]
                mime_type = audio.get("mime_type", "audio/mpeg")
                
                audio_players.append(f'''<div style="margin: 15px 0; padding: 10px; background: white; border-radius: 5px;">
<strong>Part {i}:</strong>
<figure class="wp-block-audio"><audio controls src="{audio_url}"></audio></figure>
</div>''')
            
            download_links = []
            for i, audio in enumerate(uploaded_audio, 1):
                audio_url = audio["media_url"]
                download_links.append(f'<a href="{audio_url}" download style="color: #0073aa; text-decoration: none;">Part {i}</a>')
            
            return f'''<div style="background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px;">
<h3 style="margin-top: 0; color: #333; text-align: center;">🎧 Listen to This Article/Podcast</h3>
<p style="color: #666; margin-bottom: 15px; text-align: center;">This article/podcast is available in {len(uploaded_audio)} audio parts:</p>

{"".join(audio_players)}

<p style="margin-top: 20px; text-align: center; font-size: 14px;">
<strong>Download all parts:</strong> {" | ".join(download_links)}
</p>

<p style="margin-bottom: 0; font-size: 14px; color: #888; text-align: center;">Audio generated using AI voice synthesis</p>
</div>'''


# OAuth callback handler
class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/callback'):
            from urllib.parse import urlparse, parse_qs
            query = urlparse(self.path).query
            params = parse_qs(query)
            
            if 'code' in params:
                self.server.authorization_code = params['code'][0]
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                
                success_html = '''
                <html>
                <head><title>WordPress Authorization</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2 style="color: green;">Authorization Successful!</h2>
                <p>You can now close this window and return to the terminal.</p>
                <p>Your WordPress.com integration is ready!</p>
                <script>setTimeout(function() { window.close(); }, 3000);</script>
                </body>
                </html>
                '''
                self.wfile.write(success_html.encode('utf-8'))
            else:
                error = params.get('error', ['Unknown error'])[0]
                self.send_response(400)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                
                error_html = f'''
                <html>
                <head><title>WordPress Authorization Error</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2 style="color: red;">Authorization Failed</h2>
                <p><strong>Error:</strong> {error}</p>
                <p>Please return to the terminal and try again.</p>
                </body>
                </html>
                '''
                self.wfile.write(error_html.encode('utf-8'))
    
    def log_message(self, format, *args):
        return

def start_callback_server():
    """Start local server to handle OAuth callback"""
    try:
        server = HTTPServer(('localhost', 8080), CallbackHandler)
        server.authorization_code = None
        
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        print("✅ Local callback server started on http://localhost:8080")
        return server
    except Exception as e:
        print(f"❌ Could not start callback server: {str(e)}")
        return None

def setup_wordpress_credentials():
    """Interactive setup for WordPress.com credentials"""
    
    print("\n🔧 WordPress.com Setup")
    print("=" * 35)
    
    print("\nStep 1: Create WordPress.com App")
    print("1. Go to: https://developer.wordpress.com/apps/")
    print("2. Click 'Create New Application'")
    print("3. Fill in details:")
    print("   - Name: Article Generator")
    print("   - Description: Automated article publishing")
    print("   - Website URL: your site URL")
    print("   - Redirect URL: http://localhost:8080/callback")
    print("4. Save and copy Client ID and Client Secret")
    
    proceed = input("\nHave you created the WordPress.com app? (y/N): ").strip().lower()
    if proceed != 'y':
        print("\nPlease create the app first, then run setup again.")
        return
    
    client_id = input("\nEnter your WordPress.com Client ID: ").strip()
    if not client_id:
        print("❌ Client ID is required!")
        return
    
    client_secret = input("Enter your WordPress.com Client Secret: ").strip()
    if not client_secret:
        print("❌ Client Secret is required!")
        return
    
    site_id = input(f"Enter your Site ID (default: 248582144): ").strip()
    if not site_id:
        site_id = "248582144"
    
    # Initialize WordPress publisher
    wp_publisher = WordPressPublisher()
    wp_publisher.client_id = client_id
    wp_publisher.client_secret = client_secret
    wp_publisher.site_id = site_id
    
    print("\nStep 2: Get Access Token")
    
    # Start callback server
    server = start_callback_server()
    if not server:
        return
    
    # Generate and open authorization URL
    auth_url = wp_publisher.get_authorization_url()
    print(f"\n🌐 Opening WordPress.com authorization page...")
    
    try:
        webbrowser.open(auth_url)
        print("✅ Browser opened successfully")
    except Exception as e:
        print(f"❌ Could not open browser: {str(e)}")
        print(f"\nPlease manually open this URL:")
        print(f"{auth_url}")
    
    print("\n⏳ Waiting for authorization...")
    print("👆 Please authorize the app in your browser...")
    
    # Wait for callback
    timeout = 120
    start_time = time.time()
    
    while server.authorization_code is None and (time.time() - start_time) < timeout:
        elapsed = int(time.time() - start_time)
        remaining = timeout - elapsed
        print(f"\r⏳ Waiting... ({remaining}s remaining)", end="", flush=True)
        time.sleep(1)
    
    print()
    
    if server.authorization_code:
        print("✅ Authorization code received!")
        
        # Exchange code for token
        access_token = wp_publisher.exchange_code_for_token(server.authorization_code)
        
        if access_token:
            # Test API access
            test_result = wp_publisher.test_api_access()
            
            if test_result["success"]:
                # Save credentials
                save_wordpress_credentials(client_id, client_secret, site_id, access_token)
                print("\n🎉 WordPress.com setup complete!")
            else:
                print(f"❌ API test failed: {test_result.get('error')}")
        else:
            print("❌ Could not get access token")
    else:
        print("❌ Authorization timeout or failed")
    
    # Stop server
    try:
        server.shutdown()
    except:
        pass

def save_wordpress_credentials(client_id, client_secret, site_id, access_token):
    """Save WordPress.com credentials to .env file"""
    
    env_lines = []
    env_file_path = '.env'
    
    # Read existing .env
    try:
        with open(env_file_path, 'r') as f:
            env_lines = f.readlines()
    except FileNotFoundError:
        pass
    
    # Remove existing WordPress credentials
    env_lines = [line for line in env_lines if not line.startswith('WORDPRESS_')]
    
    # Add new credentials
    env_lines.append(f"\n# WordPress.com API Credentials\n")
    env_lines.append(f"WORDPRESS_CLIENT_ID={client_id}\n")
    env_lines.append(f"WORDPRESS_CLIENT_SECRET={client_secret}\n")
    env_lines.append(f"WORDPRESS_SITE_ID={site_id}\n")
    env_lines.append(f"WORDPRESS_ACCESS_TOKEN={access_token}\n")
    
    # Write .env file
    try:
        with open(env_file_path, 'w') as f:
            f.writelines(env_lines)
        
        print(f"✅ Credentials saved to .env file:")
        print(f"   🆔 Client ID: {client_id[:10]}...")
        print(f"   🔑 Access Token: {access_token[:20]}...")
        print(f"   🌐 Site ID: {site_id}")
    except Exception as e:
        print(f"❌ Could not save to .env file: {str(e)}")
        print(f"\nPlease manually add these to your .env file:")
        print(f"WORDPRESS_CLIENT_ID={client_id}")
        print(f"WORDPRESS_CLIENT_SECRET={client_secret}")
        print(f"WORDPRESS_SITE_ID={site_id}")
        print(f"WORDPRESS_ACCESS_TOKEN={access_token}")

# Example usage
async def test_wordpress_publishing():
    """Test WordPress.com publishing functionality with separate title/content"""
    
    wp_publisher = WordPressPublisher()
    
    # Test API access
    test_result = wp_publisher.test_api_access()
    if not test_result["success"]:
        print("❌ WordPress.com not properly configured")
        setup_choice = input("Run setup now? (y/N): ").strip().lower()
        if setup_choice == 'y':
            setup_wordpress_credentials()
        return
    
    # Create test article data with separate title and content
    test_article = {
        "topic": "Testing Separate Title/Content WordPress Integration",
        "article_title": "WordPress Integration with Separate Title and Content",
        "article_content": """In today's digital publishing landscape, separating content generation from title creation provides numerous advantages for automated publishing systems.

## Key Benefits of Separate Title/Content Approach

The separation of title and content variables eliminates the common problem of title duplication that plagues many automated publishing systems. When content is generated independently of titles, there's no risk of the title appearing within the article body.

## Technical Implementation

This approach uses distinct variables throughout the publishing pipeline. The article_title variable contains only the headline, while article_content contains the pure content without any title references.

## Publishing Workflow

WordPress receives these as completely separate inputs - one for the post title field and another for the post content field. This ensures clean presentation and eliminates any need for post-processing to remove duplicate titles.

## Quality Assurance Benefits

Quality control processes can focus on improving content without worrying about title conflicts. The title generation process can analyze the final content to create the most appropriate headline.

## Conclusion

This architectural approach provides a robust foundation for automated content publishing that maintains professional standards while eliminating common technical issues.""",
        "meta_description": "Testing WordPress publisher with separate title and content variables to eliminate duplication issues.",
        "metrics": {
            "created_at": datetime.now().isoformat()
        }
    }
    
    # Publish article
    result = await wp_publisher.publish_article(test_article, status="publish")
    
    if result["success"]:
        print(f"\n🎉 Test article published with separate title/content!")
        print(f"🔗 URL: {result['post_url']}")
        print(f"📋 Title used: {result['title_used']}")
        print(f"📝 Content length: {result['content_length']} characters")
        
        # Generate social media content
        social_content = wp_publisher.create_social_media_post_with_link(test_article, result['post_url'])
        print(f"\n📱 LinkedIn post content:")
        print(social_content['text'])
        
        # Save log
        wp_publisher.save_publishing_log(test_article, result)
    else:
        print(f"❌ Publishing failed: {result.get('error')}")

if __name__ == "__main__":
    choice = input("Setup WordPress.com credentials? (y/N): ").strip().lower()
    if choice == 'y':
        setup_wordpress_credentials()
    else:
        asyncio.run(test_wordpress_publishing())