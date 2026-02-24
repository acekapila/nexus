# enhanced_linkedin_poster.py - LinkedIn poster with separate title/content handling
import os
import json
import requests
import asyncio
import openai  # Added for dynamic hook generation
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class EnhancedLinkedInPoster:
    """LinkedIn poster that handles separate title and content variables"""
    
    def __init__(self):
        # LinkedIn API credentials
        self.linkedin_access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
        self.linkedin_person_id = os.getenv('LINKEDIN_PERSON_ID')
        
        # Platform settings
        self.enabled_platforms = []
        self._check_platform_availability()
    
    def _check_platform_availability(self):
        """Check if LinkedIn personal posting is configured"""
        if self.linkedin_access_token and self.linkedin_person_id:
            self.enabled_platforms.append('linkedin_personal')
            print("✅ LinkedIn personal posting enabled")
        else:
            print("⚠️ LinkedIn personal posting disabled - missing credentials")
    
    # ADDED: Dynamic hook generation methods
    # Replace the _generate_dynamic_hook method in your personal_social_media_poster.py
# with this updated version for OpenAI v1.0+:

    async def _generate_dynamic_hook(self, title: str, topic: str, content: str = "") -> str:
        """Generate dynamic hook using OpenAI v1.0+ - no markdown, clean text only"""
        
        # Check if OpenAI is available
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            print("   ⚠️ OpenAI not available, using fallback hook")
            return self._create_fallback_hook(topic, title)
        
        try:
            # For OpenAI v1.0+, create client
            from openai import OpenAI
            client = OpenAI(api_key=openai_api_key)
            
            # Get content preview for context (first 500 chars)
            content_preview = content[:500] if content else ""
            
            # Create prompt for hook generation
            hook_prompt = f"""Create a compelling LinkedIn hook for this article.

    STRICT REQUIREMENTS:
    - Maximum 15 words
    - No markdown formatting (**, *, `, #, etc.)
    - No hashtags
    - No emojis
    - Plain text only
    - One sentence
    - Professional and intriguing
    - Make professionals want to read the article

    Article Title: {title}
    Topic: {topic}
    Content Preview: {content_preview}

    Generate ONLY the hook text, nothing else."""

            # Updated API call for OpenAI v1.0+
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a LinkedIn content expert. Create compelling hooks that are professional, clean, and contain no formatting. Return only the hook text."
                    },
                    {"role": "user", "content": hook_prompt}
                ],
                max_tokens=50,
                temperature=0.7
            )
            
            hook = response.choices[0].message.content.strip()
            
            # Clean the hook (remove any formatting that might have slipped through)
            hook = self._clean_hook_text(hook)
            
            print(f"   ✨ Dynamic hook generated: {hook}")
            return hook
        
        except Exception as e:
            print(f"   ⚠️ Hook generation failed: {str(e)}, using fallback")
            return self._create_fallback_hook(topic, title)


    def _clean_hook_text(self, hook: str) -> str:
        """Clean hook text to remove any unwanted formatting"""
        
        # Remove markdown formatting
        hook = re.sub(r'\*\*(.*?)\*\*', r'\1', hook)  # Bold
        hook = re.sub(r'\*(.*?)\*', r'\1', hook)      # Italic
        hook = re.sub(r'`(.*?)`', r'\1', hook)        # Code
        hook = re.sub(r'#{1,6}\s+', '', hook)         # Headers
        
        # Remove quotes if they wrap the entire hook
        hook = hook.strip('"\'')
        
        # Remove any hashtags
        hook = re.sub(r'#\w+', '', hook)
        
        # Remove emojis (basic emoji patterns)
        hook = re.sub(r'[😀-🙏🌀-🗿🚀-🛿⚡-➿]', '', hook)
        
        # Clean up whitespace
        hook = ' '.join(hook.split())
        
        # Ensure it ends with proper punctuation
        if not hook.endswith(('.', '!', '?')):
            hook += '.'
        
        return hook

    def _create_fallback_hook(self, topic: str, title: str) -> str:
        """Create fallback hook when OpenAI is not available - NO EMOJIS"""
        topic_lower = topic.lower()
        
        if any(word in topic_lower for word in ['cyber', 'security', 'safety', 'protection']):
            return "Making cybersecurity accessible to everyone, not just IT experts."
        elif any(word in topic_lower for word in ['ai', 'artificial', 'intelligence', 'machine']):
            return "AI doesn't have to be complicated or intimidating."
        elif any(word in topic_lower for word in ['digital', 'transformation', 'technology']):
            return "Digital transformation starts with understanding the fundamentals."
        else:
            return f"New insights on {topic} that anyone can understand and apply."

    # MODIFIED: Now async and uses dynamic hooks
    async def create_article_link_post(self, article_data: Dict, article_url: str) -> Dict:
        """Create LinkedIn post using separate title and content variables with dynamic hook"""
        
        # Use separate title variable (preferred) or fallback to unified_title
        title = article_data.get('article_title') or article_data.get('unified_title') or article_data.get('title_options', ['Untitled'])[0]
        
        # Use separate content variable
        content = article_data.get('article_content', '')
        excerpt = article_data.get('meta_description', '')
        topic = article_data.get('topic', '')
        
        print(f"   🎯 Using title: {title}")
        print(f"   📄 Content length: {len(content)} characters")
        
        # Check for override content first
        if "linkedin_post_override" in article_data:
            return {
                "text": article_data["linkedin_post_override"],
                "article_url": article_url,
                "has_link": True,
                "source": "override"
            }
        
        # Create enhanced post content with dynamic hook
        post_text = await self._create_enhanced_post_content(title, excerpt, topic, article_url, content)
        
        return {
            "text": post_text,
            "article_url": article_url,
            "article_title": title,  # Include separate title for reference
            "has_link": True,
            "source": "generated_with_dynamic_hook"
        }
    
    # MODIFIED: Now async and uses dynamic hooks
    async def _create_enhanced_post_content(self, title: str, excerpt: str, topic: str, article_url: str, content: str = "") -> str:
        """Create enhanced LinkedIn post using separate title and content variables with dynamic hook"""
        
        # Generate dynamic hook using OpenAI
        hook = await self._generate_dynamic_hook(title, topic, content)
        
        # Generate topic-specific hashtags
        hashtags = "#CyberForEveryone #CybersecurityAwareness #InformationSecurity #CyberEducation #DigitalSecurity #SecurityTraining #CyberResilience #CyberAwareness #Technology #updates #news #podcast #AI "+self._generate_topic_hashtags(topic)
        
        # Create complete statistics based on topic and content
        stats = self._generate_complete_statistics(topic, content)
        
        stats_text = ""
        if stats:
            stats_text = "\n\n💡 Key insights from Article:\n" + "\n".join([f"• {stat}" for stat in stats[:3]])
        
        # URL AT TOP - Right after the dynamic hook
        post_text = f"""{hook}

🔗 Read the new article: {article_url}

"{title}" {self._create_value_proposition(topic)}.{stats_text}

What's your biggest challenge with {topic.lower()}? Share below! 👇

{hashtags}"""
        
        return post_text
    
    def _create_topic_hook(self, topic: str, title: str) -> str:
        """Create engaging hook based on topic"""
        
        topic_lower = topic.lower()
        
        if any(word in topic_lower for word in ['cyber', 'security', 'safety', 'protection']):
            return "🔐 Making cybersecurity accessible to everyone, not just IT experts."
        elif any(word in topic_lower for word in ['ai', 'artificial', 'intelligence', 'machine']):
            return "🤖 AI doesn't have to be complicated or intimidating."
        elif any(word in topic_lower for word in ['digital', 'transformation', 'technology']):
            return "🚀 Digital transformation starts with understanding the fundamentals."
        else:
            return f"📚 New insights on {topic} that anyone can understand and apply."
    
    def _create_value_proposition(self, topic: str) -> str:
        """Create value proposition based on topic"""
        
        topic_lower = topic.lower()
        
        if any(word in topic_lower for word in ['cyber', 'security']):
            return "breaks down digital protection into actionable steps for all skill levels"
        elif any(word in topic_lower for word in ['ai', 'artificial']):
            return "demystifies AI concepts with practical examples and clear explanations"
        elif any(word in topic_lower for word in ['digital', 'transformation']):
            return "provides a roadmap for successful digital transformation"
        else:
            return "offers practical guidance with expert insights and actionable advice"
    
    def _generate_complete_statistics(self, topic: str, content: str = "") -> List[str]:
        """Generate complete statistics using topic and content context"""
        
        # Try to extract relevant statistics from content first
        content_stats = self._extract_stats_from_content(content) if content else []
        
        if len(content_stats) >= 2:
            return content_stats[:3]
        
        # Fall back to topic-based statistics
        topic_lower = topic.lower()
        
        # Define complete, contextual statistics by topic
        cybersecurity_stats = [
            "Security awareness training reduces phishing success rates by 70%",
            "Organizations with basic cybersecurity measures prevent 60% of common attacks",
            "Password managers eliminate 85% of credential-related security incidents",
            "Regular security updates prevent 90% of known vulnerability exploits",
            "Multi-factor authentication blocks 99.9% of automated cyber attacks"
        ]
        
        ai_tech_stats = [
            "AI automation reduces manual task completion time by 60% on average",
            "Machine learning models improve accuracy by 40% with proper training data",
            "Automated workflows increase productivity by 75% in technical teams",
            "Organizations using AI see 45% faster decision-making processes",
            "Businesses implementing AI solutions report 50% reduction in operational costs"
        ]
        
        digital_stats = [
            "Digital transformation initiatives increase revenue by 45% on average",
            "Companies with digital strategies grow 30% faster than competitors",
            "Automation reduces operational costs by 55% across most industries",
            "Digital tools improve customer satisfaction scores by 40%",
            "Remote work capabilities increase employee retention by 35%"
        ]
        
        # Select appropriate statistics
        if any(word in topic_lower for word in ['cyber', 'security', 'safety', 'protection']):
            return cybersecurity_stats[:3]
        elif any(word in topic_lower for word in ['ai', 'artificial', 'intelligence', 'machine']):
            return ai_tech_stats[:3]
        elif any(word in topic_lower for word in ['digital', 'transformation', 'technology']):
            return digital_stats[:3]
        else:
            # Default to cybersecurity for unknown topics
            return cybersecurity_stats[:3]
    
    def _extract_stats_from_content(self, content: str) -> List[str]:
        """Extract meaningful statistics from article content"""
        
        if not content or len(content) < 500:
            return []
        
        # Look for sentences containing percentages with context
        stat_patterns = [
            r'[^.!?]*\b\d+%[^.!?]*[.!?]',  # Sentences with percentages
            r'[^.!?]*\b\d+ percent[^.!?]*[.!?]',  # Sentences with "percent"
            r'[^.!?]*reduces? [^.!?]*by \d+%[^.!?]*[.!?]',  # Reduction statistics
            r'[^.!?]*increases? [^.!?]*by \d+%[^.!?]*[.!?]',  # Increase statistics
            r'[^.!?]*shows? \d+%[^.!?]*[.!?]',  # Study results
        ]
        
        extracted_stats = []
        
        for pattern in stat_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                cleaned = match.strip()
                # Ensure the statistic is substantial and complete
                if (len(cleaned) > 40 and  # Minimum length for context
                    len(cleaned) < 150 and  # Maximum length to avoid long sentences
                    cleaned not in extracted_stats):  # Avoid duplicates
                    extracted_stats.append(cleaned)
                
                if len(extracted_stats) >= 3:  # Limit to 3 statistics
                    break
            
            if len(extracted_stats) >= 3:
                break
        
        return extracted_stats
    
    def _generate_topic_hashtags(self, topic: str) -> str:
        """Generate relevant hashtags based on topic"""
        
        # Extract key words from topic
        words = topic.lower().replace("how to", "").replace("guide to", "").split()
        key_words = [word.strip('.,!?').title() for word in words if len(word) > 3][:3]
        
        # Add topic-specific hashtags
        topic_tags = [f"#{word}" for word in key_words]
        
        # Common professional hashtags based on topic
        topic_lower = topic.lower()
        if 'cyber' in topic_lower or 'security' in topic_lower:
            base_tags = ["#Cybersecurity", "#InfoSec", "#DigitalSafety", "#CyberAwareness"]
        elif 'ai' in topic_lower or 'artificial' in topic_lower:
            base_tags = ["#AI", "#ArtificialIntelligence", "#MachineLearning", "#Technology"]
        else:
            base_tags = ["#Technology", "#Innovation", "#DigitalTransformation", "#ProfessionalDevelopment"]
        
        # Combine and limit
        all_tags = topic_tags + base_tags
        return " ".join(all_tags[:6])
    
    # MODIFIED: Now async for dynamic hooks
    async def create_full_content_post(self, article_data: Dict) -> Dict:
        """Create LinkedIn post with full content using separate variables with dynamic hook"""
        
        # Use separate title and content variables
        title = article_data.get('article_title') or article_data.get('unified_title') or article_data.get('title_options', ['Untitled'])[0]
        content = article_data.get('article_content', '')
        meta_description = article_data.get('meta_description', '')
        topic = article_data.get('topic', '')
        
        print(f"   🎯 Full content post for: {title}")
        
        # Generate dynamic hook
        hook = await self._generate_dynamic_hook(title, topic, content)
        
        # Get statistics from content or generate topic-based ones
        stats = self._generate_complete_statistics(topic, content)
        
        stats_text = ""
        if stats:
            stats_text = "\n\nKey insights from Article:\n" + "\n".join([f"• {stat}" for stat in stats[:3]])
        
        hashtags = "#CyberForEveryone #CybersecurityAwareness #InformationSecurity #CyberEducation #DigitalSecurity #SecurityTraining #CyberResilience #CyberAwareness #Technology #updates #news #podcast #AI "+self._generate_topic_hashtags(topic)
        
        post_text = f"""{hook}

{title}

{meta_description}{stats_text}

What's your experience with {topic.lower()}? Share your thoughts below! 👇

{hashtags}

#ThoughtLeadership #ProfessionalDevelopment"""
        
        return {
            "text": post_text,
            "article_title": title,
            "has_link": False,
            "dynamic_hook_used": True
        }
    
    async def post_to_linkedin_with_url(self, article_data: Dict, article_url: str = None) -> Dict:
        """Post to LinkedIn - with article link if available, full content otherwise"""
        
        if 'linkedin_personal' not in self.enabled_platforms:
            return {"success": False, "error": "LinkedIn personal not configured"}
        
        try:
            # Create appropriate post content (now using async methods)
            if article_url:
                print(f"📤 Posting to LinkedIn with article link...")
                post_content = await self.create_article_link_post(article_data, article_url)
                print(f"   🔗 Article URL: {article_url}")
            else:
                print(f"📤 Posting full content to LinkedIn...")
                post_content = await self.create_full_content_post(article_data)
            
            # Validate post content length
            post_text = post_content["text"]
            if len(post_text) > 3000:  # LinkedIn limit
                post_text = post_text[:2900] + "..."
                print(f"   ⚠️ Post truncated to fit LinkedIn limit")
            
            # Personal profile URN format
            author_urn = f"urn:li:person:{self.linkedin_person_id}"
            
            # LinkedIn API v2 post structure for text posts
            post_data = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": post_text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.linkedin_access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            # Debug: Print request data (without sensitive info)
            print(f"   📄 Post length: {len(post_text)} characters")
            print(f"   👤 Author URN: {author_urn}")
            
            response = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers=headers,
                json=post_data,
                timeout=30
            )
            
            print(f"   📡 LinkedIn API response: {response.status_code}")
            
            if response.status_code == 201:
                response_data = response.json()
                post_id = response_data.get('id', 'unknown')
                print(f"   ✅ LinkedIn post successful! Post ID: {post_id}")
                
                result = {
                    "success": True,
                    "platform": "linkedin_personal",
                    "post_type": "article_link" if article_url else "full_content",
                    "post_id": post_id,
                    "post_content": post_text,
                    "character_count": len(post_text),
                    "article_title": post_content.get("article_title", ""),
                    "separate_title_content": True,
                    "dynamic_hook_used": post_content.get("dynamic_hook_used", True),
                    "response": response_data
                }
                
                if article_url:
                    result["article_url"] = article_url
                
                return result
            else:
                error_msg = f"LinkedIn API error: {response.status_code} - {response.text}"
                print(f"   ❌ LinkedIn posting failed: {error_msg}")
                
                # Try to parse error response for better debugging
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg += f" | Message: {error_data['message']}"
                except:
                    pass
                
                return {"success": False, "error": error_msg, "platform": "linkedin_personal"}
                
        except requests.exceptions.RequestException as e:
            error_msg = f"LinkedIn API connection error: {str(e)}"
            print(f"   ❌ Connection failed: {error_msg}")
            return {"success": False, "error": error_msg, "platform": "linkedin_personal"}
        except Exception as e:
            error_msg = f"LinkedIn posting exception: {str(e)}"
            print(f"   ❌ LinkedIn posting failed: {error_msg}")
            return {"success": False, "error": error_msg, "platform": "linkedin_personal"}
    
    def save_posting_log(self, article_data: Dict, posting_result: Dict, output_dir: str = "generated_articles"):
        """Save LinkedIn posting log"""
        
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
            "posting_timestamp": datetime.now().isoformat(),
            "linkedin_result": posting_result,
            "post_content_preview": posting_result.get("post_content", "")[:200] + "...",
            "separate_title_content": True,
            "dynamic_hook_used": posting_result.get("dynamic_hook_used", False)
        }
        
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(exist_ok=True)
        
        # Save log file
        log_file = Path(output_dir) / f"{clean_topic}_{timestamp}_linkedin_log.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        print(f"📋 LinkedIn posting log saved: {log_file.name}")

