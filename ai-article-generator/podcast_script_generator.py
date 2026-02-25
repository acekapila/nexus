# improved_podcast_script_generator.py - Clean podcast scripts optimized for audio generation
import os
import re
import json
import asyncio
import openai
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class ImprovedPodcastScriptGenerator:
    """Generate clean podcast scripts optimized for audio generation"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
        
        self.openai_client = openai.AsyncOpenAI(api_key=self.api_key)
        
        # Common contractions to expand
        self.contractions = {
            "can't": "cannot",
            "won't": "will not",
            "don't": "do not",
            "didn't": "did not",
            "doesn't": "does not",
            "isn't": "is not",
            "aren't": "are not",
            "wasn't": "was not",
            "weren't": "were not",
            "haven't": "have not",
            "hasn't": "has not",
            "hadn't": "had not",
            "shouldn't": "should not",
            "wouldn't": "would not",
            "couldn't": "could not",
            "mustn't": "must not",
            "needn't": "need not",
            "daren't": "dare not",
            "mayn't": "may not",
            "might've": "might have",
            "should've": "should have",
            "would've": "would have",
            "could've": "could have",
            "must've": "must have",
            "let's": "let us",
            "that's": "that is",
            "there's": "there is",
            "here's": "here is",
            "what's": "what is",
            "where's": "where is",
            "when's": "when is",
            "how's": "how is",
            "who's": "who is",
            "it's": "it is",
            "he's": "he is",
            "she's": "she is",
            "we're": "we are",
            "you're": "you are",
            "they're": "they are",
            "I'm": "I am",
            "I'll": "I will",
            "I'd": "I would",
            "I've": "I have",
            "you'll": "you will",
            "you'd": "you would",
            "you've": "you have",
            "we'll": "we will",
            "we'd": "we would",
            "we've": "we have",
            "they'll": "they will",
            "they'd": "they would",
            "they've": "they have"
        }
    
    def _expand_contractions(self, text: str) -> str:
        """Expand contractions to full words for better audio generation"""
        for contraction, expansion in self.contractions.items():
            # Case-insensitive replacement with word boundaries
            pattern = r'\b' + re.escape(contraction) + r'\b'
            text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)
            
            # Handle capitalized versions
            if contraction[0].lower() != contraction[0]:  # If first letter should be capitalized
                capitalized = expansion.capitalize()
                cap_pattern = r'\b' + re.escape(contraction.capitalize()) + r'\b'
                text = re.sub(cap_pattern, capitalized, text)
        
        return text
    
    def _clean_script_for_audio(self, script: str) -> str:
        """Clean script to remove all non-speech content and optimize for audio"""
        
        # Remove all metadata headers and formatting
        lines = script.split('\n')
        clean_lines = []
        
        skip_patterns = [
            r'^={3,}',  # Separator lines
            r'^-{3,}',  # Dash lines
            r'^\*\*.*?\*\*:',  # Bold labels like **HOST:**
            r'^HOST:',  # HOST labels
            r'^PODCAST:',  # Podcast info
            r'^TOPIC:',  # Topic info
            r'^DURATION:',  # Duration info
            r'^WORD COUNT:',  # Word count
            r'^STYLE:',  # Style info
            r'^GENERATED:',  # Generated timestamp
            r'^\[.*?\]',  # Stage directions in brackets
            r'^Episode Title:',  # Episode title
            r'^Podcast Name:',  # Podcast name info
            r'^Host Name:',  # Host name info
            r'🎙️',  # Microphone emoji
            r'^\s*$'  # Empty lines
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip lines matching any skip pattern
            should_skip = False
            for pattern in skip_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    should_skip = True
                    break
            
            if should_skip:
                continue
            
            # Remove stage directions and formatting from remaining lines
            line = re.sub(r'\[.*?\]', '', line)  # Remove [stage directions]
            line = re.sub(r'\*\*(.*?)\*\*', r'\1', line)  # Remove **bold**
            line = re.sub(r'\*(.*?)\*', r'\1', line)  # Remove *italic*
            line = re.sub(r'^\w+:', '', line)  # Remove speaker labels like "HOST:"
            
            # Clean up extra whitespace
            line = re.sub(r'\s+', ' ', line).strip()
            
            if line and len(line) > 10:  # Only keep substantial content
                clean_lines.append(line)
        
        # Join all lines into continuous speech
        clean_script = ' '.join(clean_lines)
        
        # Expand contractions
        clean_script = self._expand_contractions(clean_script)
        
        # Additional cleaning
        clean_script = re.sub(r'\s+', ' ', clean_script)  # Normalize whitespace
        clean_script = re.sub(r'\.{2,}', '.', clean_script)  # Fix multiple periods
        clean_script = clean_script.strip()
        
        return clean_script
    
    def _validate_script_quality(self, script: str) -> Dict:
        """Validate script quality and identify potential issues"""
        
        issues = []
        warnings = []
        
        # Check for remaining contractions
        contraction_pattern = r"\b\w+'\w+\b"
        remaining_contractions = re.findall(contraction_pattern, script)
        if remaining_contractions:
            unique_contractions = list(set(remaining_contractions))
            if len(unique_contractions) > 3:  # Allow a few missed ones
                issues.append(f"Multiple contractions found: {unique_contractions[:5]}")
        
        # Check for metadata leakage
        metadata_patterns = [
            r'\bHOST\b', r'\bPODCAST\b', r'\bEPISODE\b', r'\bDURATION\b',
            r'\bWORD COUNT\b', r'\bGENERATED\b', r'\bSTYLE\b'
        ]
        for pattern in metadata_patterns:
            if re.search(pattern, script, re.IGNORECASE):
                issues.append(f"Metadata leakage detected: {pattern}")
        
        # Check for formatting artifacts
        if re.search(r'[=\-]{3,}', script):
            issues.append("Formatting artifacts (lines) found")
        
        if re.search(r'\[.*?\]', script):
            warnings.append("Stage directions still present")
        
        # Check script length
        word_count = len(script.split())
        if word_count < 50:
            issues.append("Script too short (less than 50 words)")
        elif word_count < 100:
            warnings.append("Script quite short (less than 100 words)")
        
        # Check for incomplete sentences
        sentences = re.split(r'[.!?]+', script)
        short_sentences = [s.strip() for s in sentences if 0 < len(s.strip().split()) < 3]
        if len(short_sentences) > 2:
            warnings.append(f"Multiple very short sentences: {short_sentences[:3]}")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "word_count": word_count,
            "character_count": len(script)
        }
    
    async def generate_clean_podcast_script(self, 
                                          article_data: Dict,
                                          podcast_style: str = "conversational",
                                          target_duration: int = 10,
                                          podcast_name: str = "Cyber For Everyone",
                                          host_name: str = None,
                                          max_retries: int = 3) -> Dict:
        """Generate a clean podcast script optimized for audio generation with validation"""
        
        print(f"🎙️ Generating clean podcast script...")
        print(f"   📰 Article: {article_data.get('article_title', 'Unknown')}")
        print(f"   🎭 Style: {podcast_style}")
        print(f"   ⏱️ Target: {target_duration} minutes")
        
        title = article_data.get('article_title', 'Unknown Article')
        content = article_data.get('article_content', '')
        topic = article_data.get('topic', title)
        
        # Clean content for processing
        clean_content = self._clean_article_content(content)
        target_words = target_duration * 160  # ~160 words per minute
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                print(f"   🔄 Attempt {retry_count + 1}/{max_retries}")
                
                # Generate script with strict instructions
                script_result = await self._generate_optimized_script(
                    title, clean_content, target_words, podcast_style, podcast_name, host_name
                )
                
                if not script_result["success"]:
                    retry_count += 1
                    continue
                
                raw_script = script_result["script"]
                
                # Clean the script for audio
                clean_script = self._clean_script_for_audio(raw_script)
                
                # Validate script quality
                validation = self._validate_script_quality(clean_script)
                
                print(f"   ✅ Validation: {'PASSED' if validation['is_valid'] else 'FAILED'}")
                if validation["issues"]:
                    print(f"   ❌ Issues: {validation['issues']}")
                if validation["warnings"]:
                    print(f"   ⚠️ Warnings: {validation['warnings']}")
                
                # If validation passes or we're on the last retry, use the result
                if validation["is_valid"] or retry_count == max_retries - 1:
                    estimated_duration = validation["word_count"] / 160
                    
                    metadata = {
                        "original_article_title": title,
                        "topic": topic,
                        "podcast_style": podcast_style,
                        "podcast_name": podcast_name,
                        "host_name": host_name or "Host",
                        "target_duration_minutes": target_duration,
                        "estimated_duration_minutes": round(estimated_duration, 1),
                        "word_count": validation["word_count"],
                        "character_count": validation["character_count"],
                        "generated_at": datetime.now().isoformat(),
                        "retries_used": retry_count + 1,
                        "validation_passed": validation["is_valid"],
                        "validation_issues": validation["issues"],
                        "validation_warnings": validation["warnings"]
                    }
                    
                    print(f"   ✅ Clean script generated!")
                    print(f"   📝 Words: {validation['word_count']}")
                    print(f"   ⏱️ Duration: ~{round(estimated_duration, 1)} minutes")
                    print(f"   🔄 Retries used: {retry_count + 1}")
                    
                    return {
                        "success": True,
                        "clean_script": clean_script,
                        "raw_script": raw_script,
                        "metadata": metadata,
                        "validation": validation,
                        "estimated_duration_minutes": round(estimated_duration, 1),
                        "word_count": validation["word_count"]
                    }
                
                else:
                    print(f"   🔄 Retrying due to validation issues...")
                    retry_count += 1
                    
            except Exception as e:
                print(f"   ❌ Attempt {retry_count + 1} failed: {str(e)}")
                retry_count += 1
        
        return {
            "success": False,
            "error": f"Failed to generate valid script after {max_retries} attempts"
        }
    
    def _clean_article_content(self, content: str) -> str:
        """Clean article content for script generation"""
        # Remove markdown formatting
        content = re.sub(r'#{1,6}\s+', '', content)
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
        content = re.sub(r'\*(.*?)\*', r'\1', content)
        content = re.sub(r'`(.*?)`', r'\1', content)
        content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
        
        # Remove links but keep text
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
        content = re.sub(r'http[s]?://[^\s]+', '', content)
        
        # Clean up formatting
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()
    
    async def _generate_optimized_script(self, title: str, content: str, target_words: int,
                                       podcast_style: str, podcast_name: str, host_name: str) -> Dict:
        """Generate script with specific instructions for audio optimization"""
        
        # Truncate content if too long — cut at word boundary to avoid broken words
        if len(content) > 3500:
            truncated = content[:3500]
            last_space = truncated.rfind(' ')
            content = (truncated[:last_space] if last_space > 0 else truncated) + "..."
        
        system_prompt = """You are an expert podcast script writer who creates scripts specifically optimized for text-to-speech audio generation. Your scripts must be completely clean and ready for direct audio conversion.

