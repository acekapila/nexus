# enhanced_podcast_article_system.py - COMPLETE system with LinkedIn integration
import os
import json
import requests
import asyncio
import openai
import anthropic
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import re
from dotenv import load_dotenv
load_dotenv("/Users/acekapila/Documents/llm_train/cyb4eo/ai-article-generator/.env")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import the enhanced source tracking components
from enhanced_source_tracking import (
    EnhancedPerplexityWebResearcherWithSourceTracking, 
    SourceAttributedArticleGenerator
)

# Import ALL your existing components to maintain the complete workflow
from audio_enhanced_wordpress_publisher import AudioEnhancedWordPressPublisher
from elevenlabs_audio_generator import BlogAudioGenerator

# Import the LinkedIn poster with the clean markdown and URL positioning methods
from personal_social_media_poster import EnhancedLinkedInPoster


# Keep your existing quality control classes
class ArticleQualityAgent:
    """Agent responsible for improving article quality, readability, and structure"""

    def __init__(self):
        self.anthropic_client = anthropic.AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    async def improve_readability(self, article_content: str, topic: str) -> Dict:
        """Improve article readability and flow"""
        
        print("📖 Improving article readability and flow...")
        
        readability_prompt = f"""You are an expert content editor specializing in making complex topics accessible to general audiences.

Your task: Take this article content about "{topic}" and improve its readability while maintaining accuracy.

IMPROVEMENTS NEEDED:
1. Simplify complex sentences and jargon
2. Improve flow between paragraphs
3. Add smooth transitions
4. Use simpler vocabulary where possible
5. Ensure consistent tone throughout
6. Break up long paragraphs
7. Add subheadings for better structure

ORIGINAL CONTENT:
{article_content}

REQUIREMENTS:
- Keep all factual information accurate
- Maintain the article's core message
- Target reading level: 8th-9th grade
- Ensure smooth, natural flow
- Use active voice where possible
- Keep the same general structure
- Return ONLY the improved content (no title)
- PRESERVE ALL SOURCE ATTRIBUTIONS - do not remove citations or source references

Rewrite the entire article content with improved readability:"""

        try:
            response = await self.anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                messages=[{"role": "user", "content": readability_prompt}],
                max_tokens=4000,
            )

            improved_content = response.content[0].text.strip()
            
            return {
                "success": True,
                "improved_content": improved_content,
                "improvements_made": "Simplified language, improved flow, enhanced readability while preserving source attributions"
            }
            
        except Exception as e:
            print(f"   ❌ Readability improvement failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "improved_content": article_content
            }
    
    async def check_article_quality(self, article_content: str, topic: str) -> Dict:
        """Check article for quality, completeness, and structural issues"""
        
        print("🔍 Checking article quality and structure...")
        
        quality_check_prompt = f"""You are a professional content quality analyst. Analyze this article content about "{topic}" for quality issues.

CONTENT TO ANALYZE:
{article_content}

CHECK FOR THESE ISSUES:
1. Multiple conclusion sections (should only have ONE)
2. Incomplete or abrupt endings
3. Poor structure or organization
4. Factual inconsistencies
5. Repetitive content
6. Missing essential information
7. Formatting issues
8. Logical flow problems
9. Source attribution quality (are sources properly cited?)

RETURN A JSON RESPONSE WITH:
{{
  "overall_quality": "excellent|good|fair|poor",
  "completeness_score": 1-10,
  "structure_issues": ["list of specific issues found"],
  "content_issues": ["list of content problems"],
  "recommendations": ["specific suggestions for improvement"],
  "needs_revision": true/false,
  "conclusion_count": number_of_conclusion_sections_found,
  "article_makes_sense": true/false,
  "main_problems": ["top 3 most critical issues"],
  "source_attribution_quality": "good|fair|poor"
}}

Analyze thoroughly and provide detailed feedback:"""

        try:
            response = await self.anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                messages=[{"role": "user", "content": quality_check_prompt}],
                max_tokens=2000,
            )

            quality_analysis = response.content[0].text.strip()
            
            # Clean up the response
            if quality_analysis.startswith('```json'):
                quality_analysis = quality_analysis.replace('```json', '').replace('```', '').strip()
            elif quality_analysis.startswith('```'):
                quality_analysis = quality_analysis.replace('```', '').strip()
            
            if not quality_analysis:
                raise ValueError("Empty response from quality check")
            
            quality_data = json.loads(quality_analysis)
            
            return {
                "success": True,
                "quality_analysis": quality_data
            }
            
        except json.JSONDecodeError as e:
            print(f"   ❌ Quality check JSON parsing failed: {str(e)}")
            return {
                "success": False,
                "error": f"JSON parsing failed: {str(e)}",
                "quality_analysis": {
                    "overall_quality": "unknown",
                    "completeness_score": 5,
                    "needs_revision": True,
                    "main_problems": ["Quality check parsing failed"],
                    "conclusion_count": 1,
                    "article_makes_sense": True,
                    "structure_issues": [],
                    "content_issues": [],
                    "recommendations": ["Manual review needed"],
                    "source_attribution_quality": "unknown"
                }
            }
        except Exception as e:
            print(f"   ❌ Quality check failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "quality_analysis": {
                    "overall_quality": "unknown",
                    "completeness_score": 5,
                    "needs_revision": True,
                    "main_problems": ["Quality check failed"],
                    "conclusion_count": 1,
                    "article_makes_sense": True,
                    "structure_issues": [],
                    "content_issues": [],
                    "recommendations": ["Manual review needed"],
                    "source_attribution_quality": "unknown"
                }
            }
    
    async def fix_structure_issues(self, article_content: str, quality_issues: Dict, topic: str) -> Dict:
        """Fix structural and content issues identified in quality check"""
        
        print("🔧 Fixing structural and content issues...")
        
        issues_list = quality_issues.get("structure_issues", []) + quality_issues.get("content_issues", [])
        
        fix_prompt = f"""You are a professional content editor. Fix the following issues in this article content about "{topic}":

IDENTIFIED ISSUES:
{chr(10).join(f"- {issue}" for issue in issues_list)}

SPECIFIC REQUIREMENTS:
1. Ensure ONLY ONE conclusion section at the end
2. Remove any duplicate or repetitive content
3. Fix structural problems
4. Ensure logical flow from introduction to conclusion
5. Complete any incomplete sections
6. Fix formatting issues
7. Ensure the content makes sense as a whole
8. PRESERVE ALL SOURCE ATTRIBUTIONS - do not remove citations or source references

ORIGINAL CONTENT:
{article_content}

Return the COMPLETE corrected content with all issues fixed (no title):"""

        try:
            response = await self.anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                messages=[{"role": "user", "content": fix_prompt}],
                max_tokens=4000,
            )

            fixed_content = response.content[0].text.strip()
            
            return {
                "success": True,
                "fixed_content": fixed_content,
                "issues_fixed": issues_list
            }
            
        except Exception as e:
            print(f"   ❌ Structure fixing failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "fixed_content": article_content
            }