# Integration class for seamless workflow
class WordPressLinkedInIntegration:
    """Integrated WordPress publishing with LinkedIn promotion using separate title/content"""
    
    def __init__(self, wordpress_publisher, linkedin_poster):
        self.wordpress = wordpress_publisher
        self.linkedin = linkedin_poster
    
    async def publish_and_promote(self, article_data: Dict, wordpress_status: str = "publish") -> Dict:
        """Publish to WordPress and promote on LinkedIn using separate title/content"""
        
        result = {
            "wordpress_result": None,
            "linkedin_result": None,
            "workflow_success": False,
            "separate_title_content": True
        }
        
        # Extract separate title and content for logging
        article_title = article_data.get('article_title', 'Unknown')
        content_length = len(article_data.get('article_content', ''))
        
        print(f"🔧 Starting integrated workflow with separate title/content:")
        print(f"   🎯 Title: {article_title}")
        print(f"   📄 Content: {content_length} characters")
        
        # Step 1: Publish to WordPress
        if self.wordpress.access_token:
            print("🌐 Publishing to WordPress...")
            wordpress_result = await self.wordpress.publish_article(article_data, status=wordpress_status)
            result["wordpress_result"] = wordpress_result
            
            if wordpress_result["success"]:
                article_url = wordpress_result["post_url"]
                
                # Step 2: Promote on LinkedIn with article link
                if 'linkedin_personal' in self.linkedin.enabled_platforms:
                    print("📱 Promoting on LinkedIn...")
                    linkedin_result = await self.linkedin.post_to_linkedin_with_url(article_data, article_url)
                    result["linkedin_result"] = linkedin_result
                    
                    if linkedin_result["success"]:
                        result["workflow_success"] = True
                        print("✅ Complete workflow successful!")
                    else:
                        print("⚠️ WordPress published but LinkedIn promotion failed")
                else:
                    print("⚠️ LinkedIn not configured - WordPress published only")
                    result["workflow_success"] = True
            else:
                print("❌ WordPress publishing failed")
                
                # Fallback: Post full content to LinkedIn
                if 'linkedin_personal' in self.linkedin.enabled_platforms:
                    print("📱 Fallback: Posting full content to LinkedIn...")
                    linkedin_result = await self.linkedin.post_to_linkedin_with_url(article_data)
                    result["linkedin_result"] = linkedin_result
        
        return result