CRITICAL REQUIREMENTS FOR AUDIO OPTIMIZATION:
1. Write ONLY the spoken content - no labels, headers, metadata, or formatting
2. Use FULL WORDS ONLY - never use contractions (don't → do not, we're → we are, etc.)
3. Write in natural, conversational speech patterns
4. Use proper sentence structure with clear beginnings and endings
5. Include natural pauses through punctuation, not stage directions
6. Never include speaker labels like "HOST:" or "NARRATOR:"
7. Never include stage directions like [pause] or [music]
8. Never include metadata like podcast name, duration, or episode info
9. Write as one continuous speech flow
10. Use "and" instead of "&" or other symbols
11. Write in Australian English — use Australian spelling throughout (organisation, recognise, behaviour, colour, centre, programme, analyse, defence)
12. Never hyphenate or break words across lines — always write complete, unbroken words"""

        user_prompt = f"""Create a podcast script for text-to-speech generation:

TOPIC: {title}
CONTENT TO COVER: {content}
STYLE: {podcast_style} and engaging
LANGUAGE: Australian English — use Australian spelling throughout (organisation, recognise, behaviour, colour, centre)
TARGET LENGTH: {target_words} words (approximately {target_words // 160} minutes)
PODCAST: {podcast_name}

STRICT INSTRUCTIONS:
1. Write ONLY the actual spoken words - nothing else
2. Expand ALL contractions to full words (cannot, will not, we are, etc.)
3. Create a natural, flowing monologue
4. Start directly with content - no introductions about "Today we will discuss..."
5. Use proper punctuation for natural speech pauses
6. Never include any labels, headers, or metadata
7. Write as if you are speaking directly to listeners
8. Make it engaging but keep it conversational
9. End naturally without formal conclusions

Write the complete spoken script now:"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4000,
                temperature=0.6
            )
            
            script = response.choices[0].message.content.strip()
            
            return {
                "success": True,
                "script": script
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "script": ""
            }
    
    def save_clean_script(self, script_data: Dict, output_dir: str = "clean_podcast_scripts") -> Dict:
        """Save the clean script optimized for audio generation"""
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metadata = script_data.get("metadata", {})
        topic = metadata.get("original_article_title", "podcast_script")
        
        # Clean filename
        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_topic = safe_topic.replace(' ', '_')[:40]
        
        # Save clean script (audio-ready)
        clean_script_filename = f"{safe_topic}_clean_audio_{timestamp}.txt"
        clean_script_file = output_path / clean_script_filename
        
        with open(clean_script_file, 'w', encoding='utf-8') as f:
            f.write(script_data.get("clean_script", ""))
        
        # Save raw script (with formatting) for reference
        raw_script_filename = f"{safe_topic}_raw_script_{timestamp}.txt"
        raw_script_file = output_path / raw_script_filename
        
        with open(raw_script_file, 'w', encoding='utf-8') as f:
            f.write("ORIGINAL GENERATED SCRIPT (with formatting):\n")
            f.write("=" * 50 + "\n")
            f.write(script_data.get("raw_script", ""))
        
        # Save metadata
        metadata_filename = f"{safe_topic}_metadata_{timestamp}.json"
        metadata_file = output_path / metadata_filename
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)
        
        print(f"   💾 Files saved:")
        print(f"      🎤 Audio-ready: {clean_script_filename}")
        print(f"      📝 Raw script: {raw_script_filename}")
        print(f"      📊 Metadata: {metadata_filename}")
        
        return {
            "clean_script_file": str(clean_script_file),
            "raw_script_file": str(raw_script_file),
            "metadata_file": str(metadata_file)
        }


