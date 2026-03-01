# enhanced_complete_article_system_with_audio.py - Your existing system with audio integration
import os
import json
import requests
import asyncio
import openai
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import all your existing classes unchanged
# from complete_article_system import ArticleQualityAgent, EnhancedArticleGenerator

class ArticleQualityAgent:
    """Agent responsible for improving article quality, readability, and structure"""
    
    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
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

Rewrite the entire article content with improved readability:"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": readability_prompt}],
                max_tokens=4000,
                temperature=0.3
            )
            
            improved_content = response.choices[0].message.content.strip()
            
            return {
                "success": True,
                "improved_content": improved_content,
                "improvements_made": "Simplified language, improved flow, enhanced readability"
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
  "main_problems": ["top 3 most critical issues"]
}}

Analyze thoroughly and provide detailed feedback:"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": quality_check_prompt}],
                max_tokens=2000,
                temperature=0.1
            )
            
            quality_analysis = response.choices[0].message.content.strip()
            
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
                    "recommendations": ["Manual review needed"]
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
                    "recommendations": ["Manual review needed"]
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

ORIGINAL CONTENT:
{article_content}

Return the COMPLETE corrected content with all issues fixed (no title):"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": fix_prompt}],
                max_tokens=4000,
                temperature=0.2
            )
            
            fixed_content = response.choices[0].message.content.strip()
            
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

class EnhancedArticleGenerator:
    """Enhanced article generator with separate title and content generation"""
    
    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.quality_agent = ArticleQualityAgent()
    
    async def generate_article_with_research(self, topic: str, research_data: Dict, 
                                           audience: str = None, article_type: str = "how-to") -> Dict:
        """Generate article using research data - content first, then title"""
        
        print("📝 Generating article with research context...")
        
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
            "research_data": research_data
        }
    
    async def _generate_article_content(self, topic: str, research_context: str, 
                                      audience: str, article_type: str) -> str:
        """Generate pure article content without any title"""
        
        content_prompt = f"""You are an expert content writer. Create comprehensive article content about "{topic}" using the provided research context.

RESEARCH CONTEXT:
{research_context}

CONTENT REQUIREMENTS:
- Target audience: {audience or "Professional audience"}
- Article type: {article_type}
- Length: 1500-2500 words
- Start directly with an engaging introduction paragraph
- Include 4-6 main sections with descriptive H2 headings (## Section Name)
- End with ONE conclusion section (## Conclusion)
- Writing style: Professional but accessible
- Include actionable insights from the research
- Use statistics and trends from the research naturally

STRUCTURE FORMAT:
1. Introduction paragraph (engaging opener, no heading)
2. ## Understanding [Topic Aspect 1]
3. ## Key Components of [Topic]
4. ## Implementation Strategies
5. ## Best Practices and Benefits
6. ## Common Challenges and Solutions
7. ## Conclusion

CRITICAL INSTRUCTIONS:
- Do NOT include any title or main heading
- Start immediately with introduction content
- Use only H2 headings (##) for main sections
- Make content comprehensive and valuable
- Include practical examples and actionable advice

Write the complete article content (no title, just content):"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": content_prompt}],
                max_tokens=4000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean any potential title remnants (just in case)
            content = self._clean_content_only(content)
            
            return content
            
        except Exception as e:
            print(f"   ❌ Content generation failed: {str(e)}")
            return None
    
    async def _generate_title_from_content(self, article_content: str, topic: str) -> str:
        """Generate compelling title based on the actual article content"""
        
        title_prompt = f"""Analyze this article content about "{topic}" and create a compelling title.

ARTICLE CONTENT:
{article_content[:1500]}...

TITLE REQUIREMENTS:
- Under 60 characters for SEO
- Engaging and professional
- Accurately reflects the content
- Clear value proposition
- No subtitle or secondary text
- Should entice readers to click

Based on the actual content, create ONE perfect title:"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": title_prompt}],
                max_tokens=100,
                temperature=0.4
            )
            
            title = response.choices[0].message.content.strip()
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
CONTENT PREVIEW: {article_content[:800]}...

META DESCRIPTION REQUIREMENTS:
- Under 160 characters
- Compelling and descriptive
- Includes main value proposition
- Encourages clicks
- Summarizes key benefits

