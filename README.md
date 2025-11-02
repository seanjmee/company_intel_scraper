# 🔍 Company Intelligence Report Generator

A web-based AI-powered tool that analyzes company websites and generates detailed sales intelligence reports.

## 🎯 Purpose

Help OutSystems sales teams:
- Understand potential customers quickly
- Identify company objectives and priorities
- Discover technology initiatives and pain points
- Find opportunities to position low-code solutions

## ✨ Features

- **Web-based Interface**: Easy-to-use form for company name and URL
- **AI-Powered Analysis**: Uses GPT-4o-mini to analyze website content
- **Beautiful Reports**: Professional HTML formatting with styled sections
- **Real-time Generation**: See reports generated in seconds
- **Error Handling**: Helpful troubleshooting for common issues

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Make sure you have these packages:
- `gradio` - Web interface
- `openai` - AI analysis
- `markdown` - Report formatting
- `python-dotenv` - Environment variables

### 2. Set Up API Key

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=sk-proj-your_key_here
```

### 3. Run the Application

```bash
python week1/company_intel.py
```

The app will launch at: **http://localhost:7860**

## 📊 How to Use

1. **Open the web interface** in your browser
2. **Enter company name** (e.g., "Acme Corporation")
3. **Enter website URL** (e.g., "https://www.acme.com")
4. **Click "Generate Report"**
5. **Wait 10-30 seconds** for AI analysis
6. **View the beautiful HTML report** with insights

## 📝 What's In The Report

- **Company Overview**: Mission, vision, and background
- **Business Objectives**: Strategic goals and priorities
- **Technology Stack**: Current technologies and infrastructure
- **Initiatives & Plans**: Upcoming projects and investments
- **Pain Points**: Potential challenges and needs
- **Sales Opportunities**: How OutSystems can help

## 🎨 Report Features

- **Gradient Header**: Purple gradient with company info
- **Styled Content**: Professional formatting with proper spacing
- **Markdown Support**: Headings, lists, tables, code blocks
- **Clickable Links**: Direct link to company website
- **Disclaimer**: Reminds to verify AI-generated content

## 🛠️ Technical Details

### Architecture

```
User Input (Form)
    ↓
Scraper Module (scraper.py)
    ↓
Website Content
    ↓
OpenAI GPT-4o-mini
    ↓
Markdown Report
    ↓
HTML Conversion
    ↓
Styled Display (Gradio)
```

### Key Functions

- `get_company_intel()` - Generates markdown report
- `generate_report_html()` - Converts to styled HTML
- `create_gradio_interface()` - Builds web UI
- `fetch_website_contents()` - Scrapes website (from scraper.py)

### Dependencies on scraper.py

This tool requires `scraper.py` with:
- `fetch_website_contents(url)` - Gets page text
- `fetch_website_links(url)` - Gets all links

## ⚙️ Configuration

### Model Selection

Change the AI model in `company_intel.py`:

```python
MODEL = "gpt-4o-mini"  # Fast and cost-effective
# MODEL = "gpt-4o"     # More powerful, slower
# MODEL = "gpt-4-turbo" # Alternative
```

### Custom Prompts

Modify the system prompt to change report focus:

```python
COMPANY_INTEL_SYSTEM_PROMPT = """
Your custom instructions here...
Focus on specific aspects...
"""
```

## 💡 Tips for Best Results

### Website Selection
- ✅ Use main company homepage
- ✅ Ensure site is publicly accessible
- ✅ Check site allows web scraping
- ❌ Avoid login-protected pages
- ❌ Avoid sites with heavy JavaScript

### Company Research
- Start with well-known companies for testing
- Use for companies with informative websites
- Supplement AI insights with manual research
- Verify all AI-generated information

### Report Customization
- Edit system prompts for different focus areas
- Adjust markdown extensions for formatting
- Customize HTML styling for branding

## 🔧 Troubleshooting

### "Error generating report"
**Causes:**
- Website blocks scraping
- URL is incorrect
- API key is missing/invalid
- Network issues

**Solutions:**
- Verify URL is accessible in browser
- Check `.env` file has valid OPENAI_API_KEY
- Try a different company website
- Check internet connection

### "No content found"
**Causes:**
- Website requires JavaScript
- Content is behind login
- Site uses anti-scraping measures

**Solutions:**
- Try the company's main domain
- Use sites with static content
- Check if site allows automated access

### Slow Generation
**Causes:**
- Large website with many pages
- GPT-4 processing time
- Network latency

**Solutions:**
- Normal for 10-30 seconds
- Consider caching results
- Use faster model (gpt-4o-mini)

## 📈 Improvements & Extensions

### Possible Enhancements

1. **Multiple Companies**: Batch analysis of competitor list
2. **PDF Export**: Download reports as PDF
3. **Report History**: Save and view past reports
4. **Custom Templates**: Different report formats
5. **Data Visualization**: Charts for tech stack analysis
6. **LinkedIn Integration**: Add executive profiles
7. **News Integration**: Recent company news
8. **Comparison Mode**: Side-by-side company analysis

### Code Extensions

```python
# Add caching
from functools import lru_cache

@lru_cache(maxsize=100)
def get_company_intel_cached(company_name, url):
    return get_company_intel(company_name, url)

# Add PDF export
from fpdf import FPDF

def export_to_pdf(markdown_report, filename):
    # Convert and save as PDF
    pass

# Add database storage
import sqlite3

def save_report(company_name, url, report):
    # Store in database
    pass
```

## 🔐 Security Considerations

- Never commit API keys to git
- Use environment variables for secrets
- Respect website robots.txt
- Add rate limiting for production
- Validate user input (URL format)
- Sanitize scraped content

## 💰 Cost Estimate

Per report with GPT-4o-mini:
- Average tokens: ~2,000 (input) + ~1,000 (output)
- Cost: ~$0.001 per report
- Very cost-effective for sales intelligence

For heavy usage:
- 100 reports/day: ~$0.10/day
- Consider caching repeated companies
- Use cheaper models for drafts

## 📚 Related Files

- `scraper.py` - Web scraping functions (required)
- `.env` - API keys (create this)
- `requirements.txt` - Python dependencies

## 🎓 Learning Outcomes

This project demonstrates:
- Web scraping techniques
- AI prompt engineering
- Gradio interface building
- Markdown to HTML conversion
- Error handling and validation
- Professional UI/UX design

## 📄 License

Part of the LLM Engineering course materials.

---

**Ready to analyze companies?** Run `python week1/company_intel.py` and start generating reports! 🚀
