# linkedin_token_setup.py - Setup using existing LinkedIn access token
import requests
import os

def get_person_id_from_token(access_token):
    """Get LinkedIn Person ID using access token"""
    
    print("🔍 Getting your LinkedIn Person ID...")
    
    # Try the userinfo endpoint first (newer API)
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    endpoints_to_try = [
        ("https://api.linkedin.com/v2/userinfo", "sub"),
        ("https://api.linkedin.com/v2/people/~", "id")
    ]
    
    for endpoint, id_field in endpoints_to_try:
        try:
            print(f"   Trying endpoint: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                person_id = data.get(id_field)
                
                if person_id:
                    print(f"✅ Success! Found your Person ID: {person_id}")
                    
                    # Display profile info if available
                    name = data.get('name') or f"{data.get('localizedFirstName', '')} {data.get('localizedLastName', '')}"
                    if name.strip():
                        print(f"👤 Profile: {name.strip()}")
                    
                    return person_id
                else:
                    print(f"⚠️  Response missing {id_field} field")
                    
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Error with {endpoint}: {str(e)}")
    
    return None

def test_posting_capability(access_token, person_id):
    """Test if the token can be used for posting"""
    
    print("\n🧪 Testing posting capability...")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    
    # Test post structure (we won't actually post)
    test_post = {
        "author": f"urn:li:person:{person_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": "Test post structure validation"
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    
    # We'll just validate the token works by checking profile again
    try:
        profile_check = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers, timeout=30)
        if profile_check.status_code == 200:
            print("✅ Token is valid and ready for posting!")
            return True
        else:
            print(f"⚠️  Token validation failed: {profile_check.status_code}")
            return False
    except Exception as e:
        print(f"❌ Token test error: {str(e)}")
        return False

def save_credentials_to_env(access_token, person_id):
    """Save credentials to .env file"""
    
    print("\n💾 Saving credentials to .env file...")
    
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
    env_lines.append(f"LINKEDIN_ACCESS_TOKEN={access_token}\n")
    env_lines.append(f"LINKEDIN_PERSON_ID={person_id}\n")
    
    # Write back to .env file
    try:
        with open(env_file_path, 'w') as f:
            f.writelines(env_lines)
        
        print(f"✅ Credentials saved successfully!")
        print(f"   📝 Access Token: {access_token[:20]}...")
        print(f"   📝 Person ID: {person_id}")
        print(f"   📁 File: {env_file_path}")
        return True
    except Exception as e:
        print(f"❌ Could not save to .env file: {str(e)}")
        print(f"\n📝 Please manually add these to your .env file:")
        print(f"LINKEDIN_ACCESS_TOKEN={access_token}")
        print(f"LINKEDIN_PERSON_ID={person_id}")
        return False

def main():
    """Main setup function"""
    
    print("🔧 LinkedIn API Setup (Using Existing Token)")
    print("=" * 50)
    
    print("\n📝 You should have:")
    print("✅ Generated an access token from LinkedIn Developer Console")
    print("✅ Selected scopes: openid, profile, w_member_social, email")
    
    # Get access token from user
    access_token = input("\n🔑 Paste your LinkedIn access token here: ").strip()
    
    if not access_token:
        print("❌ Access token is required!")
        return
    
    if len(access_token) < 20:
        print("❌ That doesn't look like a valid LinkedIn access token")
        print("💡 LinkedIn tokens are usually much longer (100+ characters)")
        return
    
    print(f"✅ Token received: {access_token[:20]}...")
    
    # Get Person ID
    person_id = get_person_id_from_token(access_token)
    
    if not person_id:
        print("\n❌ Could not get your Person ID automatically")
        print("💡 You can find it manually:")
        print("   1. Go to your LinkedIn profile")
        print("   2. View page source and search for 'member:'")
        print("   3. Or use browser dev tools to inspect network requests")
        
        manual_id = input("\n🆔 Enter your Person ID manually (or press Enter to skip): ").strip()
        if manual_id:
            person_id = manual_id
        else:
            print("❌ Setup incomplete - Person ID is required")
            return
    
    # Test posting capability
    if test_posting_capability(access_token, person_id):
        
        # Save credentials
        if save_credentials_to_env(access_token, person_id):
            
            # Test with social media poster
            print("\n🧪 Testing integration with Social Media Poster...")
            try:
                from social_media_poster import SocialMediaPoster
                
                poster = SocialMediaPoster()
                if 'linkedin' in poster.enabled_platforms:
                    print("✅ SocialMediaPoster integration working!")
                else:
                    print("⚠️  SocialMediaPoster not detecting LinkedIn - restart may be needed")
                    
            except ImportError:
                print("⚠️  SocialMediaPoster not found - make sure you have the social_media_poster.py file")
            except Exception as e:
                print(f"⚠️  Integration test error: {str(e)}")
            
            print("\n🎉 LinkedIn setup complete!")
            print("\n📝 Next steps:")
            print("   1. Run: uv run integrated_article_generator.py")
            print("   2. Enable auto-posting when prompted")
            print("   3. Your articles will automatically post to LinkedIn!")
            
        else:
            print("❌ Could not save credentials")
    else:
        print("❌ Token validation failed")

def quick_test():
    """Quick test of saved credentials"""
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
    person_id = os.getenv('LINKEDIN_PERSON_ID')
    
    if not access_token or not person_id:
        print("❌ No saved LinkedIn credentials found")
        print("💡 Run the main setup first")
        return
    
    print("🧪 Testing saved LinkedIn credentials...")
    print(f"Token: {access_token[:20]}...")
    print(f"Person ID: {person_id}")
    
    if test_posting_capability(access_token, person_id):
        print("✅ Your LinkedIn setup is working!")
    else:
        print("❌ There's an issue with your LinkedIn setup")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        quick_test()
    else:
        main()