Create the meta description:"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": meta_prompt}],
                max_tokens=100,
                temperature=0.4
            )
            
            return response.choices[0].message.content.strip().replace('"', '')
            
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
                # Skip lines that look like titles (short, no punctuation, all caps, etc.)
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
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": outline_prompt}],
                max_tokens=1000,
                temperature=0.2
            )
            
            outline_text = response.choices[0].message.content.strip()
            
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
    
    async def generate_enhanced_linkedin_post(self, article_data: Dict, article_url: str) -> Dict:
        """Generate LinkedIn post using separate title and content variables"""
        
        topic = article_data.get("topic", "")
        article_content = article_data.get("article_content", "")
        article_title = article_data.get("article_title", "")  # Use separate title variable
        research_data = article_data.get("research_data", {})
        
        # Check for override content first
        if "linkedin_post_override" in article_data:
            return {
                "success": True,
                "linkedin_content": article_data["linkedin_post_override"],
                "character_count": len(article_data["linkedin_post_override"]),
                "has_complete_stats": True,
                "source": "override"
            }
        
        linkedin_prompt = f"""Create an engaging LinkedIn post about "{topic}".

ARTICLE TITLE: {article_title}
ARTICLE URL: {article_url}
CONTENT PREVIEW: {article_content[:600]}...

REQUIREMENTS:
- Engaging hook about the topic
- Brief value proposition from the article
- 2-3 complete statistics with full context (no bare percentages)
- Engagement question
- Relevant hashtags (3-4)
- Article link with call-to-action
- Under 1300 characters total

EXAMPLE COMPLETE STATISTICS:
• Security awareness training reduces phishing success rates by 70%
• Organizations with basic cybersecurity measures prevent 60% of attacks
• Password managers eliminate 85% of credential-related incidents

Create the LinkedIn post:"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": linkedin_prompt}],
                max_tokens=800,
                temperature=0.4
            )
            
            linkedin_content = response.choices[0].message.content.strip()
            
            # Ensure URL is included
            if article_url not in linkedin_content:
                linkedin_content += f"\n\n🔗 Read the full article: {article_url}"
            
            return {
                "success": True,
                "linkedin_content": linkedin_content,
                "character_count": len(linkedin_content),
                "has_complete_stats": True
            }
            
        except Exception as e:
            # Fallback post
            fallback_post = f"""🔐 New insights on {topic}.

"{article_title}" provides practical guidance for digital protection that anyone can implement.

💡 Key insights:
• Security awareness training reduces phishing success rates by 70%
• Basic cybersecurity measures prevent 60% of common attacks
• Password managers eliminate 85% of credential-related incidents

What's your biggest cybersecurity challenge? 👇

#Cybersecurity #DigitalSafety #InfoSec #Technology