# Updated Audio Generator Integration
class OptimizedPodcastAudioGenerator:
    """Generate audio from optimized podcast scripts"""
    
    def __init__(self, voice_id: str = None):
        # Import the existing audio generator
        from elevenlabs_audio_generator import BlogAudioGenerator
        self.audio_generator = BlogAudioGenerator(voice_id)
        self.available = self.audio_generator.available
    
    async def generate_podcast_audio_from_clean_script(self, clean_script: str, 
                                                     podcast_title: str = "Podcast Episode",
                                                     output_dir: str = "podcast_audio") -> Dict:
        """Generate audio directly from clean script text"""
        
        if not self.available:
            return {
                "success": False,
                "error": "ElevenLabs not available",
                "audio_files": []
            }
        
        print("🎤 Generating audio from clean podcast script...")
        
        # Create article-like data structure for compatibility
        article_data = {
            "article_title": podcast_title,
            "article_content": clean_script  # Use clean script directly
        }
        
        # Override the script creation to use the clean script as-is
        original_create_script = self.audio_generator._create_audio_script
        
        def use_clean_script(article_data):
            return clean_script  # Return clean script without modification
        
        self.audio_generator._create_audio_script = use_clean_script
        
        try:
            result = await self.audio_generator.generate_article_audio(
                article_data, 
                output_dir=output_dir
            )
            
            if result["success"]:
                result["metadata"]["content_type"] = "clean_podcast_script"
                result["metadata"]["script_optimized"] = True
                
                print(f"   ✅ Podcast audio generated from clean script!")
                print(f"   🎵 Files: {len(result['audio_files'])}")
                print(f"   ⏱️ Duration: ~{result['estimated_duration_minutes']} minutes")
            
            return result
            
        finally:
            # Restore original method
            self.audio_generator._create_audio_script = original_create_script


