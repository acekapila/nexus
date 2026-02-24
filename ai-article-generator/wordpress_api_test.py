# wordpress_upload_test.py - Test audio upload and article creation
import os
import requests
import json
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

class WordPressUploadTester:
    """Test WordPress audio upload and article publishing"""
    
    def __init__(self):
        self.access_token = os.getenv('WORDPRESS_ACCESS_TOKEN')
        self.site_id = os.getenv('WORDPRESS_SITE_ID')
        self.base_url = "https://public-api.wordpress.com/rest/v1.1"
        
        if not self.access_token:
            raise ValueError("WORDPRESS_ACCESS_TOKEN required")
        if not self.site_id:
            raise ValueError("WORDPRESS_SITE_ID required")
    
    def upload_test_audio(self, audio_file_path: str) -> Dict:
        """Upload audio file and examine complete response"""
        print(f"🔤 Testing audio upload...")
        
        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            return {"success": False, "error": f"Audio file not found: {audio_file_path}"}
        
        print(f"   📁 File: {audio_path.name}")
        print(f"   📏 Size: {audio_path.stat().st_size} bytes")
        
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        try:
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'media[]': (audio_path.name, audio_file, 'audio/mpeg')
                }
                
                data = {
                    'title': f"Test Audio Upload - {audio_path.stem}",
                    'description': "Test audio upload for debugging"
                }
                
                # According to WordPress.com API docs, URL should be in format:
                # POST /rest/v1.1/sites/$site/media/new
                api_endpoint = f"{self.base_url}/sites/{self.site_id}/media/new"
                print(f"   📡 API Endpoint: {api_endpoint}")
                
                response = requests.post(
                    api_endpoint,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=120
                )
            
            print(f"   📡 HTTP Status: {response.status_code}")
            print(f"   📋 Response Headers: {dict(response.headers)}")
            
            # PRINT FULL RAW RESPONSE
            print("\n" + "="*60)
            print("🔍 FULL RAW RESPONSE:")
            print("="*60)
            try:
                raw_text = response.text
                print(f"Raw response length: {len(raw_text)} characters")
                print(f"Raw response content:\n{raw_text}")
                
                # Try to parse as JSON and pretty print
                if response.headers.get('content-type', '').startswith('application/json'):
                    media_response = response.json()
                    print("\n" + "-"*40)
                    print("📊 PARSED JSON (Pretty Printed):")
                    print("-"*40)
                    print(json.dumps(media_response, indent=2, ensure_ascii=False))
                else:
                    print("⚠️ Response is not JSON format")
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print(f"Raw response: {response.text[:1000]}...")
            
            print("="*60)
            
            if response.status_code == 200:
                media_response = response.json()
                print(f"   ✅ Upload successful!")
                
                # According to official WordPress.com API docs, response should include:
                # URL: Direct URL to uploaded file
                # ID: Media attachment ID
                # mime_type: File MIME type
                print(f"\n📋 RESPONSE ANALYSIS:")
                print(f"   📋 Response Keys: {list(media_response.keys())}")
                
                media_url = None
                
                # Check specifically for the documented URL field
                if 'URL' in media_response:
                    api_url = media_response['URL']
                    print(f"   🎯 Found 'URL' field: {api_url}")
                    
                    if api_url and api_url.startswith(('http://', 'https://')):
                        media_url = api_url
                        print(f"   ✅ Valid URL extracted from API response")
                    else:
                        print(f"   ❌ URL field exists but invalid: {api_url}")
                else:
                    print(f"   ❌ No 'URL' field in response (API docs say it should exist)")
                    
                    # Fallback: check other possible fields
                    fallback_fields = ['url', 'source_url', 'link', 'guid']
                    for field_name in fallback_fields:
                        if field_name in media_response:
                            potential_url = media_response[field_name]
                            
                            # Handle nested objects
                            if isinstance(potential_url, dict) and 'rendered' in potential_url:
                                potential_url = potential_url['rendered']
                            
                            print(f"   🔍 Checking fallback '{field_name}': {potential_url}")
                            
                            if potential_url and isinstance(potential_url, str) and potential_url.startswith(('http://', 'https://')):
                                media_url = potential_url
                                print(f"   ✅ Using fallback field '{field_name}' for URL")
                                break
                
                # Show key fields
                important_fields = ['ID', 'title', 'mime_type', 'date']
                for field in important_fields:
                    if field in media_response:
                        print(f"   📋 {field}: {media_response[field]}")
                
                if media_url:
                    # Test URL accessibility
                    print(f"\n🌐 Testing URL accessibility...")
                    try:
                        url_check = requests.head(media_url, timeout=10)
                        print(f"   📡 URL Response: {url_check.status_code}")
                        if url_check.status_code == 200:
                            print(f"   ✅ URL is accessible")
                        else:
                            print(f"   ⚠️ URL returned {url_check.status_code}")
                    except Exception as e:
                        print(f"   ❌ URL check failed: {str(e)}")
                    
                    return {
                        "success": True,
                        "media_id": media_response.get('ID'),
                        "media_url": media_url,
                        "mime_type": media_response.get('mime_type', 'audio/mpeg'),
                        "title": media_response.get('title', ''),
                        "response": media_response
                    }
                else:
                    print(f"   ❌ No valid URL found in response")
                    return {"success": False, "error": "No valid URL in response", "response": media_response}
                    
            else:
                error_msg = f"Upload failed: {response.status_code} - {response.text[:300]}"
                print(f"   ❌ {error_msg}")
                return {"success": False, "error": error_msg, "raw_response": response.text}
                
        except Exception as e:
            error_msg = f"Upload exception: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {"success": False, "error": error_msg}
    
    def create_test_article_with_audio(self, audio_upload_result: Dict) -> Dict:
        """Create a test article with embedded audio player"""
        print(f"\n📝 Creating test article with audio...")
        
        if not audio_upload_result["success"]:
            return {"success": False, "error": "No valid audio to embed"}
        
        # Create audio player HTML
        audio_url = audio_upload_result["media_url"]
        mime_type = audio_upload_result.get("mime_type", "audio/mpeg")
        
        audio_html = f'''<div style="background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; text-align: center;">
<h3 style="margin-top: 0; color: #333;">🎧 Listen to This Test Article</h3>
<p style="color: #666; margin-bottom: 15px;">Testing audio embedding with WordPress.com API:</p>

<audio controls preload="metadata" style="width: 100%; max-width: 600px;">
  <source src="{audio_url}" type="{mime_type}">
  <source src="{audio_url}" type="audio/mpeg">
  <source src="{audio_url}" type="audio/mp3">
  Your browser does not support the audio element. <a href="{audio_url}" target="_blank">Click here to download the audio file</a>.
</audio>

<p style="margin-top: 15px; font-size: 14px;">
<a href="{audio_url}" target="_blank" style="color: #0073aa; text-decoration: none;">🔗 Open audio in new tab</a> | 
<a href="{audio_url}" download style="color: #0073aa; text-decoration: none;">⬇️ Download audio file</a>
</p>

<p style="margin-bottom: 0; font-size: 14px; color: #888;">Audio generated using AI voice synthesis</p>
</div>'''
        
        # Create test article content
        article_content = audio_html + """

<h2>Test Article: WordPress Audio Integration</h2>

<p>This is a test article to verify that our WordPress.com API integration correctly uploads audio files and embeds them as playable audio elements.</p>

<h3>What We're Testing</h3>

<ul>
<li><strong>Audio Upload</strong>: Verifying files upload to WordPress media library</li>
<li><strong>URL Extraction</strong>: Ensuring we get proper URLs from the API response</li>
<li><strong>HTML Embedding</strong>: Testing that audio players render correctly</li>
<li><strong>Browser Compatibility</strong>: Multiple source formats for broad support</li>
</ul>

<h3>Expected Results</h3>

<p>If this test is successful, you should see a functional audio player above this content. The player should:</p>

<ol>
<li>Display standard browser audio controls</li>
<li>Play the uploaded audio file when clicked</li>
<li>Provide download and external link options</li>
<li>Gracefully handle browsers that don't support HTML5 audio</li>
</ol>

<p><em>This is a test post created automatically to verify WordPress.com audio integration.</em></p>
"""
        
        # Publish test article
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        post_data = {
            'title': f"Test: Audio Integration - {audio_upload_result['title']}",
            'content': article_content,
            'status': 'draft',  # Create as draft for testing
            'excerpt': 'Test article to verify WordPress audio embedding functionality'
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/sites/{self.site_id}/posts/new",
                headers=headers,
                json=post_data,
                timeout=60
            )
            
            print(f"   📡 Article Status: {response.status_code}")
            
            # PRINT FULL ARTICLE CREATION RESPONSE
            print("\n" + "="*60)
            print("🔍 FULL ARTICLE CREATION RESPONSE:")
            print("="*60)
            try:
                raw_text = response.text
                print(f"Raw response length: {len(raw_text)} characters")
                
                if response.headers.get('content-type', '').startswith('application/json'):
                    post_response = response.json()
                    print("📊 PARSED JSON (Pretty Printed):")
                    print("-"*40)
                    print(json.dumps(post_response, indent=2, ensure_ascii=False))
                else:
                    print("⚠️ Response is not JSON format")
                    print(f"Raw response: {raw_text}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print(f"Raw response: {response.text[:1000]}...")
            
            print("="*60)
            
            if response.status_code in [200, 201]:
                post_response = response.json()
                print(f"   ✅ Test article created!")
                print(f"   🔗 Article URL: {post_response.get('URL', 'N/A')}")
                print(f"   📝 Post ID: {post_response.get('ID', 'N/A')}")
                print(f"   📊 Status: {post_response.get('status', 'N/A')}")
                
                return {
                    "success": True,
                    "post_id": post_response.get('ID'),
                    "post_url": post_response.get('URL'),
                    "status": post_response.get('status'),
                    "audio_url": audio_url,
                    "response": post_response
                }
            else:
                error_msg = f"Article creation failed: {response.status_code} - {response.text[:300]}"
                print(f"   ❌ {error_msg}")
                return {"success": False, "error": error_msg, "raw_response": response.text}
                
        except Exception as e:
            error_msg = f"Article creation exception: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {"success": False, "error": error_msg}

def run_upload_test(audio_file_path: str):
    """Run complete upload and article creation test"""
    print("🧪 WordPress Audio Upload & Article Test")
    print("=" * 50)
    
    # Validate audio file path
    if not Path(audio_file_path).exists():
        print(f"❌ Audio file not found: {audio_file_path}")
        return
    
    try:
        tester = WordPressUploadTester()
        
        # Step 1: Upload audio file
        print("STEP 1: Upload Audio File")
        print("-" * 30)
        upload_result = tester.upload_test_audio(audio_file_path)
        
        if not upload_result["success"]:
            print(f"❌ Audio upload failed: {upload_result['error']}")
            if 'raw_response' in upload_result:
                print("Raw error response:")
                print(upload_result['raw_response'][:1000])
            return
        
        # Step 2: Create test article with audio
        print("\nSTEP 2: Create Test Article")
        print("-" * 30)
        article_result = tester.create_test_article_with_audio(upload_result)
        
        if article_result["success"]:
            print(f"\n🎉 SUCCESS! Complete test passed!")
            print(f"📁 Audio uploaded: {upload_result['media_url']}")
            print(f"📝 Test article created: {article_result['post_url']}")
            print(f"📊 Article status: {article_result['status']}")
            print(f"\n💡 Next Steps:")
            print(f"   1. Visit the article URL to verify audio player works")
            print(f"   2. Test audio playback in different browsers")
            print(f"   3. If successful, integrate the code into your main system")
        else:
            print(f"❌ Article creation failed: {article_result['error']}")
            print(f"   (But audio upload worked: {upload_result['media_url']})")
            if 'raw_response' in article_result:
                print("Raw error response:")
                print(article_result['raw_response'][:1000])
        
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Get audio file path from user
    audio_path = input("Enter path to audio file for testing: ").strip()
    
    if not audio_path:
        print("❌ Audio file path required")
    else:
        run_upload_test(audio_path)