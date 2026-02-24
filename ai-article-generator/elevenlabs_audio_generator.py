# hybrid_podcast_generator.py - OpenAI script generation + ElevenLabs audio
import os
import re
import asyncio
import openai
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    print("⚠️ ElevenLabs not installed. Run: pip install elevenlabs")


class HybridPodcastGenerator:
    """Generate conversational scripts with OpenAI, then create audio with ElevenLabs"""
    
    def __init__(self, voice_id: str = "JBFqnCBsd6RMkjVDRZzb"):
        # OpenAI setup for script generation
        self.openai_client = openai.AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.openai_available = bool(os.getenv('OPENAI_API_KEY'))
        
        # ElevenLabs setup for audio generation
        self.voice_id = voice_id
        self.voice_name = "george"
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_client = None
        self.elevenlabs_available = False
        
        if ELEVENLABS_AVAILABLE and self.elevenlabs_api_key:
            try:
                self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)
                self.elevenlabs_available = True
                print(f"🎤 ElevenLabs initialized with voice: {self.voice_name} ({self.voice_id})")
            except Exception as e:
                print(f"❌ ElevenLabs initialization failed: {str(e)}")
        
        # Overall availability
        self.available = self.openai_available and self.elevenlabs_available
        
        if not self.openai_available:
            print("⚠️ OpenAI not available - missing API key")
        if not self.elevenlabs_available:
            print("⚠️ ElevenLabs not available - missing API key or package")
        
        if self.available:
            print("✅ Hybrid podcast generator ready (OpenAI + ElevenLabs)")
    
    def _analyze_article_content(self, article_data: Dict) -> Dict:
        """Analyze article to extract key themes, insights, and discussion points"""
        
        title = article_data.get('article_title', 'Unknown Article')
        content = article_data.get('article_content', '')
        topic = article_data.get('topic', title)
        
        # Extract key sections from content
        sections = content.split('\n\n')
        main_points = []
        statistics = []
        practical_advice = []
        
        for section in sections:
            if section.strip():
                # Look for statistical information
                if re.search(r'\d+%|\d+ percent|statistics|data|research shows', section, re.IGNORECASE):
                    statistics.append(section.strip()[:200])
                
                # Look for practical advice or how-to content
                if re.search(r'how to|steps|should|must|important|essential|tips|advice', section, re.IGNORECASE):
                    practical_advice.append(section.strip()[:200])
                
                # General key points
                if len(section.split()) > 20:  # Substantial content
                    main_points.append(section.strip()[:200])
        
        return {
            "title": title,
            "topic": topic,
            "main_points": main_points[:5],  # Top 5 main points
            "statistics": statistics[:3],    # Top 3 statistics
            "practical_advice": practical_advice[:4],  # Top 4 practical tips
            "content_length": len(content),
            "estimated_complexity": "high" if len(content) > 2000 else "medium" if len(content) > 1000 else "low"
        }
    
    async def generate_conversational_podcast_script(self, article_data: Dict, 
                                                   podcast_style: str = "conversational",
                                                   target_duration: int = 10,
                                                   podcast_name: str = "Cyber For Everyone") -> Dict:
        """Generate conversational podcast script using OpenAI"""
        
        if not self.openai_available:
            return {"success": False, "error": "OpenAI not available"}
        
        print("🎙️ Generating conversational podcast script with OpenAI...")
        
        # Analyze the article content
        analysis = self._analyze_article_content(article_data)
        
        print(f"   📰 Article: {analysis['title']}")
        print(f"   🎯 Complexity: {analysis['estimated_complexity']}")
        print(f"   📊 Found {len(analysis['statistics'])} statistics")
        print(f"   💡 Found {len(analysis['practical_advice'])} practical tips")
        
        # Calculate target word count (roughly 160 words per minute)
        target_words = target_duration * 160
        
        # Create comprehensive prompt for conversational podcast
        podcast_prompt = f"""You are creating a conversational podcast script for "{podcast_name}" about the topic: {analysis['topic']}

ARTICLE ANALYSIS:
- Title: {analysis['title']}
- Main themes: {'; '.join(analysis['main_points'][:3])}
- Key statistics: {'; '.join(analysis['statistics'][:2])}
- Practical advice: {'; '.join(analysis['practical_advice'][:3])}

PODCAST REQUIREMENTS:
- Style: {podcast_style}, engaging, and educational
- Target length: {target_words} words (approximately {target_duration} minutes)
- Format: Single host discussing the topic conversationally
- Tone: Professional but accessible, like explaining to a friend

CONTENT INSTRUCTIONS:
1. Create a natural, flowing conversation - don't just read the article
2. Start with an engaging hook about why this topic matters
3. Discuss the key insights in a conversational way
4. Include personal observations and "what this means for you" moments
5. Use phrases like "Here's what's interesting...", "What I find fascinating is...", "The key takeaway here..."
6. Include practical, actionable advice that listeners can use
7. Share statistics in context, explaining what they actually mean
8. End with clear, memorable takeaways

SCRIPT STRUCTURE:
1. Engaging opening (why this topic matters right now)
2. Main discussion with 3-4 key insights
3. Practical application section
4. Clear, actionable conclusion

CRITICAL REQUIREMENTS:
- Write ONLY the spoken words (no stage directions, no speaker labels)
- Use conversational language with natural speech patterns
- Include transitions like "Now, here's what's really important..."
- Make it sound like a knowledgeable person explaining something interesting
- Keep sentences clear and not too complex for audio
- Aim for {target_words} words total
- Expand ALL contractions (don't → do not, we're → we are, etc.)

Generate the complete conversational podcast script:"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert podcast host who creates engaging, conversational content. You take article information and turn it into natural, flowing discussions that educate and engage listeners. You never just read content - you discuss it conversationally. Always expand contractions to full words."
                    },
                    {"role": "user", "content": podcast_prompt}
                ],
                max_tokens=4000,
                temperature=0.7
            )
            
            script = response.choices[0].message.content.strip()
            
            # Clean and validate the script for audio
            cleaned_script = self._clean_script_for_audio(script)
            word_count = len(cleaned_script.split())
            estimated_duration = word_count / 160  # 160 words per minute
            
            metadata = {
                "original_article_title": analysis['title'],
                "topic": analysis['topic'],
                "podcast_style": podcast_style,
                "target_duration_minutes": target_duration,
                "actual_duration_minutes": round(estimated_duration, 1),
                "word_count": word_count,
                "character_count": len(cleaned_script),
                "generated_at": datetime.now().isoformat(),
                "generation_method": "openai_conversational",
                "article_analysis": analysis
            }
            
            print(f"   ✅ Conversational script generated!")
            print(f"   📝 Words: {word_count} (target: {target_words})")
            print(f"   ⏱️ Duration: ~{round(estimated_duration, 1)} minutes")
            
            return {
                "success": True,
                "script": cleaned_script,
                "raw_script": script,
                "metadata": metadata,
                "word_count": word_count,
                "estimated_duration_minutes": round(estimated_duration, 1),
                "article_analysis": analysis
            }
            
        except Exception as e:
            print(f"   ❌ Script generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _clean_script_for_audio(self, script: str) -> str:
        """Clean script for optimal ElevenLabs audio generation"""
        
        # Remove any remaining stage directions or formatting
        script = re.sub(r'\[.*?\]', '', script)  # Remove [stage directions]
        script = re.sub(r'\*\*(.*?)\*\*', r'\1', script)  # Remove **bold**
        script = re.sub(r'\*(.*?)\*', r'\1', script)  # Remove *italic*
        script = re.sub(r'HOST:', '', script, flags=re.IGNORECASE)  # Remove speaker labels
        script = re.sub(r'PODCAST:', '', script, flags=re.IGNORECASE)
        
        # Expand contractions for better speech
        contractions = {
            "can't": "cannot", "won't": "will not", "don't": "do not", "didn't": "did not",
            "doesn't": "does not", "isn't": "is not", "aren't": "are not", "wasn't": "was not",
            "weren't": "were not", "haven't": "have not", "hasn't": "has not", "hadn't": "had not",
            "shouldn't": "should not", "wouldn't": "would not", "couldn't": "could not",
            "let's": "let us", "that's": "that is", "there's": "there is", "here's": "here is",
            "what's": "what is", "where's": "where is", "when's": "when is", "how's": "how is",
            "who's": "who is", "it's": "it is", "he's": "he is", "she's": "she is",
            "we're": "we are", "you're": "you are", "they're": "they are",
            "I'm": "I am", "I'll": "I will", "I'd": "I would", "I've": "I have",
            "you'll": "you will", "you'd": "you would", "you've": "you have",
            "we'll": "we will", "we'd": "we would", "we've": "we have",
            "they'll": "they will", "they'd": "they would", "they've": "they have"
        }
        
        for contraction, expansion in contractions.items():
            # Case-insensitive replacement with word boundaries
            pattern = r'\b' + re.escape(contraction) + r'\b'
            script = re.sub(pattern, expansion, script, flags=re.IGNORECASE)
        
        # Normalize whitespace and punctuation
        script = re.sub(r'\s+', ' ', script)
        script = re.sub(r'\.{2,}', '.', script)
        script = script.strip()
        
        return script
    
    async def generate_audio_from_script_elevenlabs(self, script: str, title: str = "Podcast Episode",
                                                  output_dir: str = "podcast_audio") -> Dict:
        """Generate audio from script using ElevenLabs"""
        
        if not self.elevenlabs_available:
            return {
                "success": False,
                "error": "ElevenLabs not available",
                "audio_files": []
            }
        
        print("🎵 Generating audio from script using ElevenLabs...")
        
        try:
            # Create output directory
            Path(output_dir).mkdir(exist_ok=True)
            
            # Generate filename
            title_slug = re.sub(r'[^\w\s-]', '', title).strip()
            title_slug = re.sub(r'[-\s]+', '-', title_slug).lower()[:50]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            audio_filename = f"{title_slug}_podcast_{timestamp}.mp3"
            audio_path = Path(output_dir) / audio_filename
            
            print(f"   🎤 Generating: {audio_filename}")
            print(f"   🎭 Voice: {self.voice_name}")
            print(f"   📝 Script length: {len(script)} characters")
            
            # Generate audio using ElevenLabs
            audio_generator = self.elevenlabs_client.text_to_speech.convert(
                text=script,
                voice_id=self.voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
                voice_settings=VoiceSettings(
                    stability=0.71,
                    similarity_boost=0.75,
                    style=0.0,
                    use_speaker_boost=True
                )
            )
            
            # Save audio file
            with open(audio_path, "wb") as f:
                for chunk in audio_generator:
                    f.write(chunk)
            
            # Calculate duration estimate
            word_count = len(script.split())
            estimated_duration = word_count / 160  # Words per minute
            
            # Create metadata
            audio_metadata = {
                "title": title,
                "voice_id": self.voice_id,
                "voice_name": self.voice_name,
                "model_id": "eleven_multilingual_v2",
                "generated_at": datetime.now().isoformat(),
                "script_length": len(script),
                "word_count": word_count,
                "estimated_duration_seconds": int(estimated_duration * 60),
                "estimated_duration_minutes": round(estimated_duration, 1),
                "audio_file": str(audio_path),
                "generation_method": "elevenlabs_tts"
            }
            
            # Save metadata
            metadata_path = Path(output_dir) / f"{title_slug}_metadata_{timestamp}.json"
            with open(metadata_path, "w", encoding='utf-8') as f:
                json.dump(audio_metadata, f, indent=2, ensure_ascii=False)
            
            print(f"   ✅ Audio generated successfully!")
            print(f"   📁 File: {audio_filename}")
            print(f"   ⏱️ Duration: ~{round(estimated_duration, 1)} minutes")
            
            return {
                "success": True,
                "audio_files": [str(audio_path)],
                "metadata_file": str(metadata_path),
                "metadata": audio_metadata,
                "estimated_duration_minutes": round(estimated_duration, 1),
                "word_count": word_count
            }
            
        except Exception as e:
            print(f"   ❌ Audio generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "audio_files": []
            }
    
    async def generate_podcast_from_article(self, article_data: Dict,
                                          podcast_style: str = "conversational",
                                          target_duration: int = 10,
                                          output_dir: str = "podcast_audio") -> Dict:
        """Complete workflow: Generate script with OpenAI, then audio with ElevenLabs"""
        
        print("🎬 Starting hybrid podcast generation (OpenAI + ElevenLabs)...")
        
        # Step 1: Generate conversational script with OpenAI
        script_result = await self.generate_conversational_podcast_script(
            article_data, podcast_style, target_duration
        )
        
        if not script_result["success"]:
            return script_result
        
        # Step 2: Generate audio from script with ElevenLabs
        title = article_data.get('article_title', 'Podcast Episode')
        audio_result = await self.generate_audio_from_script_elevenlabs(
            script_result["script"], title, output_dir
        )
        
        if not audio_result["success"]:
            return audio_result
        
        # Combine results
        combined_result = {
            "success": True,
            "script": script_result["script"],
            "audio_files": audio_result["audio_files"],
            "estimated_duration_minutes": audio_result["estimated_duration_minutes"],
            "word_count": script_result["word_count"],
            "script_metadata": script_result["metadata"],
            "audio_metadata": audio_result["metadata"],
            "article_analysis": script_result.get("article_analysis", {}),
            "generation_method": "hybrid_openai_elevenlabs"
        }
        
        print("🎉 Hybrid podcast generation successful!")
        print(f"   📝 Script: {script_result['word_count']} words (OpenAI)")
        print(f"   🎵 Audio: {len(audio_result['audio_files'])} file(s) (ElevenLabs)")
        print(f"   ⏱️ Duration: ~{audio_result['estimated_duration_minutes']} minutes")
        
        return combined_result


# Modified BlogAudioGenerator to use the hybrid approach
class BlogAudioGenerator:
    """Modified to use hybrid OpenAI + ElevenLabs approach"""
    
    def __init__(self, voice_id: str = None):
        # Initialize hybrid generator
        self.hybrid_generator = HybridPodcastGenerator(voice_id or "JBFqnCBsd6RMkjVDRZzb")
        self.available = self.hybrid_generator.available
        
        # Preserve original interface properties
        self.voice_id = voice_id or "JBFqnCBsd6RMkjVDRZzb"
        self.voice_name = "george"
        
        if self.available:
            print("🎤 Blog Audio Generator initialized with hybrid approach (OpenAI + ElevenLabs)")
        else:
            missing = []
            if not self.hybrid_generator.openai_available:
                missing.append("OpenAI API key")
            if not self.hybrid_generator.elevenlabs_available:
                missing.append("ElevenLabs API key/package")
            print(f"⚠️ Blog Audio Generator unavailable - missing: {', '.join(missing)}")
    
    def _create_audio_script(self, article_data: Dict) -> str:
        """Legacy method - now handled by OpenAI generator"""
        # This method is kept for interface compatibility but not used
        return ""
    
    async def generate_article_audio(self, article_data: Dict, 
                                   output_dir: str = "audio_output",
                                   model_id: str = None,
                                   output_format: str = None,
                                   target_duration_minutes: int = 10) -> Dict:
        """Generate conversational podcast using hybrid approach (preserves original interface)"""
        
        if not self.available:
            missing = []
            if not self.hybrid_generator.openai_available:
                missing.append("OpenAI")
            if not self.hybrid_generator.elevenlabs_available:
                missing.append("ElevenLabs")
            
            return {
                "success": False,
                "error": f"Hybrid generator not available - missing: {', '.join(missing)}",
                "audio_files": []
            }
        
        print("🎤 Generating conversational podcast with hybrid approach...")
        
        # Use hybrid generator
        result = await self.hybrid_generator.generate_podcast_from_article(
            article_data=article_data,
            podcast_style="conversational",
            target_duration=target_duration_minutes,
            output_dir=output_dir
        )
        
        if result["success"]:
            # Format response to match original interface
            return {
                "success": True,
                "audio_files": result["audio_files"],
                "metadata": result.get("audio_metadata", {}),
                "estimated_duration_minutes": result["estimated_duration_minutes"],
                "script_length": len(result.get("script", "")),
                "generation_method": "hybrid_openai_elevenlabs"
            }
        else:
            return result
    
    async def generate_audio_summary(self, article_data: Dict, 
                                   summary_length: str = "medium",
                                   output_dir: str = "audio_output") -> Dict:
        """Generate audio summary using hybrid approach"""
        
        if not self.available:
            return {"success": False, "error": "Hybrid generator not available"}
        
        print("🎤 Generating conversational summary with hybrid approach...")
        
        # Adjust target duration based on summary length
        duration_map = {"short": 3, "medium": 5, "long": 8}
        target_duration = duration_map.get(summary_length, 5)
        
        result = await self.hybrid_generator.generate_podcast_from_article(
            article_data=article_data,
            podcast_style="summary",
            target_duration=target_duration,
            output_dir=output_dir
        )
        
        if result["success"]:
            return {
                "success": True,
                "audio_file": result["audio_files"][0] if result["audio_files"] else "",
                "summary_text": result.get("script", ""),
                "summary_length": summary_length,
                "estimated_duration_minutes": result["estimated_duration_minutes"],
                "word_count": result["word_count"]
            }
        else:
            return result


# Test function
async def test_hybrid_podcast_generation():
    """Test the hybrid OpenAI + ElevenLabs podcast generation"""
    
    print("🧪 Testing Hybrid Podcast Generation (OpenAI + ElevenLabs)")
    print("=" * 65)
    
    # Sample article data
    test_article = {
        "article_title": "Essential Cybersecurity Practices for Small Businesses",
        "article_content": """Small businesses face increasing cybersecurity threats, with 43% of cyberattacks targeting small enterprises. Many lack dedicated IT security teams, making them vulnerable to various threats.