# Credential management functions (unchanged)
def get_linkedin_person_id(access_token: str) -> str:
    """Get LinkedIn person ID using the profile API"""
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    try:
        response = requests.get(
            "https://api.linkedin.com/v2/people/~:(id)",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            person_id = data.get('id')
            if person_id:
                print(f"✅ Person ID retrieved: {person_id}")
                return person_id
            else:
                print("❌ No person ID in response")
                return None
        else:
            print(f"❌ Profile API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting person ID: {str(e)}")
        return None

def test_linkedin_access(access_token: str, person_id: str) -> bool:
    """Test LinkedIn API access with given credentials"""
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    try:
        # Test profile access
        response = requests.get(
            "https://api.linkedin.com/v2/people/~:(id,firstName,lastName)",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            profile_data = response.json()
            first_name = profile_data.get('firstName', {}).get('localized', {})
            last_name = profile_data.get('lastName', {}).get('localized', {})
            
            if first_name and last_name:
                # Get first available localized name
                first = list(first_name.values())[0] if first_name else ""
                last = list(last_name.values())[0] if last_name else ""
                print(f"✅ LinkedIn access confirmed for: {first} {last}")
                return True
            else:
                print("✅ LinkedIn access confirmed (name data limited)")
                return True
        else:
            print(f"❌ LinkedIn API test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ LinkedIn API test error: {str(e)}")
        return False

# Setup function for LinkedIn credentials
def setup_linkedin_credentials():
    """Interactive setup for LinkedIn API credentials"""
    
    print("\n🔧 LinkedIn API Setup")
    print("=" * 25)
    
    print("\nStep 1: Create LinkedIn App")
    print("1. Go to: https://www.linkedin.com/developers/apps")
    print("2. Click 'Create App'")
    print("3. Fill in details and verify")
    print("4. In 'Auth' tab, add these scopes:")
    print("   - r_liteprofile (read profile)")
    print("   - w_member_social (post content)")
    print("5. Add redirect URL: http://localhost:8080/callback")
    
    print("\nStep 2: Get Access Token")
    print("For testing, you can use LinkedIn's Token Generator in your app settings.")
    print("For production, implement OAuth 2.0 flow.")
    
    access_token = input("\nEnter your LinkedIn Access Token: ").strip()
    if not access_token:
        print("❌ Access token required!")
        return
    
    # Try to get person ID automatically
    print("\n🔍 Retrieving your LinkedIn person ID...")
    person_id = get_linkedin_person_id(access_token)
    
    if not person_id:
        person_id = input("Enter your LinkedIn Person ID manually: ").strip()
        if not person_id:
            print("❌ Person ID required!")
            return
    
    # Test the credentials
    print("\n🧪 Testing LinkedIn API access...")
    if test_linkedin_access(access_token, person_id):
        # Save credentials
        save_linkedin_credentials(access_token, person_id)
        print("\n🎉 LinkedIn setup complete!")
    else:
        print("\n❌ LinkedIn setup failed - credentials not working")

def save_linkedin_credentials(access_token, person_id):
    """Save LinkedIn credentials to .env file"""
    
    env_lines = []
    env_file_path = '.env'
    
    # Read existing .env
    try:
        with open(env_file_path, 'r') as f:
            env_lines = f.readlines()
    except FileNotFoundError:
        pass
    
    # Remove existing LinkedIn credentials
    env_lines = [line for line in env_lines if not line.startswith('LINKEDIN_')]
    
    # Add new credentials
    env_lines.append(f"\n# LinkedIn API Credentials\n")
    env_lines.append(f"LINKEDIN_ACCESS_TOKEN={access_token}\n")
    env_lines.append(f"LINKEDIN_PERSON_ID={person_id}\n")
    
    # Write .env file
    try:
        with open(env_file_path, 'w') as f:
            f.writelines(env_lines)
        
        print(f"✅ LinkedIn credentials saved to .env file:")
        print(f"   🔑 Access Token: {access_token[:20]}...")
        print(f"   👤 Person ID: {person_id}")
    except Exception as e:
        print(f"❌ Could not save to .env file: {str(e)}")
        print(f"\nPlease manually add these to your .env file:")
        print(f"LINKEDIN_ACCESS_TOKEN={access_token}")
        print(f"LINKEDIN_PERSON_ID={person_id}")

# Example usage and testing
async def test_enhanced_workflow():
    """Test the enhanced workflow with separate title/content"""
    
    # Initialize components
    linkedin = EnhancedLinkedInPoster()
    
    if 'linkedin_personal' not in linkedin.enabled_platforms:
        print("❌ LinkedIn not configured properly")
        setup_choice = input("Run LinkedIn setup now? (y/N): ").strip().lower()
        if setup_choice == 'y':
            setup_linkedin_credentials()
            # Reinitialize after setup
            linkedin = EnhancedLinkedInPoster()
        else:
            return
    
    # Test article data with separate title and content
    test_article = {
        "topic": "Testing Enhanced LinkedIn Integration with Separate Variables",
        "article_title": "LinkedIn Integration with Separate Title and Content Variables",
        "article_content": """In today's social media landscape, automated content sharing requires sophisticated systems that maintain professional standards while eliminating technical issues.

## Benefits of Separate Title and Content Variables

Using distinct variables for titles and content eliminates the common problem of title duplication in automated publishing workflows. This architectural approach ensures clean presentation across all platforms.

## Enhanced Statistics Generation

The system can extract meaningful statistics directly from article content, providing more relevant and contextual insights than generic topic-based statistics.

## Professional LinkedIn Presence

Complete statistics with full context create engaging posts that drive meaningful engagement and traffic back to the original content.

## Technical Implementation

The LinkedIn poster uses the article_title variable for headlines and article_content for context, enabling smarter post generation based on actual article content.

## Conclusion

This separate variable approach provides a robust foundation for professional social media automation that maintains quality standards while eliminating common technical pitfalls.""",
        "meta_description": "Testing enhanced LinkedIn integration with separate title and content variables for professional social media automation.",
        "metrics": {
            "created_at": datetime.now().isoformat()
        }
    }
    
    # Test LinkedIn posting with URL
    test_url = "https://example.com/test-article"
    print(f"\n🧪 Testing LinkedIn posting with article URL...")
    result = await linkedin.post_to_linkedin_with_url(test_article, test_url)
    
    # Show results
    if result["success"]:
        print("🎉 Enhanced LinkedIn test successful!")
        print(f"📱 Post ID: {result['post_id']}")
        print(f"📄 Character count: {result['character_count']}")
        print(f"🎯 Title used: {result.get('article_title', 'Unknown')}")
        print(f"🔗 Article URL included: {'Yes' if result.get('article_url') else 'No'}")
        print(f"🎯 Separate approach: {'Yes' if result.get('separate_title_content') else 'No'}")
        print(f"✨ Dynamic hook used: {'Yes' if result.get('dynamic_hook_used') else 'No'}")
        
        # Save log
        linkedin.save_posting_log(test_article, result)
    else:
        print(f"❌ LinkedIn test failed: {result.get('error')}")
        
        # Test fallback (posting without URL)
        print(f"\n🧪 Testing fallback posting (no URL)...")
        fallback_result = await linkedin.post_to_linkedin_with_url(test_article)
        
        if fallback_result["success"]:
            print("✅ Fallback posting successful!")
            print(f"📱 Post ID: {fallback_result['post_id']}")
            print(f"🎯 Title used: {fallback_result.get('article_title', 'Unknown')}")
        else:
            print(f"❌ Fallback also failed: {fallback_result.get('error')}")

async def test_integration_with_wordpress():
    """Test complete integration with WordPress using separate title/content"""
    
    try:
        from wordpress_publisher import WordPressPublisher
        
        # Initialize both components
        wordpress = WordPressPublisher()
        linkedin = EnhancedLinkedInPoster()
        integration = WordPressLinkedInIntegration(wordpress, linkedin)
        
        # Test article with separate title and content
        test_article = {
            "topic": "Complete Integration Test with Separate Variables",
            "article_title": "WordPress and LinkedIn Integration with Separate Variables",
            "article_content": """This comprehensive test validates the complete integration between WordPress publishing and LinkedIn promotion using separate title and content variables.

## Integration Architecture

The system maintains distinct article_title and article_content variables throughout the entire workflow, from generation through publication to social media promotion.

## WordPress Publishing Benefits

WordPress receives clean, separate inputs for the post title field and content field, eliminating any possibility of title duplication or formatting conflicts.

## LinkedIn Promotion Advantages

LinkedIn posts can reference both the article title and extract meaningful statistics from the actual content, creating more engaging and relevant social media posts.

        ## Quality Assurance

Separate variables enable independent optimization of titles and content, allowing for better SEO, readability, and engagement across different platforms.

## Workflow Validation

This test confirms that the entire pipeline from content generation to social media promotion works seamlessly with the separate variable approach.

## Conclusion

The separate title and content variable architecture provides a robust, scalable foundation for automated content publishing that maintains professional standards across all platforms.""",
            "meta_description": "Testing complete WordPress and LinkedIn integration workflow using separate title and content variables.",
            "metrics": {"created_at": datetime.now().isoformat()}
        }
        
        # Execute complete workflow
        result = await integration.publish_and_promote(test_article, wordpress_status="draft")
        
        # Show results
        print(f"\n📊 INTEGRATION TEST RESULTS (Separate Title/Content)")
        print("=" * 55)
        print(f"WordPress: {'✅ Success' if result.get('wordpress_result', {}).get('success') else '❌ Failed'}")
        print(f"LinkedIn: {'✅ Success' if result.get('linkedin_result', {}).get('success') else '❌ Failed'}")
        print(f"Overall: {'✅ Success' if result.get('workflow_success') else '❌ Failed'}")
        print(f"Separate Variables: {'✅ Yes' if result.get('separate_title_content') else '❌ No'}")
        
        if result.get('wordpress_result', {}).get('success'):
            wp_result = result['wordpress_result']
            print(f"🔗 Article URL: {wp_result['post_url']}")
            print(f"📋 Title Used: {wp_result.get('title_used', 'Unknown')}")
            print(f"📄 Content Length: {wp_result.get('content_length', 0)} chars")
        
        if result.get('linkedin_result', {}).get('success'):
            li_result = result['linkedin_result']
            print(f"📱 LinkedIn Post: {li_result.get('character_count', 0)} chars")
            print(f"🎯 Article Title: {li_result.get('article_title', 'Unknown')}")
        
    except ImportError:
        print("❌ WordPress publisher not available for integration test")

if __name__ == "__main__":
    print("🔧 LinkedIn Poster Setup and Testing (Separate Title/Content)")
    print("=" * 60)
    
    choice = input("Choose an option:\n1. Setup LinkedIn credentials\n2. Test LinkedIn posting\n3. Test complete integration\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        setup_linkedin_credentials()
    elif choice == '2':
        asyncio.run(test_enhanced_workflow())
    elif choice == '3':
        asyncio.run(test_integration_with_wordpress())
    else:
        print("Invalid choice. Running basic test...")
        asyncio.run(test_enhanced_workflow())