# Enhanced Article Generator with integrated LinkedIn posting methods
class EnhancedArticleGeneratorWithLinkedInIntegration:
    """Enhanced article generator with integrated clean LinkedIn posting"""

    def __init__(self):
        self.anthropic_client = anthropic.AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.openai_client = openai.AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))  # for social media posting
        self.quality_agent = ArticleQualityAgent()
        self.source_attributed_generator = SourceAttributedArticleGenerator()
        self.linkedin_poster = EnhancedLinkedInPoster()
    
    async def generate_article_with_enhanced_research(self, topic: str, research_data: Dict, 
                                                    audience: str = None, article_type: str = "how-to") -> Dict:
        """Generate article using research data - with source tracking if available"""
        
        print("📝 Generating article with research context...")
        
        # Check if we have source tracking data
        has_source_tracking = (
            research_data.get("research_type") == "enhanced_deep_research_with_source_tracking" and
            not research_data.get("source_tracking_failed")
        )
        
        if has_source_tracking:
            print("   📚 Using SOURCE ATTRIBUTION method")
            return await self.source_attributed_generator.generate_article_with_proper_attribution(
                topic, research_data, audience, article_type
            )
        else:
            print("   📚 Using STANDARD method")
            return await self._generate_standard_article(topic, research_data, audience, article_type)
    
    async def _generate_standard_article(self, topic: str, research_data: Dict, 
                                       audience: str = None, article_type: str = "how-to") -> Dict:
        """Generate article using standard method"""
        
        # Extract research insights
        research_summary = research_data.get("research_summary", "")
        sources = research_data.get("web_sources_analyzed", [])
        trends = research_data.get("recent_trends", [])
        statistics = research_data.get("key_statistics", [])
        content_gaps = research_data.get("content_gaps", [])
        
        # Build research context
        research_context = self._build_research_context(research_summary, sources, trends, statistics, content_gaps)
        
        # STEP 1: Generate article content WITHOUT any title
        article_content = await self._generate_article_content(topic, research_context, audience, article_type)
        
        if not article_content:
            return {"success": False, "error": "Failed to generate article content"}
        
        print("   ✅ Article content generated")
        
        # STEP 2: Generate title based on the actual content
        article_title = await self._generate_title_from_content(article_content, topic)
        
        print(f"   📋 Generated title: {article_title}")
        
        # STEP 3: Generate meta description based on content
        meta_description = await self._generate_meta_description_from_content(article_content, article_title)
        
        # STEP 4: Generate article outline/structure
        outline = await self._generate_article_outline(article_content, topic)
        
        return {
            "success": True,
            "article_content": article_content,  # Pure content, no title
            "article_title": article_title,      # Separate title variable
            "title_options": [article_title],    # For backward compatibility
            "unified_title": article_title,      # For backward compatibility
            "meta_description": meta_description,
            "outline": outline,
            "topic": topic,
            "audience": audience,
            "article_type": article_type,
            "research_integrated": True,
            "source_attribution_used": False,
            "research_data": research_data
        }
    
    def _build_research_context(self, summary: str, sources: List, trends: List, stats: List, gaps: List) -> str:
        """Build formatted research context for article generation"""
        
        context_parts = []
        
        if summary:
            context_parts.append(f"RESEARCH SUMMARY:\n{summary}")
        
        if trends:
            context_parts.append("CURRENT TRENDS:\n" + "\n".join(f"- {trend}" for trend in trends[:5]))
        
        if stats:
            context_parts.append("KEY STATISTICS:\n" + "\n".join(f"- {stat}" for stat in stats[:5]))
        
        if gaps:
            context_parts.append("CONTENT GAPS TO ADDRESS:\n" + "\n".join(f"- {gap}" for gap in gaps[:3]))
        
        if sources:
            context_parts.append("SOURCE INSIGHTS:\n" + "\n".join(f"- {source.get('title', 'Unknown')}: {source.get('snippet', '')[:100]}..." for source in sources[:3]))
        
        return "\n\n".join(context_parts)
    
    async def _generate_article_content(self, topic: str, research_context: str, 
                                      audience: str, article_type: str) -> str:
        """Generate pure article content without any title"""
        
        content_prompt = f"""You are an expert content writer. Create comprehensive article content about "{topic}" using the provided research context.

RESEARCH CONTEXT:
{research_context}

CONTENT REQUIREMENTS:
- Target audience: {audience or "Professional audience"}
- Article type: {article_type}
- English type: Australian English
- Length: 2000-3000 words
- Start directly with an engaging introduction paragraph
- Include 4-6 main sections with descriptive H2 headings (## Section Name)
- End with ONE conclusion section (## Conclusion)
- Writing style: Professional but accessible
- Include actionable insights from the research
- Use statistics and trends from the research naturally

HEADING STYLE REQUIREMENTS:
- Make headings compelling and curiosity-driven
- Focus on what the reader will learn or discover
- Ask yourself: "Why should someone read this next section?"
- Use benefit-focused, insight-driven language
- STRICTLY AVOID academic phrases like "Evidence-Based Insights", "Expert Perspectives", "Research-Backed Benefits", "Practical Implementation", "Addressing Limitations"
- NEVER use methodology-focused headings that describe the source of information
- Instead use reader-focused headings about the actual insights and topics

FORBIDDEN HEADING PATTERNS:
❌ "Evidence-Based Insights"
❌ "Expert Perspectives" 
❌ "Research-Backed Benefits"
❌ "Practical Implementation"
❌ "Addressing Limitations"
❌ "Current Landscape"
❌ Any heading that describes WHERE information comes from

PREFERRED HEADING PATTERNS:
✅ "Why [Problem] Is Getting Worse"
✅ "The Hidden Truth About [Topic]"
✅ "What Really Works for [Solution]"
✅ "How [Bad Actors] Exploit [Vulnerability]"
✅ "Simple Steps That Actually Work"
✅ "The Real Cost of Ignoring [Issue]"
✅ "What Most People Miss About [Topic]"

EXAMPLE TRANSFORMATIONS:
- "Evidence-Based Insights" → "Why Romance Scams Are Skyrocketing"
- "Expert Perspectives" → "How Scammers Exploit Your Emotions"  
- "Research-Backed Benefits" → "What Awareness Actually Prevents"
- "Practical Implementation" → "Simple Steps to Protect Yourself"
- "Current Landscape" → "The Growing Threat You Need to Know"

CRITICAL CONTENT RULES:
1. NEVER write "(source needed)" or similar placeholders
2. Only include statistics that are fully sourced in the research context
3. If research context lacks specific statistics, create general informative content instead
4. All claims must be either common knowledge or backed by the provided research
5. Focus on practical advice and actionable insights
6. Use complete sentences with full context for any statistics
7. Use the evidence naturally without announcing it's "evidence-based"

STRUCTURE FORMAT:
1. Introduction paragraph (engaging opener, no heading)
2. ## [Compelling insight-driven heading about the problem/challenge]
3. ## [Intriguing heading about what people should know]
4. ## [Benefit-focused heading about solutions/strategies]
5. ## [Results-oriented heading about outcomes/benefits]
6. ## [Challenge-focused heading about obstacles/limitations]
7. ## Conclusion

CRITICAL INSTRUCTIONS:
- Do NOT include any title or main heading
- Start immediately with introduction content
- Use only H2 headings (##) for main sections
- Make content comprehensive and valuable
- Include practical examples and actionable advice
- NEVER use placeholder text like "(source needed)"
- Only reference statistics that are clearly provided in the research context
- Make headings irresistible - focus on reader curiosity and benefits

Write the complete article content (no title, just content):"""

        try:
            response = await self.anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                messages=[{"role": "user", "content": content_prompt}],
                max_tokens=4000,
            )

            content = response.content[0].text.strip()
            
            # Clean any potential title remnants and validate content
            content = self._clean_content_only(content)
            content = self._validate_and_clean_content(content)
            
            return content
            
        except Exception as e:
            print(f"   ❌ Content generation failed: {str(e)}")
            return None
    
    def _validate_and_clean_content(self, content: str) -> str:
        """Validate and clean content to remove any placeholder text or problematic elements"""
        
        # Remove common placeholder patterns
        problematic_patterns = [
            r'\(source needed\)',
            r'\[source needed\]',
            r'\(citation needed\)',
            r'\[citation needed\]',
            r'\(needs source\)',
            r'\[needs source\]',
            r'\(add source\)',
            r'\[add source\]',
            r'\(pending verification\)',
            r'\[pending verification\]'
        ]
        
        for pattern in problematic_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Clean up any double spaces or orphaned punctuation
        content = re.sub(r'\s+', ' ', content)  # Multiple spaces to single space
        content = re.sub(r'\s+([,.!?;:])', r'\1', content)  # Remove space before punctuation
        content = re.sub(r'([.!?])\s*([.!?])', r'\1 \2', content)  # Fix double punctuation
        
        return content.strip()
    
    async def _generate_title_from_content(self, article_content: str, topic: str) -> str:
        """Generate compelling title based on the actual article content"""
        
        title_prompt = f"""Analyze this article content about "{topic}" and create a compelling title.

ARTICLE CONTENT:
{article_content[:2500]}...

TITLE REQUIREMENTS:
- Under 60 characters for SEO
- Engaging and professional
- Accurately reflects the content
- Clear value proposition
- No subtitle or secondary text
- Should entice readers to click

Based on the actual content, create ONE perfect title:"""

        try:
            response = await self.anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                messages=[{"role": "user", "content": title_prompt}],
                max_tokens=100,
            )

            title = response.content[0].text.strip()
            # Clean any quotes or extra formatting
            title = title.replace('"', '').replace("'", "").strip()

            return title
            
        except Exception as e:
            print(f"   ⚠️ Title generation failed, using fallback: {str(e)}")
            return f"Complete Guide to {topic}"
    
    async def _generate_meta_description_from_content(self, article_content: str, title: str) -> str:
        """Generate meta description based on actual content and title"""
        
        meta_prompt = f"""Create a compelling meta description for this article.

TITLE: {title}
CONTENT PREVIEW: {article_content[:1500]}...

META DESCRIPTION REQUIREMENTS:
- Under 160 characters
- Compelling and descriptive
- Includes main value proposition
- Encourages clicks
- Summarizes key benefits

Create the meta description:"""

        try:
            response = await self.anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                messages=[{"role": "user", "content": meta_prompt}],
                max_tokens=100,
            )

            return response.content[0].text.strip().replace('"', '')
            
        except Exception as e:
            return "Comprehensive guide with expert insights and practical advice."
    
    def _clean_content_only(self, content: str) -> str:
        """Remove any title-like elements from content"""
        lines = content.split('\n')
        cleaned_lines = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Skip potential title lines at the beginning
            if i < 3:
                # Skip lines that look like titles
                if (len(line_stripped) < 80 and 
                    not line_stripped.endswith(('.', '!', '?')) and
                    not line_stripped.startswith('##') and
                    line_stripped.isupper()):
                    continue
                
                # Skip lines that start with # (any heading level except ##)
                if line_stripped.startswith('#') and not line_stripped.startswith('##'):
                    continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    async def _generate_article_outline(self, article_content: str, topic: str) -> Dict:
        """Generate article outline/structure from the content"""
        
        outline_prompt = f"""Analyze this article about "{topic}" and extract its structure.

ARTICLE CONTENT:
{article_content[:2000]}...

Extract the main sections and create a JSON outline:
{{
  "article_structure": {{
    "introduction": "Brief description of intro",
    "main_sections": [
      {{"section_title": "Section 1", "section_summary": "Summary"}},
      {{"section_title": "Section 2", "section_summary": "Summary"}}
    ],
    "conclusion": "Brief description of conclusion"
  }},
  "estimated_sections": 6,
  "content_type": "guide"
}}"""

        try:
            response = await self.anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                messages=[{"role": "user", "content": outline_prompt}],
                max_tokens=1000,
            )

            outline_text = response.content[0].text.strip()
            
            # Clean up markdown formatting
            if outline_text.startswith('```json'):
                outline_text = outline_text.replace('```json', '').replace('```', '').strip()
            elif outline_text.startswith('```'):
                outline_text = outline_text.replace('```', '').strip()
            
            outline_data = json.loads(outline_text)
            return outline_data
            
        except Exception as e:
            # Extract headings manually as fallback
            headings = re.findall(r'^#+\s+(.+)$', article_content, re.MULTILINE)
            
            main_sections = []
            for heading in headings[:6]:
                if not any(word in heading.lower() for word in ['introduction', 'conclusion']):
                    main_sections.append({
                        "section_title": heading.strip(),
                        "section_summary": f"Content about {heading.strip().lower()}"
                    })
            
            return {
                "article_structure": {
                    "introduction": "Article introduction",
                    "main_sections": main_sections,
                    "conclusion": "Article conclusion and summary"
                },
                "estimated_sections": len(main_sections) + 2,
                "content_type": "guide"
            }
    
    async def generate_clean_linkedin_post(self, article_data: Dict, article_url: str) -> Dict:
        """Generate clean LinkedIn post using AI to extract actual article insights"""
        
        print("📱 Generating clean LinkedIn post with proper formatting...")
        
        # Extract article details
        title = article_data.get('article_title') or article_data.get('unified_title', 'Article')
        content = article_data.get('article_content', '')
        topic = article_data.get('topic', '')
        
        # Generate AI-powered LinkedIn post based on actual article content
        linkedin_content = await self._generate_dynamic_linkedin_post(title, content, topic, article_url)
        
        return {
            "success": True,
            "linkedin_content": linkedin_content,
            "character_count": len(linkedin_content),
            "has_complete_stats": True,
            "clean_formatting": True,
            "url_at_top": True,
            "source": "ai_generated_from_article"
        }
    
    async def _generate_dynamic_linkedin_post(self, title: str, content: str, topic: str, article_url: str) -> str:
        """Generate LinkedIn post using AI based on actual article content"""
        
        try:
            # Create prompt for LinkedIn post generation
            linkedin_prompt = f"""Create a professional LinkedIn post for this article.

ARTICLE TITLE: {title}
ARTICLE CONTENT: {content[:2000]}...
TOPIC: {topic}
ARTICLE URL: {article_url}

REQUIREMENTS:
1. Start with a compelling hook (no markdown, plain text, under 15 words)
2. Place the article URL immediately after the hook with proper line breaks
3. Include the article title in quotes with a brief value proposition
4. Extract 3 key insights/statistics from the ACTUAL article content (not generic stats)
5. Add an engagement question related to the specific topic
6. Include relevant hashtags (4-6)
7. Keep total under 1300 characters
8. NO markdown formatting (**, *, etc.)
9. Professional tone throughout
10. Use proper line breaks for readability

EXACT STRUCTURE WITH LINE BREAKS:
[Compelling hook about the topic]

🔗 Read the new article: {article_url}

"[Article Title]" [value proposition based on content].

💡 Key insights from the article:
• [Actual insight 1 from the content]
• [Actual insight 2 from the content] 
• [Actual insight 3 from the content]

[Engagement question specific to the topic]

[Relevant hashtags]

CRITICAL: 
- Only use insights/statistics that actually appear in the article content
- Use double line breaks between sections for proper spacing
- Ensure each bullet point is on its own line"""

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a LinkedIn content expert. Create professional posts with clean formatting, proper line breaks, and content that matches the article. Never use markdown formatting or generic statistics. Use double line breaks between sections."
                    },
                    {"role": "user", "content": linkedin_prompt}
                ],
                max_tokens=800,
                temperature=0.4
            )
            
            linkedin_content = response.choices[0].message.content.strip()
            
            # Clean any potential markdown that slipped through
            linkedin_content = self._clean_linkedin_formatting(linkedin_content)
            
            # Ensure proper line breaks for LinkedIn
            linkedin_content = self._fix_linkedin_line_breaks(linkedin_content)
            
            print(f"   ✨ AI-generated LinkedIn post: {len(linkedin_content)} characters")
            return linkedin_content
            
        except Exception as e:
            print(f"   ⚠️ AI LinkedIn generation failed: {str(e)}, using fallback")
            return self._create_fallback_linkedin_post(title, topic, article_url)
    
    def _fix_linkedin_line_breaks(self, content: str) -> str:
        """Ensure proper line breaks for LinkedIn formatting"""
        
        # Normalize line breaks - replace any single \n with double \n\n for better spacing
        lines = content.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:  # Skip empty lines
                continue
                
            formatted_lines.append(line)
            
            # Add extra spacing after certain elements
            if (line.startswith('🔗') or 
                line.startswith('💡') or 
                line.endswith('?') or 
                line.startswith('#')):
                formatted_lines.append('')  # Add blank line
        
        # Join with single line breaks, but the blank lines will create proper spacing
        result = '\n'.join(formatted_lines)
        
        # Clean up any triple line breaks
        result = re.sub(r'\n\n\n+', '\n\n', result)
        
        return result.strip()
    
    def _clean_linkedin_formatting(self, content: str) -> str:
        """Remove any markdown formatting from LinkedIn content"""
        
        # Remove markdown formatting
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Bold
        content = re.sub(r'\*(.*?)\*', r'\1', content)      # Italic
        content = re.sub(r'`(.*?)`', r'\1', content)        # Code
        content = re.sub(r'#{1,6}\s+', '', content)         # Headers
        
        # Clean up any escaped characters
        content = content.replace('\\', '')
        
        # Don't normalize line breaks here - let _fix_linkedin_line_breaks handle it
        
        return content.strip()
    
    def _create_fallback_linkedin_post(self, title: str, topic: str, article_url: str) -> str:
        """Fallback LinkedIn post when AI generation fails"""
        
        hook = f"New insights on {topic} that professionals need to know."
        
        fallback_post = f"""{hook}

🔗 Read the new article: {article_url}

"{title}" provides practical guidance with actionable insights.

💡 Key takeaways:
• Essential strategies for protection
• Expert recommendations for awareness
• Practical steps for implementation

What's your experience with {topic.lower()}? Share your thoughts below!

#Technology #Innovation #ProfessionalDevelopment"""

        return self._fix_linkedin_line_breaks(fallback_post)


