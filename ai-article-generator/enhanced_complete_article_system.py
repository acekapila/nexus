# enhanced_complete_article_system.py - Complete updated system with URL browsing integration
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

# Import all existing classes (ArticleQualityAgent, EnhancedArticleGenerator remain the same)
# from complete_article_system import ArticleQualityAgent, EnhancedArticleGenerator

class DeepLearningArticleGenerator(EnhancedArticleGenerator):
    """Enhanced article generator that uses deep learning from full articles and URL browsing"""
    
    async def generate_article_with_enhanced_research(self, topic: str, research_data: Dict, 
                                                    audience: str = None, article_type: str = "how-to") -> Dict:
        """Generate article using enhanced research data that includes URL browsing"""
        
        print("📝 Generating article with enhanced research context...")
        
        # Check research type
        research_type = research_data.get("research_type", "standard")
        is_enhanced_research = research_type in ["enhanced_deep_research_with_browsing", "deep_research_with_browsing"]
        
        if is_enhanced_research:
            research_context = self._build_enhanced_research_context(research_data)
            urls_browsed = research_data.get("urls_analyzed", 0)
            words_extracted = research_data.get("total_words_browsed", 0)
            print(f"   🌐 Using enhanced research: {urls_browsed} URLs browsed, {words_extracted} words extracted")
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
        
        print("   ✅ Article content generated with enhanced insights")
        
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
    
    def _build_enhanced_research_context(self, research_data: Dict) -> str:
        """Build research context from enhanced URL browsing data"""
        
        context_parts = []
        
        # Comprehensive themes from synthesis
        themes = research_data.get("comprehensive_themes", [])
        if themes:
            context_parts.append(f"COMPREHENSIVE THEMES:\n" + "\n".join(f"- {theme}" for theme in themes))
        
        # Evidence-based findings
        findings = research_data.get("evidence_based_findings", [])
        if findings:
            context_parts.append(f"EVIDENCE-BASED FINDINGS:\n" + "\n".join(f"- {finding}" for finding in findings))
        
        # Novel insights from browsed content
        novel_insights = research_data.get("novel_insights", [])
        if novel_insights:
            context_parts.append(f"NOVEL INSIGHTS FROM BROWSED SOURCES:\n" + "\n".join(f"- {insight}" for insight in novel_insights))
        
        # Data-driven points with context
        data_points = research_data.get("data_driven_points", [])
        if data_points:
            context_parts.append(f"DATA-DRIVEN INSIGHTS:\n" + "\n".join(f"- {point}" for point in data_points))
        
        # Practical framework
        framework = research_data.get("practical_framework", [])
        if framework:
            context_parts.append(f"PRACTICAL FRAMEWORK:\n" + "\n".join(f"- {item}" for item in framework))
        
        # Expert perspectives from browsed content
        expert_perspectives = research_data.get("expert_perspectives", [])
        if expert_perspectives:
            context_parts.append(f"EXPERT PERSPECTIVES:\n" + "\n".join(f"- {perspective}" for perspective in expert_perspectives))
        
        # Implementation strategies
        strategies = research_data.get("implementation_strategies", [])
        if strategies:
            context_parts.append(f"IMPLEMENTATION STRATEGIES:\n" + "\n".join(f"- {strategy}" for strategy in strategies))
        
        # Content gaps to address
        gaps = research_data.get("content_gaps", [])
        if gaps:
            context_parts.append(f"CONTENT GAPS TO ADDRESS:\n" + "\n".join(f"- {gap}" for gap in gaps))
        
        # Insights from browsed content
        browsed_insights = research_data.get("browsed_insights", [])
        if browsed_insights:
            context_parts.append(f"INSIGHTS FROM BROWSED ARTICLES:\n" + "\n".join(f"- {insight}" for insight in browsed_insights[:8]))
        
        # Unique data points
        unique_data = research_data.get("unique_data_points", [])
        if unique_data:
            context_parts.append(f"UNIQUE DATA POINTS:\n" + "\n".join(f"- {data}" for data in unique_data))
        
        # Practical applications
        applications = research_data.get("practical_applications", [])
        if applications:
            context_parts.append(f"PRACTICAL APPLICATIONS:\n" + "\n".join(f"- {app}" for app in applications))
        
        return "\n\n".join(context_parts)
    
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
- Reference concepts from browsed sources without direct attribution

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


