# linkedin_auth_helper.py - Helper script to get LinkedIn credentials
import requests
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import webbrowser  # Built into Python, no installation needed
import time

class LinkedInAuth:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = "http://localhost:8080/callback"
        self.authorization_code = None
        self.access_token = None
        self.person_id = None
        
    def get_authorization_url(self):
        """Generate LinkedIn authorization URL"""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'r_liteprofile w_member_social'  # Only basic scopes
        }
        
        base_url = "https://www.linkedin.com/oauth/v2/authorization"
        return f"{base_url}?{urllib.parse.urlencode(params)}"
    
    def exchange_code_for_token(self, authorization_code):
        """Exchange authorization code for access token"""
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        
        data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = requests.post(token_url, data=data, headers=headers, timeout=30)
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 'unknown')
                print(f"✅ Access token obtained!")
                print(f"🔑 Token expires in: {expires_in} seconds ({int(expires_in)//86400} days)" if expires_in != 'unknown' else "🔑 Token obtained!")
                return True
            else:
                print(f"❌ Token exchange failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Token exchange error: {str(e)}")
            return False
    
    def get_profile_info(self):
        """Get user profile information including person ID"""
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        profile_url = "https://api.linkedin.com/v2/people/~"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(profile_url, headers=headers, timeout=30)
            if response.status_code == 200:
                profile_data = response.json()
                self.person_id = profile_data.get('id')
                
                # Get name for confirmation
                first_name = profile_data.get('localizedFirstName', 'Unknown')
                last_name = profile_data.get('localizedLastName', 'Unknown')
                
                print(f"✅ Profile retrieved!")
                print(f"👤 Name: {first_name} {last_name}")
                print(f"🆔 Person ID: {self.person_id}")
                return True
            else:
                print(f"❌ Profile fetch failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Profile fetch error: {str(e)}")
            return False
    
    def test_posting_permission(self):
        """Test if we can post to LinkedIn"""
        if not self.access_token or not self.person_id:
            print("❌ Missing access token or person ID")
            return False
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        # Test by checking the profile again with posting headers
        try:
            profile_check = requests.get("https://api.linkedin.com/v2/people/~", headers=headers, timeout=30)
            if profile_check.status_code == 200:
                print("✅ LinkedIn API access confirmed!")
                print("✅ Ready for posting!")
                return True
            else:
                print(f"❌ API access test failed: {profile_check.status_code}")
                return False
        except Exception as e:
            print(f"❌ API test error: {str(e)}")
            return False

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/callback'):
            # Extract authorization code from URL
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            if 'code' in params:
                self.server.authorization_code = params['code'][0]
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                
                success_html = '''
                <html>
                <head><title>LinkedIn Authorization</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2 style="color: green;">Authorization Successful!</h2>
                <p>You can now close this window and return to the terminal.</p>
                <p>The setup process will continue automatically.</p>
                <script>
                setTimeout(function() {
                    window.close();
                }, 3000);
                </script>
                </body>
                </html>
                '''
                self.wfile.write(success_html.encode('utf-8'))
            else:
                # Handle error
                error = params.get('error', ['Unknown error'])[0]
                error_description = params.get('error_description', ['No details provided'])[0]
                self.send_response(400)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                
                error_html = f'''
                <html>
                <head><title>LinkedIn Authorization Error</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2 style="color: red;">Authorization Failed</h2>
                <p><strong>Error:</strong> {error}</p>
                <p><strong>Description:</strong> {error_description}</p>
                <p>Please return to the terminal and try again.</p>
                </body>
                </html>
                '''
                self.wfile.write(error_html.encode('utf-8'))
        else:
            # Handle other paths
            self.send_response(404)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            not_found_html = '<html><body><h2>404 - Not Found</h2></body></html>'
            self.wfile.write(not_found_html.encode('utf-8'))
    
    def log_message(self, format, *args):
        # Suppress default logging to keep output clean
        return

def start_callback_server():
    """Start local server to handle OAuth callback"""
    try:
        server = HTTPServer(('localhost', 8080), CallbackHandler)
        server.authorization_code = None
        
        # Start server in background thread
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        print("✅ Local callback server started on http://localhost:8080")
        return server
    except Exception as e:
        print(f"❌ Could not start callback server: {str(e)}")
        print("💡 Make sure port 8080 is not in use by another application")
        return None