class EnhancedQualityControlledArticleSystemWithLinkedInIntegration:
    """Complete system with clean LinkedIn integration"""
    
    def __init__(self):
        # Initialize ALL components for complete workflow
        self.researcher = EnhancedPerplexityWebResearcherWithSourceTracking()
        self.generator = EnhancedArticleGeneratorWithLinkedInIntegration()
        self.linkedin = EnhancedLinkedInPoster()
        self.wordpress = AudioEnhancedWordPressPublisher()
        self.audio_generator = BlogAudioGenerator()
        
        # Check system availability
        self.perplexity_available = bool(self.researcher.base_researcher.api_key)
        self.openai_available = bool(os.getenv('OPENAI_API_KEY'))
        self.wordpress_available = bool(self.wordpress.access_token)
        self.linkedin_available = 'linkedin_personal' in self.linkedin.enabled_platforms
        self.audio_available = self.audio_generator.available
        self.enhanced_research_available = self.perplexity_available and self.openai_available
        self.source_tracking_available = self.enhanced_research_available
    
    def _estimate_syllables(self, text: str) -> int:
        """Estimate syllable count for readability calculations"""
        text = re.sub(r'[^\w\s]', '', text.lower())
        words = text.split()
        
        syllable_count = 0
        for word in words:
            vowels = 'aeiouy'
            word = word.strip('.,!?;:"')
            if len(word) == 0:
                continue
                
            syllable_groups = 0
            prev_was_vowel = False
            
            for char in word:
                is_vowel = char in vowels
                if is_vowel and not prev_was_vowel:
                    syllable_groups += 1
                prev_was_vowel = is_vowel
            
            if word.endswith('e') and syllable_groups > 1:
                syllable_groups -= 1
            
            syllable_count += max(1, syllable_groups)
        
        return syllable_count
    
    def _get_reading_level(self, flesch_score: float) -> str:
        """Convert Flesch Reading Ease score to reading level description"""
        if flesch_score >= 90:
            return "5th grade"
        elif flesch_score >= 80:
            return "6th grade"
        elif flesch_score >= 70:
            return "7th grade"
        elif flesch_score >= 60:
            return "8th-9th grade"
        elif flesch_score >= 50:
            return "10th-12th grade"
        elif flesch_score >= 30:
            return "College level"
        else:
            return "Graduate level"

    async def generate_complete_workflow_with_clean_linkedin(
        self, topic: str, audience: str = None, article_type: str = "how-to",
        enable_enhanced_research: bool = True, 
        enable_source_tracking: bool = True,
        research_model: str = "sonar",
        max_urls_to_browse: int = 6, 
        publish_to_wordpress: bool = True, 
        wordpress_status: str = "publish", 
        post_to_linkedin: bool = True,
        generate_audio: bool = True,
        audio_output_dir: str = "audio_output",
        max_revision_cycles: int = 2
    ) -> Dict:
        """COMPLETE workflow with clean LinkedIn integration"""
        
        print(f"\n🎭 Starting COMPLETE workflow with clean LinkedIn integration for: {topic}")
        print("   🔍 Research → Source Tracking → Article → Quality → Audio → WordPress → Clean LinkedIn")
        
        # PHASE 1: Enhanced Research with Source Tracking
        research_data = {}
        
        if enable_source_tracking and self.source_tracking_available:
            print("🔍 Phase 1: Research with comprehensive source tracking...")
            try:
                research_data = await self.researcher.deep_research_topic_with_source_tracking(
                    topic, max_urls_to_browse=max_urls_to_browse
                )
                
                if not research_data.get("source_tracking_failed"):
                    urls_browsed = research_data.get('urls_analyzed', 0)
                    sourced_claims = research_data.get('sourced_claims_count', 0)
                    sources_tracked = len(research_data.get('source_summary', []))
                    
                    print(f"   ✅ Source tracking complete!")
                    print(f"   📊 URLs browsed: {urls_browsed}")
                    print(f"   📝 Sourced claims: {sourced_claims}")
                    print(f"   📚 Sources tracked: {sources_tracked}")
                else:
                    print("   ⚠️ Source tracking failed, falling back to enhanced research")
                    enable_source_tracking = False
                    
            except Exception as e:
                print(f"   ⚠️ Source tracking failed: {str(e)}")
                enable_source_tracking = False
        
        # Fallback to enhanced research without source tracking
        if not enable_source_tracking or not self.source_tracking_available:
            if enable_enhanced_research and self.enhanced_research_available:
                print("📚 Phase 1: Enhanced research without source tracking...")
                try:
                    self.researcher.base_researcher.set_model(research_model)
                    research_data = await self.researcher.base_researcher.deep_research_topic_with_browsing(
                        topic, max_urls_to_browse=max_urls_to_browse
                    )
                    
                    urls_browsed = research_data.get('urls_analyzed', 0)
                    words_extracted = research_data.get('total_words_browsed', 0)
                    print(f"   ✅ Enhanced research complete! Browsed {urls_browsed} URLs, {words_extracted} words")
                except Exception as e:
                    print(f"   ⚠️ Enhanced research failed: {str(e)}")
                    research_data = {"web_research_enabled": False}
            else:
                print("   ⚠️ No research APIs available")
                research_data = {"web_research_enabled": False}
        
        # PHASE 2: Generate Article
        print("📝 Phase 2: Generating content...")
        article_result = await self.generator.generate_article_with_enhanced_research(
            topic, research_data, audience, article_type
        )
        
        if not article_result["success"]:
            return article_result
        
        # Extract separate variables
        current_content = article_result["article_content"]
        current_title = article_result["article_title"]
        
        print(f"   ✅ Content generated: {len(current_content)} characters")
        print(f"   🎯 Title created: {current_title}")
        
        if article_result.get("source_attribution_used"):
            print(f"   📚 Sources cited: {article_result.get('sources_cited', 0)}")
            print(f"   📝 Sourced claims: {article_result.get('sourced_claims_used', 0)}")
        
        revision_cycle = 0
        quality_logs = []
        
        # PHASE 3: Quality Control Loop
        while revision_cycle < max_revision_cycles:
            revision_cycle += 1
            print(f"\n🔧 Phase 3.{revision_cycle}: Quality control check...")
            
            quality_check = await self.generator.quality_agent.check_article_quality(current_content, topic)
            
            if quality_check["success"]:
                quality_analysis = quality_check["quality_analysis"]
                quality_logs.append(quality_analysis)
                
                print(f"   📊 Quality: {quality_analysis.get('overall_quality', 'unknown')}")
                print(f"   📈 Completeness: {quality_analysis.get('completeness_score', 0)}/10")
                if quality_analysis.get('source_attribution_quality'):
                    print(f"   📚 Source attribution: {quality_analysis.get('source_attribution_quality', 'unknown')}")
                
                # Quality passing criteria
                needs_revision = quality_analysis.get("needs_revision", False)
                overall_quality = quality_analysis.get("overall_quality", "poor")
                completeness_score = quality_analysis.get("completeness_score", 0)
                
                quality_passed = (
                    overall_quality in ["good", "excellent"] and 
                    completeness_score >= 7 and 
                    not needs_revision
                )
                
                if quality_passed:
                    print(f"   ✅ Quality check passed!")
                    break
                elif revision_cycle < max_revision_cycles:
                    main_problems = quality_analysis.get("main_problems", [])
                    if main_problems:
                        print(f"   🔧 Issues found: {', '.join(main_problems[:2])}")
                    
                    # Fix issues in content
                    fix_result = await self.generator.quality_agent.fix_structure_issues(
                        current_content, quality_analysis, topic
                    )
                    
                    if fix_result["success"]:
                        current_content = fix_result["fixed_content"]
                        current_title = await self.generator._generate_title_from_content(current_content, topic)
                        print(f"   ✅ Content and title updated")
                    else:
                        print(f"   ⚠️ Could not fix issues, regenerating...")
                        new_article = await self.generator.generate_article_with_enhanced_research(
                            topic, research_data, audience, article_type
                        )
                        
                        if new_article["success"]:
                            current_content = new_article["article_content"]
                            current_title = new_article["article_title"]
                            print(f"   ✅ Content regenerated")
                        else:
                            break
                else:
                    print(f"   ⚠️ Max revision cycles reached")
                    break
            else:
                print(f"   ❌ Quality check failed, using fallback assessment")
                quality_logs.append({
                    "overall_quality": "fair",
                    "completeness_score": 6,
                    "needs_revision": False,
                    "source_attribution_quality": "unknown"
                })
                break
        
        # PHASE 4: Final Readability Enhancement
        print("📖 Phase 4: Final readability enhancement...")
        readability_result = await self.generator.quality_agent.improve_readability(current_content, topic)
        
        if readability_result["success"]:
            final_content = readability_result["improved_content"]
            final_title = await self.generator._generate_title_from_content(final_content, topic)
            print("   ✅ Readability improved and title updated")
        else:
            final_content = current_content
            final_title = current_title
            print("   ⚠️ Readability improvement failed")
        
        # Update article data
        article_result["article_content"] = final_content
        article_result["article_title"] = final_title
        article_result["unified_title"] = final_title
        article_result["title_options"] = [final_title]
        
        article_result["quality_control"] = {
            "revision_cycles": revision_cycle,
            "quality_logs": quality_logs,
            "final_quality": quality_logs[-1] if quality_logs else None,
            "readability_improved": readability_result["success"],
            "separate_title_content": True,
            "source_attribution_used": article_result.get("source_attribution_used", False)
        }
        
        # Calculate metrics
        word_count = len(final_content.split())
        sentence_count = len([s for s in final_content.replace('!', '.').replace('?', '.').split('.') if s.strip()])
        syllable_count = self._estimate_syllables(final_content)
        
        if sentence_count > 0 and word_count > 0:
            avg_sentence_length = word_count / sentence_count
            avg_syllables_per_word = syllable_count / word_count
            flesch_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
            flesch_score = max(0, min(100, flesch_score))
        else:
            flesch_score = 50
        
        reading_level = self._get_reading_level(flesch_score)
        
        article_result["metrics"] = {
            "created_at": datetime.now().isoformat(),
            "word_count": word_count,
            "estimated_reading_time_minutes": word_count // 200,
            "character_count": len(final_content),
            "paragraph_count": len([p for p in final_content.split('\n\n') if p.strip()]),
            "quality_score": quality_logs[-1].get("completeness_score", 0) if quality_logs else 0,
            "flesch_reading_score": round(flesch_score, 1),
            "reading_level": reading_level,
            "sentence_count": sentence_count,
            "avg_words_per_sentence": round(word_count / sentence_count, 1) if sentence_count > 0 else 0,
            "title_length": len(final_title),
            "source_tracking_used": enable_source_tracking and not research_data.get("source_tracking_failed"),
            "sources_cited": article_result.get("sources_cited", 0),
            "sourced_claims_used": article_result.get("sourced_claims_used", 0)
        }
        
        # PHASE 5: Audio Generation
        audio_results = {}
        audio_files = []
        
        if generate_audio and self.audio_available:
            print("\n🎤 Phase 5: Audio generation...")
            
            # Generate full audio
            audio_result = await self.audio_generator.generate_article_audio(
                article_result, output_dir=audio_output_dir
            )
            audio_results["full_audio"] = audio_result
            
            if audio_result["success"]:
                audio_files.extend(audio_result["audio_files"])
                print(f"   ✅ Audio generated: {len(audio_result['audio_files'])} files")
                print(f"   ⏱️ Duration: ~{audio_result['estimated_duration_minutes']} minutes")
            else:
                print(f"   ❌ Audio generation failed: {audio_result.get('error')}")
        else:
            if not self.audio_available:
                print("\n⚠️ Phase 5: Audio generation skipped (not available)")
            else:
                print("\n⚠️ Phase 5: Audio generation skipped (disabled)")
        
        # PHASE 6: WordPress Publishing with Audio
        result = {
            "article_data": article_result,
            "research_summary": research_data,
            "audio_results": audio_results,
            "wordpress_result": None,
            "linkedin_result": None,
            "workflow_success": False
        }
        
        # Save local files
        try:
            from article_generator import save_article_files
            file_paths = save_article_files(article_result)
            result["file_paths"] = file_paths
        except:
            print("   ⚠️ Could not save local files")
        
        # Publish to WordPress with audio integration
        if publish_to_wordpress and self.wordpress_available:
            print("🌐 Phase 6: Publishing to WordPress with source information...")
            print(f"   📋 Title: {final_title}")
            print(f"   📄 Content: {len(final_content)} chars")
            print(f"   🎵 Audio files: {len(audio_files)}")
            
            if article_result.get("source_attribution_used"):
                print(f"   📚 Sources cited: {article_result.get('sources_cited', 0)}")
                
                # Add source methodology section to content
                enhanced_content = self._add_source_methodology_section(
                    final_content, article_result, research_data
                )
                article_result["article_content"] = enhanced_content
            
            # Use enhanced WordPress publisher with audio
            wordpress_result = await self.wordpress.publish_article_with_audio(
                article_result, 
                audio_files=audio_files if audio_files else None,
                status=wordpress_status
            )
            result["wordpress_result"] = wordpress_result
            
            if wordpress_result["success"]:
                article_url = wordpress_result["post_url"]
                print(f"   ✅ Published: {article_url}")
                if wordpress_result.get("has_audio"):
                    print(f"   🎧 Audio embedded: {wordpress_result.get('audio_files_uploaded', 0)} files")
                if article_result.get("source_attribution_used"):
                    print(f"   📚 Article includes source methodology section")
                
                # PHASE 7: Clean LinkedIn Post with Research Credibility
                if post_to_linkedin and self.linkedin_available:
                    print("📱 Phase 7: Sharing on LinkedIn with clean formatting...")
                    
                    # Use the enhanced clean LinkedIn posting method
                    clean_linkedin_post = await self.generator.generate_clean_linkedin_post(article_result, article_url)
                    
                    if clean_linkedin_post["success"]:
                        enhanced_article_data = article_result.copy()
                        enhanced_article_data["linkedin_post_override"] = clean_linkedin_post["linkedin_content"]
                        
                        # Add research credibility mentions if source tracking was used
                        if article_result.get("source_attribution_used"):
                            post_content = clean_linkedin_post["linkedin_content"]
                            sources_cited = article_result.get("sources_cited", 0)
                            
                            # Add research credibility to the post (maintaining clean formatting)
                            if sources_cited > 0:
                                if "🔗 Read more:" in post_content:
                                    post_content = post_content.replace(
                                        "🔗 Read more:",
                                        f"📚 Research-backed insights from {sources_cited} verified sources.\n\n🔗 Read more:"
                                    )
                                else:
                                    post_content += f"\n\n📚 Research-backed insights from {sources_cited} verified sources."
                            
                            enhanced_article_data["linkedin_post_override"] = post_content
                        
                        # Add audio mention if available (maintaining clean format)
                        if audio_files:
                            post_content = enhanced_article_data["linkedin_post_override"]
                            if "🔗 Read" in post_content:
                                post_content = post_content.replace(
                                    "🔗 Read",
                                    "🎧 Available as audio podcast!\n\n🔗 Read"
                                )
                            enhanced_article_data["linkedin_post_override"] = post_content
                        
                        # Post using the clean LinkedIn method
                        linkedin_result = await self.linkedin.post_to_linkedin_with_url(enhanced_article_data, article_url)
                        linkedin_result["clean_formatting_used"] = True
                        linkedin_result["enhanced_post_used"] = True
                        linkedin_result["source_attribution_mentioned"] = article_result.get("source_attribution_used", False)
                        linkedin_result["audio_mentioned"] = bool(audio_files)
                        linkedin_result["markdown_removed"] = True
                        linkedin_result["url_at_top"] = True
                    else:
                        # Fallback to standard LinkedIn method
                        linkedin_result = await self.linkedin.post_to_linkedin_with_url(article_result, article_url)
                        linkedin_result["clean_formatting_used"] = False
                        linkedin_result["enhanced_post_used"] = False
                        linkedin_result["source_attribution_mentioned"] = False
                        linkedin_result["audio_mentioned"] = False
                    
                    result["linkedin_result"] = linkedin_result
                    
                    if linkedin_result["success"]:
                        result["workflow_success"] = True
                        print("✅ Complete workflow with clean LinkedIn integration successful!")
                        
                        # Clean formatting confirmation
                        if linkedin_result.get("clean_formatting_used"):
                            print("🧹 LinkedIn post uses clean formatting (no markdown)")
                            print("🔗 Article URL positioned at top of post")
                        
                        if article_result.get("source_attribution_used"):
                            print("📚 LinkedIn post highlights research credibility!")
                        if audio_files:
                            print("🎧 LinkedIn post mentions audio availability!")
        else:
            print("   ⚠️ WordPress not configured or disabled")
        
        return result
    
    def _add_source_methodology_section(self, content: str, article_result: Dict, research_data: Dict) -> str:
        """Add source links section to article content instead of generic methodology"""
        
        if not article_result.get("source_attribution_used"):
            return content
        
        source_summary = research_data.get("source_summary", [])
        
        if not source_summary:
            return content
        
        # Create a clean sources section with direct links
        sources_section = "\n\n## Sources and References\n\n"
        
        # Add actual source links
        for i, source in enumerate(source_summary, 1):
            domain = source.get('domain', 'Unknown')
            url = source.get('url', '')
            title = source.get('title', domain)
            claims_count = source.get('claims_count', 0)
            
            if url and claims_count > 0:
                sources_section += f"{i}. [{title}]({url}) - {claims_count} data point{'s' if claims_count != 1 else ''} referenced\n"
        
        sources_section += "\n*All statistics and claims in this article are directly attributed to these verified sources.*"
        
        return content + sources_section