class EnhancedQualityControlledArticleSystem:
    """Enhanced system with URL browsing and deep learning research capabilities"""
    
    def __init__(self):
        # Use the enhanced researcher with URL browsing
        from enhanced_perplexity_web_researcher import EnhancedPerplexityWebResearcher
        from wordpress_publisher import WordPressPublisher
        from personal_social_media_poster import EnhancedLinkedInPoster
        
        self.researcher = EnhancedPerplexityWebResearcher()
        self.generator = DeepLearningArticleGenerator()
        self.wordpress = WordPressPublisher()
        self.linkedin = EnhancedLinkedInPoster()
        
        # Check system availability
        self.perplexity_available = bool(self.researcher.api_key)
        self.openai_available = bool(os.getenv('OPENAI_API_KEY'))
        self.wordpress_available = bool(self.wordpress.access_token)
        self.linkedin_available = 'linkedin_personal' in self.linkedin.enabled_platforms
        
        # Check enhanced research capability
        self.enhanced_research_available = self.perplexity_available and self.openai_available
    
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

    async def generate_enhanced_quality_article(self, topic: str, audience: str = None, article_type: str = "how-to",
                                              enable_enhanced_research: bool = True, research_model: str = "sonar",
                                              max_urls_to_browse: int = 6, publish_to_wordpress: bool = True, 
                                              wordpress_status: str = "publish", post_to_linkedin: bool = True, 
                                              max_revision_cycles: int = 2) -> Dict:
        """Generate high-quality article with enhanced URL browsing research"""
        
        print(f"\n🏭 Starting enhanced article generation for: {topic}")
        if enable_enhanced_research and self.enhanced_research_available:
            print("   🌐 Enhanced Research: URLs → Content Analysis → Synthesis → Article → Quality → Publish")
        else:
            print("   📚 Standard: Research → Content → Title → Quality → Publish")
        
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
        
        # Step 3: Quality Control Loop
        while revision_cycle < max_revision_cycles:
            revision_cycle += 1
            print(f"\n🔍 Phase 3.{revision_cycle}: Quality control check...")
            
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
        
        # Step 5: Publishing workflow
        result = {
            "article_data": article_result,
            "research_summary": research_data,
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
        
        # Publish to WordPress
        if publish_to_wordpress and self.wordpress_available:
            print("🌐 Phase 5: Publishing to WordPress...")
            print(f"   📋 Title: {final_title}")
            print(f"   📄 Content: {len(final_content)} chars")
            if article_result.get("enhanced_research_used"):
                print(f"   🌐 Enhanced with {article_result.get('urls_browsed', 0)} browsed URLs")
            
            wordpress_result = await self.wordpress.publish_article(article_result, status=wordpress_status)
            result["wordpress_result"] = wordpress_result
            
            if wordpress_result["success"]:
                article_url = wordpress_result["post_url"]
                print(f"   ✅ Published: {article_url}")
                
                # Share on LinkedIn
                if post_to_linkedin and self.linkedin_available:
                    print("📱 Phase 6: Sharing on LinkedIn...")
                    
                    enhanced_post = await self.generator.generate_enhanced_linkedin_post(article_result, article_url)
                    
                    if enhanced_post["success"]:
                        enhanced_article_data = article_result.copy()
                        enhanced_article_data["linkedin_post_override"] = enhanced_post["linkedin_content"]
                        
                        linkedin_result = await self.linkedin.post_to_linkedin_with_url(enhanced_article_data, article_url)
                        linkedin_result["enhanced_post_used"] = True
                        linkedin_result["enhanced_research_used"] = article_result.get("enhanced_research_used", False)
                    else:
                        linkedin_result = await self.linkedin.post_to_linkedin_with_url(article_result, article_url)
                        linkedin_result["enhanced_post_used"] = False
                    
                    result["linkedin_result"] = linkedin_result
                    
                    if linkedin_result["success"]:
                        result["workflow_success"] = True
                        print("✅ Complete enhanced workflow successful!")
        
        return result

    # Legacy method for backward compatibility
    async def generate_enhanced_quality_article_legacy(self, topic: str, audience: str = None, article_type: str = "how-to",
                                                      enable_deep_research: bool = True, research_model: str = "sonar",
                                                      max_articles_to_analyze: int = 6, publish_to_wordpress: bool = True, 
                                                      wordpress_status: str = "publish", post_to_linkedin: bool = True, 
                                                      max_revision_cycles: int = 2) -> Dict:
        """Legacy method that maps to new enhanced research"""
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
            max_revision_cycles=max_revision_cycles
        )