## Password Security Foundation

Strong password policies form the cornerstone of cybersecurity. Every account should have a unique, complex password containing at least 12 characters with a mix of letters, numbers, and symbols. Password managers can help generate and store these securely.

## Software Updates and Patch Management

Regular software updates are essential for security. Operating systems and applications should always be kept current with the latest security patches. Many attacks exploit known vulnerabilities in outdated software.

## Employee Training and Awareness

Employee training makes a significant difference in cybersecurity posture. Staff should learn to identify phishing emails, suspicious links, and social engineering attempts. They should understand the importance of reporting potential security incidents immediately.

## Backup and Recovery Systems

Having reliable backup systems is critical for business continuity. Important data should be backed up regularly using the 3-2-1 rule: three copies of data, stored on two different media types, with one copy stored offline.""",
        "topic": "cybersecurity for small businesses",
        "meta_description": "Essential cybersecurity practices that small businesses can implement to protect against increasing cyber threats."
    }
    
    # Test the hybrid generator directly
    generator = HybridPodcastGenerator()
    
    if not generator.available:
        print("❌ Hybrid generator not available - check API keys")
        print(f"   OpenAI: {'✅' if generator.openai_available else '❌'}")
        print(f"   ElevenLabs: {'✅' if generator.elevenlabs_available else '❌'}")
        return
    
    # Test complete workflow
    result = await generator.generate_podcast_from_article(
        test_article,
        podcast_style="conversational",
        target_duration=8
    )
    
    if result["success"]:
        print("\n✅ HYBRID PODCAST GENERATION SUCCESSFUL!")
        print(f"📝 Script words: {result['word_count']}")
        print(f"⏱️ Duration: ~{result['estimated_duration_minutes']} minutes")
        print(f"🎵 Audio files: {len(result['audio_files'])}")
        print(f"🔧 Method: {result['generation_method']}")
        
        # Show analysis results
        analysis = result.get("article_analysis", {})
        print(f"\n📊 ARTICLE ANALYSIS:")
        print(f"   📈 Complexity: {analysis.get('estimated_complexity', 'unknown')}")
        print(f"   📊 Statistics found: {len(analysis.get('statistics', []))}")
        print(f"   💡 Practical tips: {len(analysis.get('practical_advice', []))}")
        
        # Preview script (first 200 characters)
        script_preview = result["script"][:200]
        print(f"\n🎙️ SCRIPT PREVIEW:")
        print(f"   {script_preview}...")
        
    else:
        print(f"❌ Test failed: {result['error']}")
    
    print("\n" + "="*65)
    
    # Test modified BlogAudioGenerator interface
    print("🧪 Testing Modified BlogAudioGenerator Interface")
    
    blog_generator = BlogAudioGenerator()
    
    if blog_generator.available:
        legacy_result = await blog_generator.generate_article_audio(
            test_article, target_duration_minutes=6
        )
        
        if legacy_result["success"]:
            print("✅ Legacy interface working!")
            print(f"   🎵 Files: {len(legacy_result['audio_files'])}")
            print(f"   ⏱️ Duration: ~{legacy_result['estimated_duration_minutes']} minutes")
            print(f"   🔧 Method: {legacy_result.get('generation_method', 'unknown')}")
        else:
            print(f"❌ Legacy interface failed: {legacy_result['error']}")
    else:
        print("❌ BlogAudioGenerator not available")


if __name__ == "__main__":
    asyncio.run(test_hybrid_podcast_generation())