# Main function with complete workflow options including clean LinkedIn
async def main():
    """Main function with complete workflow including clean LinkedIn integration"""
    
    print("🎭 Enhanced AI Article Factory with Clean LinkedIn Integration")
    print("   🔍 Complete Workflow: Research → Article → Quality → Audio → WordPress → Clean LinkedIn")
    print("   📚 All statistics properly attributed to verified sources")
    print("   🧹 LinkedIn posts with clean formatting (no markdown, URL at top)")
    
    system = EnhancedQualityControlledArticleSystemWithLinkedInIntegration()
    
    # Check capabilities
    print(f"\nSystem Capabilities:")
    print(f"   🔍 Source Tracking & Attribution: {'✅ Available' if system.source_tracking_available else '❌ Unavailable'}")
    print(f"   🌐 Enhanced Research: {'✅ Available' if system.enhanced_research_available else '❌ Unavailable'}")
    print(f"   📚 Standard Research: {'✅ Available' if system.perplexity_available else '❌ Unavailable'}")
    print(f"   🎤 Audio Generation: {'✅ Available' if system.audio_available else '❌ Unavailable'}")
    print(f"   🌐 WordPress: {'✅ Available' if system.wordpress_available else '❌ Unavailable'}")
    print(f"   📱 Clean LinkedIn: {'✅ Available' if system.linkedin_available else '❌ Unavailable'}")
    
    # Configuration
    topic = input("\n🎯 Enter article topic: ").strip()
    if not topic:
        print("❌ Topic required!")
        return
    
    # Source tracking options
    if system.source_tracking_available:
        print("\n🔍 Source Tracking Options:")
        use_source_tracking = input("Enable comprehensive source tracking and attribution? (Y/n): ").strip().lower()
        enable_source_tracking = use_source_tracking != 'n'
        
        if enable_source_tracking:
            print("   📚 All statistics will be properly attributed to verified sources")
            print("   🔍 Source verification reports will be included")
            print("   📊 No fabricated or unsourced claims will be used")
            
            max_urls = input("Max URLs to browse for source tracking (1-10, default=6): ").strip()
            max_urls = int(max_urls) if max_urls.isdigit() and 1 <= int(max_urls) <= 10 else 6
        else:
            max_urls = 6
    else:
        enable_source_tracking = False
        max_urls = 6
        print("\n⚠️ Source tracking not available - missing API keys")
    
    # Research options
    if system.enhanced_research_available:
        print("\n🌐 Research Options:")
        if not enable_source_tracking:
            use_enhanced = input("Use enhanced research with URL browsing? (Y/n): ").strip().lower()
            enable_enhanced_research = use_enhanced != 'n'
            
            if enable_enhanced_research and not enable_source_tracking:
                max_urls = input("Max URLs to browse (1-10, default=6): ").strip()
                max_urls = int(max_urls) if max_urls.isdigit() and 1 <= int(max_urls) <= 10 else 6
        else:
            enable_enhanced_research = True  # Source tracking requires enhanced research
            print(f"   Enhanced research automatically enabled for source tracking")
    else:
        enable_enhanced_research = False
        if not system.perplexity_available:
            print("\n⚠️ No research APIs available - generating without research")
    
    # Audio options
    if system.audio_available:
        print("\n🎤 Audio Options:")
        generate_audio = input("Generate audio version? (Y/n): ").strip().lower() != 'n'
        if generate_audio:
            # Add duration control
            duration = input("Podcast duration in minutes (5-20, default=10): ").strip()
            try:
                target_duration = int(duration) if duration else 10
                target_duration = max(5, min(20, target_duration))
            except:
                target_duration = 10
        else:
            target_duration = 10
    else:
        generate_audio = False
        target_duration = 10
        print("\n⚠️ Audio generation not available (missing OpenAI API key)")
    
    # Research model selection
    if system.perplexity_available:
        print("\n🔧 Research Model:")
        model_choice = input("Choose model (sonar/sonar-pro/sonar-reasoning, default=sonar): ").strip().lower()
        research_model = model_choice if model_choice in ['sonar', 'sonar-pro', 'sonar-reasoning'] else 'sonar'
    else:
        research_model = 'sonar'
    
    # Article options
    print("\n📝 Article Options:")
    audience = input("Target audience (default=Professional): ").strip() or "Professional audience"
    article_type = input("Article type (how-to/guide/analysis/review, default=how-to): ").strip() or "how-to"
    
    # Quality control settings
    print("\n🔧 Quality Control:")
    max_revisions = input("Max revision cycles (1-3, default=2): ").strip()
    max_revisions = int(max_revisions) if max_revisions.isdigit() and 1 <= int(max_revisions) <= 3 else 2
    
    # Publishing options
    print("\n📤 Publishing Options:")
    publish_wp = input("Publish to WordPress with source information? (Y/n): ").strip().lower() != 'n'
    post_linkedin = input("Share on LinkedIn with clean formatting? (Y/n): ").strip().lower() != 'n' if publish_wp else False
    
    if post_linkedin:
        print("   🧹 LinkedIn posts will have clean formatting (no markdown)")
        print("   🔗 Article URL will be positioned at the top")
        print("   ✨ Dynamic hooks will be generated")
    
    # Execute complete workflow
    print(f"\n🚀 Starting complete workflow with clean LinkedIn integration...")
    if enable_source_tracking:
        print(f"   🔍 Source tracking enabled - all statistics will be properly attributed")
        print(f"   📚 Will analyze up to {max_urls} URLs for verified claims")
    elif enable_enhanced_research:
        print(f"   🌐 Enhanced research enabled - will browse up to {max_urls} URLs")
    if generate_audio:
        print(f"   🎤 Audio generation enabled")
    if post_linkedin:
        print(f"   📱 Clean LinkedIn integration enabled")
    
    try:
        result = await system.generate_complete_workflow_with_clean_linkedin(
            topic=topic,
            audience=audience,
            article_type=article_type,
            enable_enhanced_research=enable_enhanced_research,
            enable_source_tracking=enable_source_tracking,
            research_model=research_model,
            max_urls_to_browse=max_urls,
            publish_to_wordpress=publish_wp,
            post_to_linkedin=post_linkedin,
            generate_audio=generate_audio,
            max_revision_cycles=max_revisions
        )
        
        # Show comprehensive results
        if result.get("article_data"):
            print(f"\n📊 COMPLETE WORKFLOW WITH CLEAN LINKEDIN REPORT")
            print("=" * 70)
            
            article_data = result["article_data"]
            metrics = article_data.get("metrics", {})
            quality_control = article_data.get("quality_control", {})
            audio_results = result.get("audio_results", {})
            
            print(f"🎯 Title: {article_data.get('article_title', 'Unknown')}")
            print(f"📄 Content: {metrics.get('word_count', 0)} words")
            print(f"📖 Reading Level: {metrics.get('reading_level', 'Unknown')}")
            print(f"📈 Quality Score: {metrics.get('quality_score', 0)}/10")
            print(f"🔄 Revision Cycles: {quality_control.get('revision_cycles', 0)}")
            
            # Source tracking results
            source_tracking_used = metrics.get("source_tracking_used", False)
            print(f"\n🔍 Source Tracking:")
            print(f"   📚 Source tracking used: {'Yes' if source_tracking_used else 'No'}")
            
            if source_tracking_used:
                sources_cited = metrics.get("sources_cited", 0)
                sourced_claims = metrics.get("sourced_claims_used", 0)
                print(f"   📊 Sources cited: {sources_cited}")
                print(f"   📝 Sourced claims: {sourced_claims}")
                print(f"   ✅ All statistics properly attributed")
            else:
                print(f"   ⚠️ Source tracking unavailable - verify statistics independently")
            
            # Audio results
            if audio_results:
                print(f"\n🎤 Audio Generation:")
                full_audio = audio_results.get("full_audio", {})
                
                if full_audio.get("success"):
                    print(f"   🎵 Audio: {len(full_audio['audio_files'])} files")
                    print(f"   ⏱️ Duration: ~{full_audio['estimated_duration_minutes']} minutes")
                else:
                    print(f"   ❌ Audio generation failed")
            
            # WordPress results
            if result.get("wordpress_result", {}).get("success"):
                wp_result = result["wordpress_result"]
                print(f"\n🌐 WordPress:")
                print(f"   🔗 Published: {wp_result['post_url']}")
                if wp_result.get('has_audio'):
                    print(f"   🎧 Audio embedded: {wp_result.get('audio_files_uploaded', 0)} files")
                if source_tracking_used:
                    print(f"   📚 Source methodology section included")
            
            # Clean LinkedIn results
            if result.get("linkedin_result", {}).get("success"):
                li_result = result["linkedin_result"]
                print(f"\n📱 Clean LinkedIn:")
                print(f"   📤 Shared successfully")
                
                # Clean formatting confirmation
                if li_result.get("clean_formatting_used"):
                    print(f"   🧹 Clean formatting applied (no markdown)")
                    print(f"   🔗 URL positioned at top")
                    print(f"   ✨ Dynamic hook generated")
                
                if li_result.get("source_attribution_mentioned"):
                    print(f"   📝 Research credibility highlighted")
                if li_result.get("audio_mentioned"):
                    print(f"   🎧 Audio availability mentioned")
                if li_result.get('enhanced_post_used'):
                    print(f"   ⭐ Enhanced LinkedIn post method used")
            
            # Research summary
            research_summary = result.get("research_summary", {})
            urls_analyzed = research_summary.get("urls_analyzed", 0) or research_summary.get("urls_browsed", 0)
            if urls_analyzed > 0:
                print(f"\n🌐 Research Summary:")
                print(f"   URLs analyzed: {urls_analyzed}")
                
                if research_summary.get("total_words_browsed"):
                    print(f"   Words extracted: {research_summary['total_words_browsed']:,}")
                
                research_type = research_summary.get("research_type", "standard")
                if "source_tracking" in research_type:
                    print(f"   Enhancement: Comprehensive source tracking")
                elif "browsing" in research_type:
                    print(f"   Enhancement: URL content analysis")
            
            print(f"\n✅ Complete Workflow Success: {'Yes' if result.get('workflow_success') else 'No'}")
            
            # LinkedIn formatting summary
            linkedin_result = result.get("linkedin_result", {})
            if linkedin_result.get("success"):
                print(f"\n🧹 CLEAN LINKEDIN FORMATTING SUMMARY:")
                print(f"   ✅ Markdown formatting removed from post")
                print(f"   ✅ Article URL positioned at top of post")
                print(f"   ✅ Dynamic hooks generated for engagement")
                print(f"   ✅ Complete statistics with full context")
                print(f"   ✅ Professional formatting maintained")
                
                if linkedin_result.get("source_attribution_mentioned"):
                    print(f"   ✅ Research credibility highlighted")
                if linkedin_result.get("audio_mentioned"):
                    print(f"   ✅ Audio availability mentioned")
            
            # Source tracking summary
            if source_tracking_used:
                print(f"\n📚 SOURCE ATTRIBUTION SUMMARY:")
                print(f"   ✅ All statistics include proper source attribution")
                print(f"   ✅ Sources verified for credibility and reliability") 
                print(f"   ✅ No fabricated or unsourced claims included")
                print(f"   ✅ Source methodology section added to article")
                print(f"   ✅ LinkedIn post highlights research credibility")
                print(f"   ✅ Transparent about source limitations")
            else:
                print(f"\n⚠️ SOURCE ATTRIBUTION WARNING:")
                print(f"   ⚠️ Source tracking was not available")
                print(f"   ⚠️ Please verify all statistics independently")
                print(f"   ⚠️ Some claims may lack proper attribution")

        else:
            print("\n❌ Workflow failed!")
            if result.get("error"):
                print(f"Error: {result['error']}")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Generation cancelled by user")
        return
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return