🔗 Read more: {article_url}"""

            return {
                "success": False,
                "error": str(e),
                "linkedin_content": fallback_post,
                "character_count": len(fallback_post),
                "fallback_used": True,
                "has_complete_stats": True
            }



class DeepLearningArticleGenerator(EnhancedArticleGenerator):
    """Your existing DeepLearningArticleGenerator - NO CHANGES"""
    
    async def generate_article_with_enhanced_research(self, topic: str, research_data: Dict, 
                                                    audience: str = None, article_type: str = "how-to") -> Dict:
        """Generate article using enhanced research data that includes URL browsing"""
        
        print("📝 Generating article with enhanced research context...")
        
        # Check research type
        research_type = research_data.get("research_type", "standard")
        is_enhanced_research = research_type in ["enhanced_deep_research_with_browsing", "deep_research_with_browsing"]
        
        sources = []  # browsed sources used for citation references

        if is_enhanced_research:
            research_context, sources = self._build_enhanced_research_context(research_data)
            urls_browsed = research_data.get("urls_analyzed", 0)
            words_extracted = research_data.get("total_words_browsed", 0)
            print(f"   🌐 Using enhanced research: {urls_browsed} URLs browsed, {words_extracted} words extracted")
            print(f"   📎 {len(sources)} sources available for citations")
        elif research_data.get("research_type") == "deep_learning":
            research_context = self._build_deep_research_context(research_data)
            print(f"   🧠 Using deep learning from {research_data.get('articles_read', 0)} articles")
        else:
            research_context = self._build_research_context(
                research_data.get("research_summary", ""),
                research_data.get("web_sources_analyzed", []),
                research_data.get("recent_trends", []),
                research_data.get("key_statistics", []),
                research_data.get("content_gaps", [])
            )
            print("   📚 Using standard research context")

        # Generate content with enhanced research context
        article_content = await self._generate_article_content_with_enhanced_insights(
            topic, research_context, audience, article_type, is_enhanced_research
        )

        if not article_content:
            return {"success": False, "error": "Failed to generate article content"}

        # ── Append ## References section ─────────────────────────────────────
        if sources:
            refs = "\n\n## References\n"
            for i, source in enumerate(sources):
                title = source.get("title") or "Source"
                url = source.get("url", "")
                author = source.get("author", "")
                author_str = f" — {author}" if author else ""
                refs += f"\n[{i + 1}] [{title}]({url}){author_str}"
            article_content = article_content + refs
            print(f"   📚 Appended References section with {len(sources)} sources")

        print("   ✅ Article content generated with enhanced insights and citations")
        
        # Generate title based on the enriched content
        article_title = await self._generate_title_from_content(article_content, topic)
        print(f"   📋 Generated title: {article_title}")
        
        # Generate meta description
        meta_description = await self._generate_meta_description_from_content(article_content, article_title)
        
        # Generate article outline
        outline = await self._generate_article_outline(article_content, topic)
        
        return {
            "success": True,
            "article_content": article_content,
            "article_title": article_title,
            "title_options": [article_title],
            "unified_title": article_title,
            "meta_description": meta_description,
            "outline": outline,
            "topic": topic,
            "audience": audience,
            "article_type": article_type,
            "research_integrated": True,
            "enhanced_research_used": is_enhanced_research,
            "urls_browsed": research_data.get("urls_analyzed", 0),
            "research_data": research_data
        }
    
    def _build_enhanced_research_context(self, research_data: Dict):
        """Build research context from enhanced URL browsing data.

        Returns a tuple (context_string, sources_list) where sources_list is the
        list of browsed source dicts used to generate the numbered citation list
        appended to context_string.
        """

        context_parts = []

        # Comprehensive themes from synthesis
        themes = research_data.get("comprehensive_themes", [])
        if themes:
            context_parts.append("COMPREHENSIVE THEMES:\n" + "\n".join(f"- {theme}" for theme in themes))

        # Evidence-based findings
        findings = research_data.get("evidence_based_findings", [])
        if findings:
            context_parts.append("EVIDENCE-BASED FINDINGS:\n" + "\n".join(f"- {finding}" for finding in findings))

        # Novel insights from browsed content
        novel_insights = research_data.get("novel_insights", [])
        if novel_insights:
            context_parts.append("NOVEL INSIGHTS FROM BROWSED SOURCES:\n" + "\n".join(f"- {insight}" for insight in novel_insights))

        # Data-driven points with context
        data_points = research_data.get("data_driven_points", [])
        if data_points:
            context_parts.append("DATA-DRIVEN INSIGHTS:\n" + "\n".join(f"- {point}" for point in data_points))

        # Practical framework
        framework = research_data.get("practical_framework", [])
        if framework:
            context_parts.append("PRACTICAL FRAMEWORK:\n" + "\n".join(f"- {item}" for item in framework))

        # Expert perspectives from browsed content
        expert_perspectives = research_data.get("expert_perspectives", [])
        if expert_perspectives:
            context_parts.append("EXPERT PERSPECTIVES:\n" + "\n".join(f"- {perspective}" for perspective in expert_perspectives))

        # Implementation strategies
        strategies = research_data.get("implementation_strategies", [])
        if strategies:
            context_parts.append("IMPLEMENTATION STRATEGIES:\n" + "\n".join(f"- {strategy}" for strategy in strategies))

        # Content gaps to address
        gaps = research_data.get("content_gaps", [])
        if gaps:
            context_parts.append("CONTENT GAPS TO ADDRESS:\n" + "\n".join(f"- {gap}" for gap in gaps))

        # Insights from browsed content
        browsed_insights = research_data.get("browsed_insights", [])
        if browsed_insights:
            context_parts.append("INSIGHTS FROM BROWSED ARTICLES:\n" + "\n".join(f"- {insight}" for insight in browsed_insights[:8]))

        # Unique data points
        unique_data = research_data.get("unique_data_points", [])
        if unique_data:
            context_parts.append("UNIQUE DATA POINTS:\n" + "\n".join(f"- {data}" for data in unique_data))

        # Practical applications
        applications = research_data.get("practical_applications", [])
        if applications:
            context_parts.append("PRACTICAL APPLICATIONS:\n" + "\n".join(f"- {app}" for app in applications))

        # ── Numbered source list for citation markers ─────────────────────────
        sources = [s for s in research_data.get("browsed_sources", []) if s.get("url")]
        if sources:
            source_lines = "\n".join(
                f"[{i + 1}] {s.get('title', 'Untitled')} — {s.get('url', '')}"
                for i, s in enumerate(sources)
            )
            context_parts.append(
                "NUMBERED SOURCES FOR CITATION (add [N] after sentences that draw on these):\n"
                + source_lines
            )

        return "\n\n".join(context_parts), sources
    
    def _build_deep_research_context(self, research_data: Dict) -> str:
        """Build enhanced research context from deep learning data (existing method)"""
        
        context_parts = []
        
        # Core themes and consensus
        core_themes = research_data.get("core_themes", [])
        if core_themes:
            context_parts.append(f"CORE THEMES IDENTIFIED:\n" + "\n".join(f"- {theme}" for theme in core_themes))
        
        consensus_findings = research_data.get("consensus_findings", [])
        if consensus_findings:
            context_parts.append(f"EXPERT CONSENSUS:\n" + "\n".join(f"- {finding}" for finding in consensus_findings))
        
        # Deep insights from article analysis
        deep_insights = research_data.get("deep_insights", [])
        if deep_insights:
            context_parts.append(f"DEEP INSIGHTS FROM ARTICLES:\n" + "\n".join(f"- {insight}" for insight in deep_insights[:10]))
        
        # Evidence-based statistics
        evidence_stats = research_data.get("evidence_based_statistics", [])
        if evidence_stats:
            context_parts.append(f"EVIDENCE-BASED STATISTICS:\n" + "\n".join(f"- {stat}" for stat in evidence_stats[:8]))
        
        # Novel insights not commonly covered
        novel_insights = research_data.get("novel_insights", [])
        if novel_insights:
            context_parts.append(f"NOVEL INSIGHTS FOR DIFFERENTIATION:\n" + "\n".join(f"- {insight}" for insight in novel_insights))
        
        # Advanced considerations
        advanced_considerations = research_data.get("advanced_considerations", [])
        if advanced_considerations:
            context_parts.append(f"ADVANCED CONSIDERATIONS:\n" + "\n".join(f"- {consideration}" for consideration in advanced_considerations))
        
        # Knowledge gaps to address
        knowledge_gaps = research_data.get("knowledge_gaps", [])
        if knowledge_gaps:
            context_parts.append(f"KNOWLEDGE GAPS TO ADDRESS:\n" + "\n".join(f"- {gap}" for gap in knowledge_gaps))
        
        # Content opportunities
        content_opportunities = research_data.get("content_opportunities", [])
        if content_opportunities:
            context_parts.append(f"CONTENT DIFFERENTIATION OPPORTUNITIES:\n" + "\n".join(f"- {opportunity}" for opportunity in content_opportunities))
        
        # Practical applications
        practical_applications = research_data.get("practical_applications", [])
        if practical_applications:
            context_parts.append(f"PRACTICAL APPLICATIONS:\n" + "\n".join(f"- {application}" for application in practical_applications[:6]))
        
        return "\n\n".join(context_parts)
    
    async def _generate_article_content_with_enhanced_insights(self, topic: str, research_context: str, 
                                                            audience: str, article_type: str, is_enhanced_research: bool) -> str:
        """Generate article content using enhanced research insights"""
        
        if is_enhanced_research:
            content_prompt = f"""You are an expert content writer creating an article about "{topic}" using comprehensive research that includes analysis of multiple full articles and web sources.