def main():
    """Interactive LinkedIn setup process"""
    print("🔧 LinkedIn API Setup Helper")
    print("=" * 40)
    
    print("\n📋 Prerequisites:")
    print("1. You need a LinkedIn Developer account")
    print("2. You need to create a LinkedIn app")
    print("3. Your app should have OAuth redirect URI: http://localhost:8080/callback")
    
    print("\n📝 If you haven't created an app yet:")
    print("1. Go to https://developer.linkedin.com/")
    print("2. Click 'Create App'")
    print("3. Fill in app details and create it")
    print("4. In 'Auth' tab, add redirect URI: http://localhost:8080/callback")
    print("5. Add OAuth scopes: r_liteprofile, w_member_social (ONLY these two)")
    print("6. Note: Company page posting requires special approval from LinkedIn")
    
    proceed = input("\n✅ Do you have a LinkedIn app ready? (y/N): ").strip().lower()
    if proceed != 'y':
        print("\nPlease create your LinkedIn app first, then run this script again.")
        return
    
    print("\n📋 Step 1: Get your app credentials")
    print("Go to your LinkedIn app → 'Auth' tab → Copy Client ID and Client Secret")
    
    client_id = input("\n🔑 Enter your LinkedIn Client ID: ").strip()
    if not client_id:
        print("❌ Client ID is required!")
        return
    
    client_secret = input("🔐 Enter your LinkedIn Client Secret: ").strip()
    if not client_secret:
        print("❌ Client Secret is required!")
        return
    
    # Initialize LinkedIn auth
    linkedin_auth = LinkedInAuth(client_id, client_secret)
    
    print("\n📋 Step 2: Start authorization process")
    
    # Start callback server
    print("🌐 Starting local callback server...")
    server = start_callback_server()
    if not server:
        print("❌ Setup failed - could not start callback server")
        return
    
    # Generate and open authorization URL
    auth_url = linkedin_auth.get_authorization_url()
    print(f"\n🔗 Authorization URL generated")
    print("🌐 Opening LinkedIn authorization page in your browser...")
    
    try:
        webbrowser.open(auth_url)
        print("✅ Browser opened successfully")
    except Exception as e:
        print(f"❌ Could not open browser automatically: {str(e)}")
        print(f"\n🔗 Please manually open this URL in your browser:")
        print(f"{auth_url}")
    
    print("\n⏳ Waiting for authorization...")
    print("👆 Please complete the authorization in your browser...")
    print("   1. Review the permissions")
    print("   2. Click 'Allow' to authorize the app")
    print("   3. You'll be redirected back automatically")
    
    # Wait for callback with progress indicator
    timeout = 120  # 2 minutes timeout
    start_time = time.time()
    
    while server.authorization_code is None and (time.time() - start_time) < timeout:
        elapsed = int(time.time() - start_time)
        remaining = timeout - elapsed
        print(f"\r⏳ Waiting... ({remaining}s remaining)", end="", flush=True)
        time.sleep(1)
    
    print()  # New line after progress indicator
    
    if server.authorization_code:
        print("✅ Authorization code received!")
        
        # Exchange code for token
        print("\n📋 Step 3: Exchanging code for access token...")
        if linkedin_auth.exchange_code_for_token(server.authorization_code):
            
            # Get profile info
            print("\n📋 Step 4: Getting profile information...")
            if linkedin_auth.get_profile_info():
                
                # Test API access
                print("\n📋 Step 5: Testing API access...")
                if linkedin_auth.test_posting_permission():
                    
                    # Save credentials
                    print("\n📋 Step 6: Saving credentials...")
                    save_credentials(linkedin_auth)
                    
                    print("\n🎉 LinkedIn setup complete!")
                    print("✅ You can now use LinkedIn auto-posting!")
                    print("\n📝 Next steps:")
                    print("   1. Run: uv run integrated_article_generator.py")
                    print("   2. Enable auto-posting when prompted")
                    print("   3. Choose LinkedIn as your platform")
                else:
                    print("❌ API access test failed")
            else:
                print("❌ Could not get profile information")
        else:
            print("❌ Could not exchange authorization code for token")
    else:
        print("❌ Authorization timeout or failed")
        print("💡 Try again and make sure to complete the authorization in your browser")
    
    # Stop server
    try:
        server.shutdown()
        print("🔌 Callback server stopped")
    except:
        pass

def save_credentials(linkedin_auth):
    """Save LinkedIn credentials to .env file"""
    
    env_lines = []
    env_file_path = '.env'
    
    # Read existing .env file
    try:
        with open(env_file_path, 'r') as f:
            env_lines = f.readlines()
    except FileNotFoundError:
        print("📝 Creating new .env file...")
    
    # Remove existing LinkedIn credentials
    env_lines = [line for line in env_lines if not line.startswith('LINKEDIN_')]
    
    # Add new credentials
    if not any('LinkedIn API Credentials' in line for line in env_lines):
        env_lines.append(f"\n# LinkedIn API Credentials\n")
    env_lines.append(f"LINKEDIN_ACCESS_TOKEN={linkedin_auth.access_token}\n")
    env_lines.append(f"LINKEDIN_PERSON_ID={linkedin_auth.person_id}\n")
    
    # Write back to .env file
    try:
        with open(env_file_path, 'w') as f:
            f.writelines(env_lines)
        
        print(f"✅ Credentials saved to .env file:")
        print(f"   📝 Access Token: {linkedin_auth.access_token[:20]}...")
        print(f"   📝 Person ID: {linkedin_auth.person_id}")
        print(f"   📁 File location: {env_file_path}")
    except Exception as e:
        print(f"❌ Could not save to .env file: {str(e)}")
        print(f"\n📝 Please manually add these to your .env file:")
        print(f"LINKEDIN_ACCESS_TOKEN={linkedin_auth.access_token}")
        print(f"LINKEDIN_PERSON_ID={linkedin_auth.person_id}")

if __name__ == "__main__":
    main()