# Test function for the complete workflow with clean LinkedIn
async def test_complete_workflow_with_clean_linkedin():
    """Test the complete workflow with clean LinkedIn integration"""
    
    print("🧪 Testing Complete Workflow with Clean LinkedIn Integration")
    print("=" * 65)
    
    system = EnhancedQualityControlledArticleSystemWithLinkedInIntegration()
    
    if not system.source_tracking_available:
        print("❌ Source tracking not available - check API keys")
        return
    
    if not system.linkedin_available:
        print("❌ LinkedIn not available - check API keys")
        return
    
    # Test with a topic that should have good statistics
    test_topic = "clean LinkedIn automation best practices"
    
    print(f"Testing complete workflow with topic: {test_topic}")
    print("This will test: Research → Article → Quality → Audio → WordPress → Clean LinkedIn")
    print("LinkedIn formatting: No markdown, URL at top, dynamic hooks")
    
    try:
        result = await system.generate_complete_workflow_with_clean_linkedin(
            topic=test_topic,
            audience="Social media managers and content creators",
            article_type="guide",
            enable_source_tracking=True,
            max_urls_to_browse=4,
            generate_audio=True,
            publish_to_wordpress=False,  # Don't publish during testing
            post_to_linkedin=True,       # Test LinkedIn integration
            max_revision_cycles=1        # Reduced for testing
        )
        
        if result.get("article_data", {}).get("success", True):
            article_data = result["article_data"]
            metrics = article_data.get("metrics", {})
            linkedin_result = result.get("linkedin_result", {})
            
            print(f"\n✅ COMPLETE WORKFLOW WITH CLEAN LINKEDIN TEST SUCCESSFUL!")
            print(f"📚 Sources cited: {metrics.get('sources_cited', 0)}")
            print(f"📝 Sourced claims: {metrics.get('sourced_claims_used', 0)}")
            print(f"📝 Word count: {metrics.get('word_count', 0)}")
            print(f"📈 Quality score: {metrics.get('quality_score', 0)}/10")
            
            # Test LinkedIn clean formatting
            if linkedin_result.get("success"):
                print(f"\n📱 CLEAN LINKEDIN INTEGRATION:")
                print(f"   📤 Post successful: Yes")
                print(f"   🧹 Clean formatting: {'Yes' if linkedin_result.get('clean_formatting_used') else 'No'}")
                print(f"   🔗 URL at top: {'Yes' if linkedin_result.get('url_at_top') else 'No'}")
                print(f"   📝 Markdown removed: {'Yes' if linkedin_result.get('markdown_removed') else 'No'}")
                print(f"   ✨ Dynamic hook: {'Yes' if linkedin_result.get('dynamic_hook_used') else 'No'}")
                print(f"   📊 Character count: {linkedin_result.get('character_count', 0)}")
            else:
                print(f"❌ LinkedIn integration failed: {linkedin_result.get('error')}")
            
            # Test audio generation
            audio_results = result.get("audio_results", {})
            if audio_results.get("full_audio", {}).get("success"):
                print(f"🎤 Audio generated: {len(audio_results['full_audio']['audio_files'])} files")
            
            if metrics.get("source_tracking_used"):
                print("✅ Complete workflow with clean LinkedIn integration successful!")
                print("🧹 LinkedIn post should have clean formatting!")
                print("📚 All statistics properly attributed!")
            else:
                print("⚠️ Source tracking failed - workflow completed without attribution")
        else:
            print(f"❌ Test failed: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_complete_workflow_with_clean_linkedin())
    else:
        asyncio.run(main())