ENHANCED RESEARCH CONTEXT (from URL browsing and deep analysis):
{research_context}

PREMIUM CONTENT REQUIREMENTS:
- Target audience: {audience or "Professional audience"}
- Article type: {article_type}
- Length: 2500-3500 words (comprehensive due to rich research)
- Start with an engaging introduction that establishes unique value proposition
- Include 7-9 main sections with descriptive H2 headings (## Section Name)
- Integrate novel insights and expert perspectives throughout
- Use data-driven points and evidence naturally within content
- Address identified content gaps with fresh perspectives
- Include comprehensive practical applications and implementation strategies
- Leverage browsed content insights for depth and authenticity
- End with ONE comprehensive conclusion that synthesizes all learnings

UNIQUE VALUE CREATION:
- Go beyond surface-level coverage using enhanced research insights
- Include perspectives from multiple authoritative sources
- Integrate expert viewpoints with practical frameworks
- Provide advanced, actionable guidance based on comprehensive analysis
- Address knowledge gaps identified through research
- Use novel insights to differentiate from existing content

ENHANCED STRUCTURE FORMAT:
1. Introduction (compelling opener highlighting unique research-backed value)
2. ## Foundational Understanding (comprehensive themes and evidence-based findings)
3. ## Current Landscape Analysis (data-driven insights and expert perspectives)
4. ## Advanced Methodologies and Frameworks (practical frameworks from research)
5. ## Evidence-Based Implementation Strategies (implementation strategies)
6. ## Addressing Critical Challenges (content gaps and novel solutions)
7. ## Expert Insights and Best Practices (expert perspectives and applications)
8. ## Future Considerations and Trends (forward-looking insights)
9. ## Comprehensive Action Plan (synthesized practical guidance)
10. ## Conclusion (comprehensive synthesis of enhanced research)

CRITICAL INSTRUCTIONS:
- Do NOT include any title or main heading
- Start immediately with introduction content
- Use only H2 headings (##) for main sections
- Integrate research insights naturally, not as obvious lists
- Create content that's significantly more insightful than typical coverage
- Ensure every section adds unique value based on enhanced research
- When a sentence uses a specific fact, statistic, or claim traceable to one of the NUMBERED SOURCES above, append the citation marker immediately after that sentence — e.g. "...grew by 40% in 2024. [1]" or "...according to recent industry analysis. [3]"
- Only cite where genuinely applicable — not every sentence needs a marker
- Do NOT add a References section; that will be appended automatically

Write comprehensive article content that fully leverages the enhanced research:"""
        
        elif research_context and "DEEP INSIGHTS FROM ARTICLES" in research_context:
            # Deep research prompt (existing)
            content_prompt = f"""You are an expert content writer creating an article about "{topic}" using comprehensive research from multiple full articles.

DEEP RESEARCH CONTEXT:
{research_context}

ENHANCED CONTENT REQUIREMENTS:
- Target audience: {audience or "Professional audience"}
- Article type: {article_type}
- Length: 2000-3000 words (longer due to richer research)
- Start with an engaging introduction that hints at unique insights
- Include 6-8 main sections with descriptive H2 headings (## Section Name)
- Integrate novel insights and advanced considerations throughout
- Use evidence-based statistics naturally within the content
- Address knowledge gaps identified in research
- Include practical applications and real-world examples
- End with ONE comprehensive conclusion that synthesizes learnings

UNIQUE VALUE CREATION:
- Go beyond surface-level coverage using the deep insights provided
- Include perspectives and considerations not commonly discussed
- Integrate expert consensus with novel viewpoints
- Provide advanced, actionable guidance based on multiple sources
- Address the knowledge gaps identified in research

STRUCTURE FORMAT:
1. Introduction (engaging opener highlighting unique value)
2. ## Foundational Understanding (core themes and consensus)
3. ## Current Landscape Analysis (evidence-based insights)
4. ## Advanced Methodologies (novel approaches from research)
5. ## Implementation Framework (practical applications)
6. ## Addressing Common Challenges (gap-filling insights)
7. ## Future Considerations (advanced considerations)
8. ## Best Practices and Recommendations (synthesized guidance)
9. ## Conclusion (comprehensive synthesis)

CRITICAL INSTRUCTIONS:
- Do NOT include any title or main heading
- Start immediately with introduction content
- Use only H2 headings (##) for main sections
- Integrate research insights naturally, not as obvious lists
- Create content that's more insightful than typical coverage
- Ensure every section adds unique value based on the research

Write comprehensive article content that leverages the deep research:"""
        else:
            # Standard research prompt (existing)
            content_prompt = f"""You are an expert content writer. Create comprehensive article content about "{topic}" using the provided research context.

RESEARCH CONTEXT:
{research_context}

CONTENT REQUIREMENTS:
- Target audience: {audience or "Professional audience"}
- Article type: {article_type}
- Length: 1500-2500 words
- Start directly with an engaging introduction paragraph
- Include 4-6 main sections with descriptive H2 headings (## Section Name)
- End with ONE conclusion section (## Conclusion)
- Writing style: Professional but accessible
- Include actionable insights from the research
- Use statistics and trends from the research naturally

CRITICAL INSTRUCTIONS:
- Do NOT include any title or main heading
- Start immediately with introduction content
- Use only H2 headings (##) for main sections
- Make content comprehensive and valuable

Write the complete article content (no title, just content):"""

        try:
            # Use more tokens for enhanced research
            max_tokens = 6000 if is_enhanced_research else (5000 if "DEEP INSIGHTS" in research_context else 4000)
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": content_prompt}],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip()
            content = self._clean_content_only(content)
            
            return content
            
        except Exception as e:
            print(f"   ❌ Content generation failed: {str(e)}")
            return None

    # Legacy method compatibility
    async def generate_article_with_deep_research(self, topic: str, research_data: Dict, 
                                                audience: str = None, article_type: str = "how-to") -> Dict:
        """Legacy method - now routes to enhanced research method"""
        return await self.generate_article_with_enhanced_research(topic, research_data, audience, article_type)


class EnhancedQualityControlledArticleSystemWithAudio:
    """Your existing system enhanced with audio generation - MINIMAL CHANGES"""
    
    def __init__(self):
        # All your existing imports and initialization
        from enhanced_perplexity_web_researcher import EnhancedPerplexityWebResearcher
        from personal_social_media_poster import EnhancedLinkedInPoster
        from elevenlabs_audio_generator import BlogAudioGenerator
        from audio_enhanced_wordpress_publisher import AudioEnhancedWordPressPublisher
        
        self.researcher = EnhancedPerplexityWebResearcher()
        self.generator = DeepLearningArticleGenerator()
        self.linkedin = EnhancedLinkedInPoster()
        
        # NEW: Audio components
        self.audio_generator = BlogAudioGenerator("iZURAYccQtQd12U8kEcq")  # custom voice
        self.wordpress = AudioEnhancedWordPressPublisher()  # Enhanced version
        
        # Check system availability (existing + audio)
        self.perplexity_available = bool(self.researcher.api_key)
        self.openai_available = bool(os.getenv('OPENAI_API_KEY'))
        self.wordpress_available = bool(self.wordpress.access_token)
        self.linkedin_available = 'linkedin_personal' in self.linkedin.enabled_platforms
        self.enhanced_research_available = self.perplexity_available and self.openai_available
        
        # NEW: Audio availability check
        self.audio_available = self.audio_generator.available
    
    # All your existing helper methods remain exactly the same
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

    # MAIN METHOD: Your existing method with audio integration
    async def generate_enhanced_quality_article(self, topic: str, audience: str = None, article_type: str = "how-to",
                                              enable_enhanced_research: bool = True, research_model: str = "sonar",
                                              max_urls_to_browse: int = 6, publish_to_wordpress: bool = True, 
                                              wordpress_status: str = "publish", post_to_linkedin: bool = True, 
                                              max_revision_cycles: int = 2,
                                              # NEW: Audio parameters
                                              generate_audio: bool = True, audio_summary: bool = True,
                                              audio_output_dir: str = "audio_output") -> Dict:
        """Your existing method enhanced with audio generation"""
        
        print(f"\n🎭 Starting enhanced article generation for: {topic}")
        if enable_enhanced_research and self.enhanced_research_available:
            print("   🌐 Enhanced Research: URLs → Content Analysis → Synthesis → Article → Quality → Audio → Publish")
        else:
            print("   📚 Standard: Research → Content → Title → Quality → Audio → Publish")
        
        # PHASE 1-4: All your existing workflow UNCHANGED
        # Step 1: Enhanced Research with URL Browsing
        research_data = {}
        if enable_enhanced_research and self.enhanced_research_available:
            print("🌐 Phase 1: Conducting enhanced research with URL browsing...")
            try:
                self.researcher.set_model(research_model)
                research_data = await self.researcher.deep_research_topic_with_browsing(
                    topic, max_urls_to_browse=max_urls_to_browse
                )
                urls_browsed = research_data.get('urls_analyzed', 0)
                words_extracted = research_data.get('total_words_browsed', 0)
                print(f"   ✅ Enhanced research complete! Browsed {urls_browsed} URLs, extracted {words_extracted} words")
            except Exception as e:
                print(f"   ⚠️ Enhanced research failed: {str(e)}")
                print("   📚 Falling back to standard research...")
                enable_enhanced_research = False
        
        if not enable_enhanced_research or not self.enhanced_research_available:
            if self.perplexity_available:
                print("📚 Phase 1: Conducting standard research...")
                try:
                    self.researcher.set_model(research_model)
                    research_results = await self.researcher.research_topic_comprehensive(topic)
                    research_data = self.researcher.format_research_for_article_generation(research_results)
                    self.researcher.save_research_data(research_results)
                    print(f"   ✅ Standard research complete! Found {research_data.get('sources_analyzed', 0)} sources")
                except Exception as e:
                    print(f"   ⚠️ Research failed: {str(e)}")
                    research_data = {"web_research_enabled": False}
            else:
                print("   ⚠️ No research API available, generating without research")
                research_data = {"web_research_enabled": False}
        
        # Step 2: Generate Article with Enhanced Research
        print("📝 Phase 2: Generating content with enhanced research...")
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
        if article_result.get("enhanced_research_used"):
            print(f"   🌐 Enhanced research insights integrated from {article_result.get('urls_browsed', 0)} URLs")
        
        revision_cycle = 0
        quality_logs = []
        
        # Step 3: Quality Control Loop (UNCHANGED)
        while revision_cycle < max_revision_cycles:
            revision_cycle += 1
            print(f"\n🔧 Phase 3.{revision_cycle}: Quality control check...")
            
            quality_check = await self.generator.quality_agent.check_article_quality(current_content, topic)
            
            if quality_check["success"]:
                quality_analysis = quality_check["quality_analysis"]
                quality_logs.append(quality_analysis)
                
                print(f"   📊 Quality: {quality_analysis.get('overall_quality', 'unknown')}")
                print(f"   📈 Completeness: {quality_analysis.get('completeness_score', 0)}/10")
                
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
                    "needs_revision": False
                })
                break
        
        # Step 4: Final Readability Enhancement
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
            "enhanced_research_used": article_result.get("enhanced_research_used", False)
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
            "enhanced_research_used": article_result.get("enhanced_research_used", False),
            "urls_browsed": article_result.get("urls_browsed", 0),
            "research_enhancement_level": "enhanced_url_browsing" if article_result.get("enhanced_research_used") else "standard"
        }
        
        # NEW PHASE 5: Audio Generation (INSERT HERE - between quality control and publishing)
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
                print(f"   ✅ Full audio: {len(audio_result['audio_files'])} files")
                print(f"   ⏱️ Duration: ~{audio_result['estimated_duration_minutes']} minutes")
            else:
                print(f"   ❌ Full audio generation failed: {audio_result.get('error')}")
            
            # Generate summary audio
            if audio_summary:
                summary_result = await self.audio_generator.generate_audio_summary(
                    article_result, summary_length="medium", output_dir=audio_output_dir
                )
                audio_results["summary_audio"] = summary_result
                
                if summary_result["success"]:
                    audio_files.append(summary_result["audio_file"])
                    print(f"   ✅ Summary audio: ~{summary_result['estimated_duration_minutes']} minutes")
                else:
                    print(f"   ❌ Summary audio generation failed: {summary_result.get('error')}")
        else:
            if not self.audio_available:
                print("\n⚠️ Phase 5: Audio generation skipped (not available)")
            else:
                print("\n⚠️ Phase 5: Audio generation skipped (disabled)")
        
        # PHASE 6: WordPress Publishing with Audio (ENHANCED)
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
            print("🌐 Phase 6: Publishing to WordPress with audio integration...")
            print(f"   📋 Title: {final_title}")
            print(f"   📄 Content: {len(final_content)} chars")
            print(f"   🎵 Audio files: {len(audio_files)}")
            if article_result.get("enhanced_research_used"):
                print(f"   🌐 Enhanced with {article_result.get('urls_browsed', 0)} browsed URLs")
            
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
                
                # Share on LinkedIn with audio mention
                if post_to_linkedin and self.linkedin_available:
                    print("📱 Phase 7: Sharing on LinkedIn with audio mention...")
                    
                    enhanced_post = await self.generator.generate_enhanced_linkedin_post(article_result, article_url)
                    
                    # Add audio mention to LinkedIn post if audio was generated
                    if audio_files and enhanced_post["success"]:
                        post_content = enhanced_post["linkedin_content"]
                        
                        # Add audio mention before the URL
                        if "📗 Read more:" in post_content:
                            post_content = post_content.replace(
                                "📗 Read more:",
                                "🎧 This article is also available as an audio version on the blog!\n\n📗 Read or listen:"
                            )
                        else:
                            post_content += "\n\n🎧 Audio version available on the blog!"
                        
                        enhanced_post["linkedin_content"] = post_content
                        enhanced_post["includes_audio_mention"] = True
                    
                    if enhanced_post["success"]:
                        enhanced_article_data = article_result.copy()
                        enhanced_article_data["linkedin_post_override"] = enhanced_post["linkedin_content"]
                        
                        linkedin_result = await self.linkedin.post_to_linkedin_with_url(enhanced_article_data, article_url)
                        linkedin_result["enhanced_post_used"] = True
                        linkedin_result["enhanced_research_used"] = article_result.get("enhanced_research_used", False)
                        linkedin_result["audio_mentioned"] = enhanced_post.get("includes_audio_mention", False)
                    else:
                        linkedin_result = await self.linkedin.post_to_linkedin_with_url(article_result, article_url)
                        linkedin_result["enhanced_post_used"] = False
                        linkedin_result["audio_mentioned"] = False
                    
                    result["linkedin_result"] = linkedin_result
                    
                    if linkedin_result["success"]:
                        result["workflow_success"] = True
                        print("✅ Complete enhanced workflow with audio successful!")
        else:
            print("   ⚠️ WordPress not configured or disabled")
        
        return result

    # Legacy method for backward compatibility
    async def generate_enhanced_quality_article_legacy(self, topic: str, audience: str = None, article_type: str = "how-to",
                                                      enable_deep_research: bool = True, research_model: str = "sonar",
                                                      max_articles_to_analyze: int = 6, publish_to_wordpress: bool = True, 
                                                      wordpress_status: str = "publish", post_to_linkedin: bool = True, 
                                                      max_revision_cycles: int = 2) -> Dict:
        """Legacy method that maps to new enhanced research without audio"""
        return await self.generate_enhanced_quality_article(
            topic=topic,
            audience=audience,
            article_type=article_type,
            enable_enhanced_research=enable_deep_research,
            research_model=research_model,
            max_urls_to_browse=max_articles_to_analyze,
            publish_to_wordpress=publish_to_wordpress,
            wordpress_status=wordpress_status,
            post_to_linkedin=post_to_linkedin,
            max_revision_cycles=max_revision_cycles,
            generate_audio=False  # Legacy calls don't generate audio by default
        )


# Enhanced main function with audio options
async def main():
    """Main function with audio generation options"""
    
    print("🎭 Enhanced AI Article Factory with Audio Integration")
    print("   🌐 Enhanced: URLs → Content Analysis → Synthesis → Article → Quality → Audio → Publish")
    print("   📚 Standard: Research → Content → Title → Quality → Audio → Publish")
    
    system = EnhancedQualityControlledArticleSystemWithAudio()
    
    # Check capabilities
    print(f"\nSystem Capabilities:")
    print(f"   🌐 Enhanced Research (URL Browsing): {'✅ Available' if system.enhanced_research_available else '❌ Unavailable'}")
    print(f"   📚 Standard Research: {'✅ Available' if system.perplexity_available else '❌ Unavailable'}")
    print(f"   🎤 Audio Generation: {'✅ Available' if system.audio_available else '❌ Unavailable'}")
    print(f"   🌐 WordPress: {'✅ Available' if system.wordpress_available else '❌ Unavailable'}")
    print(f"   📱 LinkedIn: {'✅ Available' if system.linkedin_available else '❌ Unavailable'}")
    
    # Configuration
    topic = input("\n🎯 Enter article topic: ").strip()
    if not topic:
        print("❌ Topic required!")
        return
    
    # Research options
    if system.enhanced_research_available:
        print("\n🌐 Research Options:")
        use_enhanced = input("Use enhanced research with URL browsing? (Y/n): ").strip().lower()
        enable_enhanced_research = use_enhanced != 'n'
        
        if enable_enhanced_research:
            max_urls = input("Max URLs to browse (1-10, default=6): ").strip()
            max_urls = int(max_urls) if max_urls.isdigit() and 1 <= int(max_urls) <= 10 else 6
            print(f"   Will browse up to {max_urls} URLs for enhanced content")
        else:
            max_urls = 0
    else:
        enable_enhanced_research = False
        max_urls = 0
        if not system.perplexity_available:
            print("\n⚠️ No research APIs available - generating without research")
    
    # Audio options
    if system.audio_available:
        print("\n🎤 Audio Options:")
        generate_audio = input("Generate audio version? (Y/n): ").strip().lower() != 'n'
        if generate_audio:
            audio_summary = input("Generate audio summary? (Y/n): ").strip().lower() != 'n'
        else:
            audio_summary = False
    else:
        generate_audio = False
        audio_summary = False
        print("\n⚠️ Audio generation not available (missing ElevenLabs API key)")
    
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
    publish_wp = input("Publish to WordPress with audio? (Y/n): ").strip().lower() != 'n'
    post_linkedin = input("Share on LinkedIn with audio mention? (Y/n): ").strip().lower() != 'n' if publish_wp else False
    
    # Execute enhanced generation with audio
    print(f"\n🚀 Starting enhanced generation with audio...")
    if enable_enhanced_research:
        print(f"   Will analyze up to {max_urls} URLs for comprehensive insights")
    if generate_audio:
        print(f"   Will generate audio version and {'summary' if audio_summary else 'no summary'}")
    
    result = await system.generate_enhanced_quality_article(
        topic=topic,
        audience=audience,
        article_type=article_type,
        enable_enhanced_research=enable_enhanced_research,
        research_model=research_model,
        max_urls_to_browse=max_urls,
        publish_to_wordpress=publish_wp,
        post_to_linkedin=post_linkedin,
        max_revision_cycles=max_revisions,
        generate_audio=generate_audio,
        audio_summary=audio_summary
    )
    
    # Show results
    if result.get("article_data"):
        print(f"\n📊 ENHANCED GENERATION WITH AUDIO REPORT")
        print("=" * 55)
        
        article_data = result["article_data"]
        quality_control = article_data.get("quality_control", {})
        metrics = article_data.get("metrics", {})
        audio_results = result.get("audio_results", {})
        
        print(f"🎯 Title: {article_data.get('article_title', 'Unknown')}")
        print(f"📄 Content: {metrics.get('word_count', 0)} words")
        print(f"📖 Reading Level: {metrics.get('reading_level', 'Unknown')}")
        print(f"🌐 Enhanced Research: {'Yes' if metrics.get('enhanced_research_used') else 'No'}")
        print(f"🔗 URLs Browsed: {metrics.get('urls_browsed', 0)}")
        print(f"📄 Revision Cycles: {quality_control.get('revision_cycles', 0)}")
        print(f"📈 Quality Score: {metrics.get('quality_score', 0)}/10")
        
        # Audio results
        if audio_results:
            print(f"\n🎤 Audio Generation:")
            full_audio = audio_results.get("full_audio", {})
            summary_audio = audio_results.get("summary_audio", {})
            
            if full_audio.get("success"):
                print(f"   🎵 Full Audio: {len(full_audio['audio_files'])} files")
                print(f"   ⏱️ Duration: ~{full_audio['estimated_duration_minutes']} minutes")
            
            if summary_audio.get("success"):
                print(f"   📄 Summary Audio: ~{summary_audio['estimated_duration_minutes']} minutes")
        
        # WordPress results
        if result.get("wordpress_result", {}).get("success"):
            wp_result = result["wordpress_result"]
            print(f"\n🌐 WordPress:")
            print(f"   📗 Published: {wp_result['post_url']}")
            if wp_result.get('has_audio'):
                print(f"   🎧 Audio Player: Embedded ({wp_result.get('audio_files_uploaded', 0)} files)")
        
        # LinkedIn results
        if result.get("linkedin_result", {}).get("success"):
            li_result = result["linkedin_result"]
            print(f"\n📱 LinkedIn:")
            print(f"   📤 Shared successfully")
            if li_result.get("audio_mentioned"):
                print(f"   🎵 Audio mentioned in post")
            if li_result.get('enhanced_post_used'):
                print(f"   ✨ Used enhanced LinkedIn post")
            if li_result.get('enhanced_research_used'):
                print(f"   🌐 Included research enhancement context")
        
        print(f"\n✅ Overall Success: {'Yes' if result.get('workflow_success') else 'No'}")

    else:
        print("\n❌ Article generation failed!")
        if result.get("error"):
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())