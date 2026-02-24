# AI Article Generator with Quality Control

An automated article generation system that researches topics, generates high-quality content with separate title and content variables, and publishes to WordPress with LinkedIn promotion.

## Key Features

- **Separate Title/Content Architecture**: Eliminates title duplication issues by generating content first, then creating titles based on actual content
- **Research Integration**: Uses Perplexity API for comprehensive web research
- **Multi-Agent Quality Control**: Automated quality checking, structure fixing, and readability improvement
- **WordPress Publishing**: Clean HTML conversion and publishing with proper title/content separation
- **LinkedIn Promotion**: Intelligent post generation with complete statistics extracted from content
- **Comprehensive Logging**: Detailed tracking of the entire workflow

## Architecture Overview

```
Topic → Research → Pure Content → Title from Content → Quality Control → WordPress → LinkedIn
```

### Separate Variables Approach
- `article_title`: Generated from content analysis
- `article_content`: Pure content without any title references
- No title duplication or cleaning needed

## Prerequisites

- Python 3.8+
- OpenAI API key
- Perplexity API key (optional, for research)
- WordPress.com account and app
- LinkedIn Developer account (optional, for social sharing)

## Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd ai-article-generator
   ```

2. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv add openai requests python-dotenv markdown

   # Or using pip
   pip install openai requests python-dotenv markdown
   ```

3. **Create environment file**
   ```bash
   cp .env.example .env
   ```

## Configuration

### Required API Keys

Create a `.env` file with the following variables:

```env
# OpenAI API (Required)
OPENAI_API_KEY=your_openai_api_key_here

# Perplexity API (Optional - for research)
PERPLEXITY_API_KEY=your_perplexity_api_key_here

# WordPress.com API (Optional - for publishing)
WORDPRESS_CLIENT_ID=your_wordpress_client_id
WORDPRESS_CLIENT_SECRET=your_wordpress_client_secret
WORDPRESS_SITE_ID=your_site_id
WORDPRESS_ACCESS_TOKEN=your_access_token

# LinkedIn API (Optional - for social sharing)
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token
LINKEDIN_PERSON_ID=your_linkedin_person_id
```

### API Setup Instructions

#### 1. OpenAI API
1. Visit [OpenAI API Platform](https://platform.openai.com/api-keys)
2. Create an API key
3. Add to `.env` file

#### 2. Perplexity API (Optional)
1. Visit [Perplexity AI Settings](https://www.perplexity.ai/settings/api)
2. Generate API key
3. Add to `.env` file

#### 3. WordPress.com (Optional)
1. Visit [WordPress.com Developer Apps](https://developer.wordpress.com/apps/)
2. Create a new application with these settings:
   - Redirect URL: `http://localhost:8080/callback`
   - Website URL: Your site URL
3. **Generate access token by running:**
   ```bash
   python wordpress_publisher.py
   ```
   Choose option `y` to setup credentials
4. Follow the browser authentication flow
5. Credentials will be automatically saved to `.env`

#### 4. LinkedIn API (Optional)
1. Visit [LinkedIn Developers](https://www.linkedin.com/developers/apps)
2. Create app with scopes: `r_liteprofile`, `w_member_social`
3. **Generate access token by running:**
   ```bash
   python personal_social_media_poster.py
   ```
   Choose option `1` to setup credentials
4. Credentials will be automatically saved to `.env`

## Usage

### Basic Article Generation

```bash
# Using uv (recommended)
uv run python complete_article_system.py

# Or direct Python
python complete_article_system.py
```

Follow the interactive prompts:
1. Enter your article topic
2. Configure quality control settings
3. The system will automatically:
   - Research the topic (if Perplexity configured)
   - Generate content without title
   - Create title based on content
   - Apply quality control
   - Publish to WordPress (if configured)
   - Share on LinkedIn (if configured)

### Component Testing

Test individual components:

```bash
# Test WordPress publishing
python wordpress_publisher.py

# Test LinkedIn posting
python personal_social_media_poster.py

# Test research functionality
python perplexity_web_researcher.py
```

## System Features

### Content Generation
- Researches topics using Perplexity Sonar models
- Generates 1500-2500 word articles
- Creates titles based on actual content analysis
- Maintains separate title and content variables

### Quality Control
- Multi-cycle quality checking
- Structural issue detection and fixing
- Readability improvement
- Completeness scoring
- Automated revision cycles

### Publishing Workflow
- WordPress: Clean HTML conversion with separate title/content
- LinkedIn: Intelligent post generation with extracted statistics
- Comprehensive error handling and fallback mechanisms
- Detailed logging for debugging

### Metrics Tracking
- Word count and reading time
- Flesch reading score and grade level
- Quality scores and revision cycles
- Character counts and content analysis

## File Structure

```
ai-article-generator/
├── complete_article_system.py     # Main orchestration system
├── perplexity_web_researcher.py   # Research functionality
├── wordpress_publisher.py         # WordPress publishing
├── personal_social_media_poster.py # LinkedIn integration
├── .env                           # Environment variables
├── .env.example                   # Environment template
├── README.md                      # This file
└── generated_articles/            # Output directory
    ├── *.md                       # Generated articles
    ├── *_wordpress_log.json       # Publishing logs
    └── *_linkedin_log.json        # Social media logs
```

## Configuration Options

### Quality Control Settings
- `max_revision_cycles`: Number of quality improvement cycles (1-3)
- `enable_web_research`: Use Perplexity for topic research
- `research_model`: Perplexity model ("sonar", "sonar-pro", "sonar-reasoning")

### Publishing Settings
- `publish_to_wordpress`: Enable WordPress publishing
- `wordpress_status`: Post status ("publish", "draft", "private")
- `post_to_linkedin`: Enable LinkedIn sharing

## Troubleshooting

### Common Issues

1. **Module not found errors**
   ```bash
   # Use uv run instead of direct python
   uv run python complete_article_system.py
   ```

2. **WordPress "invalid_token" error**
   ```bash
   # Regenerate access token
   python wordpress_publisher.py
   ```

3. **LinkedIn posting failures**
   ```bash
   # Test and regenerate credentials
   python personal_social_media_poster.py
   ```

4. **Research failures**
   - Check Perplexity API key
   - Verify API quota limits
   - Check network connectivity

### Debug Mode
Enable detailed logging by setting:
```env
DEBUG=true
```

## Output

The system generates:
- Markdown article files
- WordPress publishing logs
- LinkedIn posting logs
- Quality control reports
- Metrics and analytics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the generated log files
3. Test individual components
4. Open an issue with detailed error logs

## Architecture Benefits

The separate title/content approach provides:
- **Zero title duplication**: Impossible by design
- **Better SEO**: Titles reflect actual content
- **Cleaner code**: No complex cleaning logic
- **Smarter social posts**: Real content analysis
- **Professional results**: Consistent quality across platforms