# Test function
async def test_improved_podcast_generation():
    """Test the improved podcast generation with validation"""
    
    print("🎙️ Testing Improved Podcast Script Generation")
    print("=" * 60)
    
    # Sample article data
    test_article = {
        "article_title": "Essential Cybersecurity Practices",
        "article_content": """Cybersecurity threats are constantly evolving, and it's crucial for everyone to understand basic protection measures. Small businesses are particularly vulnerable because they often lack dedicated IT security teams.

The most important step is implementing strong password policies. Every account should have a unique, complex password. Password managers can help generate and store these securely.

Regular software updates are essential. Operating systems and applications should always be kept current with the latest security patches. Many attacks exploit known vulnerabilities in outdated software.

Employee training makes a significant difference. Staff should learn to identify phishing emails and suspicious links. They should also understand the importance of reporting potential security incidents immediately.

Having reliable backup systems is critical. Important data should be backed up regularly and stored in multiple locations, including offline storage for protection against ransomware attacks.""",
        "topic": "cybersecurity essentials"
    }
    
    # Test the improved generator
    generator = ImprovedPodcastScriptGenerator()
    
    result = await generator.generate_clean_podcast_script(
        test_article,
        podcast_style="conversational",
        target_duration=8,
        podcast_name="Cyber For Everyone",
        max_retries=3
    )
    
    if result["success"]:
        print("\n✅ SCRIPT GENERATION SUCCESSFUL!")
        print(f"📊 Validation: {'PASSED' if result['validation']['is_valid'] else 'FAILED'}")
        print(f"📝 Word count: {result['word_count']}")
        print(f"⏱️ Duration: ~{result['estimated_duration_minutes']} minutes")
        print(f"🔄 Retries used: {result['metadata']['retries_used']}")
        
        if result['validation']['issues']:
            print(f"❌ Issues: {result['validation']['issues']}")
        if result['validation']['warnings']:
            print(f"⚠️ Warnings: {result['validation']['warnings']}")
        
        # Save the clean script
        files = generator.save_clean_script(result)
        print(f"\n💾 Files saved to: {files['clean_script_file']}")
        
        # Preview clean script
        clean_preview = result["clean_script"][:300]
        print(f"\n🎤 CLEAN SCRIPT PREVIEW (audio-ready):")
        print("-" * 40)
        print(f"{clean_preview}...")
        
        # Test audio generation
        print(f"\n🎵 Testing audio generation...")
        audio_generator = OptimizedPodcastAudioGenerator()
        
        if audio_generator.available:
            audio_result = await audio_generator.generate_podcast_audio_from_clean_script(
                result["clean_script"],
                "Test Cybersecurity Podcast"
            )
            
            if audio_result["success"]:
                print(f"✅ Audio generation successful!")
                print(f"🎵 Audio file: {audio_result['audio_files'][0]}")
            else:
                print(f"❌ Audio generation failed: {audio_result['error']}")
        else:
            print("⚠️ Audio generation not available - check ElevenLabs setup")
        
    else:
        print(f"❌ Script generation failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(test_improved_podcast_generation())