# Enhanced main function
async def main():
    """Main function with enhanced URL browsing research options"""
    
    print("🏭 Enhanced AI Article Factory with URL Browsing Research")
    print("   🌐 Enhanced: URLs → Content Analysis → Synthesis → Article → Publish")
    print("   📚 Standard: Research → Content → Title → Quality → Publish")
    
    system = EnhancedQualityControlledArticleSystem()
    
    # Check capabilities
    print(f"\nSystem Capabilities:")
    print(f"   🌐 Enhanced Research (URL Browsing): {'✅ Available' if system.enhanced_research_available else '❌ Unavailable'}")
    print(f"   📚 Standard Research: {'✅ Available' if system.perplexity_available else '❌ Unavailable'}")
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
    publish_wp = input("Publish to WordPress? (Y/n): ").strip().lower() != 'n'
    post_linkedin = input("Share on LinkedIn? (Y/n): ").strip().lower() != 'n' if publish_wp else False
    
    # Execute enhanced generation
    print(f"\n🚀 Starting enhanced generation...")
    if enable_enhanced_research:
        print(f"   Will analyze up to {max_urls} URLs for comprehensive insights")
    
    result = await system.generate_enhanced_quality_article(
        topic=topic,
        audience=audience,
        article_type=article_type,
        enable_enhanced_research=enable_enhanced_research,
        research_model=research_model,
        max_urls_to_browse=max_urls,
        publish_to_wordpress=publish_wp,
        post_to_linkedin=post_linkedin,
        max_revision_cycles=max_revisions
    )
    
    # Show results
    if result.get("article_data"):
        print(f"\n📊 ENHANCED GENERATION REPORT")
        print("=" * 50)
        
        article_data = result["article_data"]
        quality_control = article_data.get("quality_control", {})
        metrics = article_data.get("metrics", {})
        
        print(f"🎯 Title: {article_data.get('article_title', 'Unknown')}")
        print(f"📄 Content: {metrics.get('word_count', 0)} words")
        print(f"📖 Reading Level: {metrics.get('reading_level', 'Unknown')}")
        print(f"🌐 Enhanced Research: {'Yes' if metrics.get('enhanced_research_used') else 'No'}")
        print(f"🔗 URLs Browsed: {metrics.get('urls_browsed', 0)}")
        print(f"🔄 Revision Cycles: {quality_control.get('revision_cycles', 0)}")
        print(f"📈 Quality Score: {metrics.get('quality_score', 0)}/10")
        print(f"⚡ Enhancement Level: {metrics.get('research_enhancement_level', 'standard')}")
        
        if result.get("wordpress_result", {}).get("success"):
            print(f"\n🌐 Published: {result['wordpress_result']['post_url']}")
        
        if result.get("linkedin_result", {}).get("success"):
            enhanced_post = result['linkedin_result'].get('enhanced_post_used', False)
            research_enhanced = result['linkedin_result'].get('enhanced_research_used', False)
            print(f"📱 LinkedIn: Shared successfully")
            if enhanced_post:
                print(f"   ✨ Used enhanced LinkedIn post")
            if research_enhanced:
                print(f"   🌐 Included research enhancement context")
        
        # Research summary
        research_summary = result.get("research_summary", {})
        if research_summary.get("enhanced_research_used"):
            urls_analyzed = research_summary.get("urls_analyzed", 0)
            words_browsed = research_summary.get("total_words_browsed", 0)
            print(f"\n🔬 Research Summary:")
            print(f"   URLs Analyzed: {urls_analyzed}")
            print(f"   Words Extracted: {words_browsed:,}")
            print(f"   Enhancement Type: {research_summary.get('research_type', 'unknown')}")
            
            themes = research_summary.get("comprehensive_themes", [])
            if themes:
                print(f"   Key Themes: {len(themes)} identified")
                for i, theme in enumerate(themes[:3], 1):
                    print(f"     {i}. {theme}")

    # Error handling and fallback
    else:
        print("\n❌ Article generation failed!")
        if result.get("error"):
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())