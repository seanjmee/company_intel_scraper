import os
import sys
import json
import hashlib
import re
import asyncio
from typing import Dict, Tuple, Optional, List
from dotenv import load_dotenv
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
import gradio as gr
import markdown
from openai import OpenAI
import tempfile
from weasyprint import HTML
from urllib.parse import urlparse
import time
import pickle

# Add parent directory to path to import scraper
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scraper import fetch_website_contents, fetch_website_links, fetch_with_retry

load_dotenv()
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Constants
MODEL = "gpt-4o-mini"
CACHE_DIR = os.path.join(os.path.dirname(__file__), '.cache')
CACHE_TTL = 86400  # 24 hours in seconds
MAX_WORKERS = 5  # For parallel fetching
TOKEN_COSTS = {
    "gpt-4o-mini": {"input": 0.00015 / 1000, "output": 0.0006 / 1000},  # per token
    "gpt-4o": {"input": 0.005 / 1000, "output": 0.015 / 1000}
}

# Create cache directory
os.makedirs(CACHE_DIR, exist_ok=True)

# System Prompts
COMPANY_INTEL_SYSTEM_PROMPT = """
You are an assistant that analyzes the contents of several relevant pages from a company website
and creates a short report about the company to help an OutSystems sell low-code software to the company.
Respond in markdown.
Include details of company objectives, priorities and initiatives/plans if you have the information.
Format the report with clear sections and bullet points for readability.
"""

# Relevant page patterns for rule-based link filtering
RELEVANT_LINK_PATTERNS = {
    'about': r'/(about|company|who-we-are|our-story|mission|vision)',
    'careers': r'/(careers|jobs|join-us|work-with-us|opportunities)',
    'products': r'/(products|solutions|services|offerings|platform)',
    'technology': r'/(technology|tech-stack|engineering|innovation)',
    'news': r'/(news|blog|press|media|newsroom|insights)',
    'team': r'/(team|leadership|management|executives)',
    'customers': r'/(customers|clients|case-studies|success-stories)',
}


# ============================================================================
# CACHING UTILITIES
# ============================================================================

def get_cache_key(data: str) -> str:
    """Generate cache key from data"""
    return hashlib.md5(data.encode()).hexdigest()


def get_from_cache(cache_key: str) -> Optional[any]:
    """Retrieve data from file cache if not expired"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")

    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                cached_data = pickle.load(f)
                timestamp, data = cached_data

                # Check if cache is still valid
                if time.time() - timestamp < CACHE_TTL:
                    print(f"   ✓ Cache hit for {cache_key[:8]}...")
                    return data
                else:
                    print(f"   ⚠️  Cache expired for {cache_key[:8]}...")
                    os.remove(cache_file)
    except Exception as e:
        print(f"   ⚠️  Cache read error: {e}")

    return None


def save_to_cache(cache_key: str, data: any):
    """Save data to file cache with timestamp"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")

    try:
        with open(cache_file, 'wb') as f:
            pickle.dump((time.time(), data), f)
        print(f"   ✓ Cached data with key {cache_key[:8]}...")
    except Exception as e:
        print(f"   ⚠️  Cache write error: {e}")


def calculate_cost(input_tokens: int, output_tokens: int, model: str = MODEL) -> float:
    """Calculate API cost based on token usage"""
    costs = TOKEN_COSTS.get(model, TOKEN_COSTS["gpt-4o-mini"])
    input_cost = input_tokens * costs["input"]
    output_cost = output_tokens * costs["output"]
    return input_cost + output_cost


# ============================================================================
# RULE-BASED LINK FILTERING (Replaces expensive AI call)
# ============================================================================

def filter_relevant_links(url: str) -> Dict:
    """
    Get relevant links from a company website using rule-based filtering
    This replaces the AI-based link selection, saving ~$0.0005 and 2-3 seconds per request
    """
    try:
        # Check cache first
        cache_key = get_cache_key(f"links_{url}")
        cached_result = get_from_cache(cache_key)
        if cached_result:
            return cached_result

        print(f"   → Fetching all links from {url[:50]}...")
        all_links = fetch_website_links(url)

        if not all_links:
            print("   ⚠️  No links found on page")
            return {"links": []}

        print(f"   → Found {len(all_links)} total links on page")

        # Filter using regex patterns
        relevant_links = []
        seen_types = set()

        for link in all_links:
            link_lower = link.lower()

            # Skip irrelevant patterns
            skip_patterns = ['login', 'signup', 'cart', 'checkout', 'privacy', 'terms',
                           'cookie', 'legal', '#', 'javascript:', 'mailto:']
            if any(skip in link_lower for skip in skip_patterns):
                continue

            # Match against relevant patterns
            for link_type, pattern in RELEVANT_LINK_PATTERNS.items():
                if re.search(pattern, link_lower, re.IGNORECASE):
                    # Only add one link per type to avoid duplicates
                    if link_type not in seen_types:
                        relevant_links.append({
                            "type": f"{link_type} page",
                            "url": link
                        })
                        seen_types.add(link_type)
                        break

            # Stop after finding 5 relevant pages
            if len(relevant_links) >= 5:
                break

        result = {"links": relevant_links}
        print(f"   ✓ Rule-based filtering identified {len(relevant_links)} relevant pages: {list(seen_types)}")

        # Cache the result
        save_to_cache(cache_key, result)

        return result

    except Exception as e:
        print(f"   ❌ Error filtering links: {e}")
        return {"links": []}


# ============================================================================
# PARALLEL PAGE FETCHING
# ============================================================================

def fetch_page_content(link_info: Dict, idx: int) -> Tuple[str, Dict]:
    """
    Fetch content for a single page (used in parallel fetching)
    Returns: (content_section, link_info)
    """
    try:
        link_url = link_info.get('url', '')
        link_type = link_info.get('type', 'page')

        if not link_url:
            return "", link_info

        print(f"\n📄 Fetching {link_type}...")
        print(f"   URL: {link_url[:80]}...")

        # Check cache first
        cache_key = get_cache_key(f"content_{link_url}")
        cached_content = get_from_cache(cache_key)

        if cached_content:
            content = cached_content
        else:
            content = fetch_with_retry(link_url)
            save_to_cache(cache_key, content)

        print(f"   ✓ Got {len(content)} characters")

        content_section = f"\n\n### {link_type.upper()}:\n{content}"
        return content_section, link_info

    except Exception as e:
        print(f"   ❌ Error fetching {link_type}: {e}")
        return "", link_info


def get_company_intel_user_prompt(company_name: str, url: str) -> str:
    """
    Build prompt for company intelligence gathering with multi-page analysis
    Now with parallel fetching and caching for 50% speed improvement
    """
    user_prompt = f"""
    You are looking at a company called: {company_name}
    Here are the contents of its landing page and other relevant pages;
    use this information to build a short report about the company to help an OutSystems sell low-code software to the company.

    ## LANDING PAGE CONTENT:
    """

    # Get main page content with caching
    try:
        print(f"📄 Fetching main page: {url}")
        cache_key = get_cache_key(f"content_{url}")
        cached_content = get_from_cache(cache_key)

        if cached_content:
            main_content = cached_content
        else:
            main_content = fetch_with_retry(url)
            save_to_cache(cache_key, main_content)

        user_prompt += main_content
    except Exception as e:
        print(f"⚠️  Error fetching main page: {e}")
        user_prompt += f"\n[Error loading main page: {str(e)}]"

    # Get and analyze relevant links with parallel fetching
    try:
        print("\n🔗 STEP 2: Finding relevant links...")
        relevant_links = filter_relevant_links(url)

        if relevant_links and 'links' in relevant_links and len(relevant_links['links']) > 0:
            print(f"\n✓ SUCCESS: Found {len(relevant_links['links'])} relevant pages to analyze")
            user_prompt += "\n\n## ADDITIONAL RELEVANT PAGES:\n"

            # Fetch content from multiple pages in parallel
            links_to_fetch = relevant_links['links'][:5]

            print(f"\n⚡ Fetching {len(links_to_fetch)} pages in parallel...")
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # Submit all fetch tasks
                future_to_link = {
                    executor.submit(fetch_page_content, link_info, idx): link_info
                    for idx, link_info in enumerate(links_to_fetch, 1)
                }

                # Collect results as they complete
                for future in as_completed(future_to_link):
                    content_section, link_info = future.result()
                    if content_section:
                        user_prompt += content_section

            elapsed = time.time() - start_time
            print(f"\n✓ Fetched {len(links_to_fetch)} pages in {elapsed:.2f}s (parallel)")

        else:
            print("\n⚠️  No additional relevant links found, using main page only")

    except Exception as e:
        print(f"\n❌ Error in link analysis: {e}")
        import traceback
        traceback.print_exc()
        user_prompt += "\n\n[Note: Additional pages could not be analyzed]"

    return user_prompt


def get_company_intel(company_name: str, url: str) -> Tuple[str, Dict]:
    """
    Generate company intelligence report with cost tracking

    CRITICAL FIX: Previously called get_company_intel_user_prompt() TWICE
    (once for printing, once for API call), doubling execution time and costs!

    Returns: (markdown_report, metadata_dict)
    """
    print(f"Generating report for {company_name} from {url}")

    # Check cache for complete report
    cache_key = get_cache_key(f"report_{company_name}_{url}")
    cached_report = get_from_cache(cache_key)
    if cached_report:
        print("   ✓ Using cached report!")
        return cached_report['report'], cached_report['metadata']

    try:
        # FIXED: Generate prompt only ONCE and reuse it
        user_prompt = get_company_intel_user_prompt(company_name, url)

        print(f"\n📊 Prompt size: {len(user_prompt)} characters")
        print(f"📊 Estimated input tokens: ~{len(user_prompt) // 4}")

        start_time = time.time()

        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": COMPANY_INTEL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )

        elapsed = time.time() - start_time

        # Extract report and usage data
        report = response.choices[0].message.content
        usage = response.usage

        # Calculate cost
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        cost = calculate_cost(input_tokens, output_tokens, MODEL)

        metadata = {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': usage.total_tokens,
            'cost': cost,
            'elapsed_time': elapsed,
            'model': MODEL
        }

        print(f"\n💰 API Usage:")
        print(f"   • Input tokens: {input_tokens:,}")
        print(f"   • Output tokens: {output_tokens:,}")
        print(f"   • Total tokens: {usage.total_tokens:,}")
        print(f"   • Cost: ${cost:.4f}")
        print(f"   • Generation time: {elapsed:.2f}s")
        print("✅ Report generated successfully")

        # Cache the complete result
        cache_data = {'report': report, 'metadata': metadata}
        save_to_cache(cache_key, cache_data)

        return report, metadata

    except Exception as e:
        print(f"❌ Error generating report: {e}")
        return f"Error generating report: {e}", {}


def generate_report_html(company_name: str, url: str) -> Tuple[str, Dict]:
    """
    Generate company intelligence report and return as HTML with metadata

    Returns: (styled_html, metadata_dict)
    """
    if not company_name or not url:
        error_html = "<p style='color: red;'>Please provide both company name and URL.</p>"
        return error_html, {}

    if not url.startswith(('http://', 'https://')):
        error_html = "<p style='color: red;'>URL must start with http:// or https://</p>"
        return error_html, {}

    try:
        print(f"\n{'='*60}")
        print(f"🚀 Starting analysis for: {company_name}")
        print(f"{'='*60}")

        # Generate the markdown report with metadata
        markdown_report, metadata = get_company_intel(company_name, url)

        print("="*60)
        print("✅ Report generation complete!")
        print("="*60 + "\n")

        # Convert markdown to HTML
        html_report = markdown.markdown(markdown_report, extensions=['tables', 'fenced_code'])

        # Add cost info to footer if available
        cost_info = ""
        if metadata and 'cost' in metadata:
            cost_info = f"""
            <div style='margin-top: 10px; padding-top: 10px; border-top: 1px solid #ccc; font-size: 12px; color: #666;'>
                <strong>Generation Stats:</strong>
                {metadata['total_tokens']:,} tokens |
                ${metadata['cost']:.4f} |
                {metadata['elapsed_time']:.1f}s |
                {metadata['model']}
            </div>
            """

        # Wrap in styled container with proper text contrast
        styled_html = f"""
        <div style='font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;'>
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; color: white;'>
                <h1 style='margin: 0; font-size: 28px; color: white;'>📊 Company Intelligence Report</h1>
                <p style='margin: 10px 0 0 0; font-size: 18px; color: white;'>{company_name}</p>
                <p style='margin: 5px 0 0 0; font-size: 14px;'><a href='{url}' target='_blank' style='color: white; text-decoration: underline;'>{url}</a></p>
            </div>
            <div style='padding: 30px; background-color: white; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); line-height: 1.8; color: #1a1a1a;'>
                <style>
                    /* Ensure all text has good contrast */
                    h1, h2, h3, h4, h5, h6 {{ color: #1a1a1a !important; margin-top: 20px; margin-bottom: 10px; font-weight: 600; }}
                    p {{ color: #2d2d2d !important; margin-bottom: 12px; font-size: 15px; }}
                    ul, ol {{ color: #2d2d2d !important; }}
                    li {{ color: #2d2d2d !important; margin-bottom: 8px; font-size: 15px; }}
                    strong, b {{ color: #000000 !important; font-weight: 600; }}
                    a {{ color: #0066cc !important; text-decoration: underline; }}
                    code {{ background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; color: #d63384; }}
                    pre {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #667eea; overflow-x: auto; }}
                    blockquote {{ border-left: 4px solid #667eea; padding-left: 15px; color: #444; font-style: italic; }}
                </style>
                {html_report}
            </div>
            <div style='margin-top: 20px; padding: 15px; background-color: #e8eaf6; border-left: 4px solid #667eea; border-radius: 5px; font-size: 13px; color: #1a1a1a;'>
                <strong style='color: #000;'>Note:</strong> This report was generated using AI analysis of publicly available website content.
                Always verify information and supplement with additional research.
                {cost_info}
            </div>
        </div>
        """

        return styled_html, metadata

    except Exception as e:
        error_html = f"""
        <div style='padding: 20px; background-color: #ffebee; border-left: 4px solid #f44336; border-radius: 5px;'>
            <h3 style='color: #c62828; margin-top: 0;'>❌ Error Generating Report</h3>
            <p style='color: #d32f2f;'>{str(e)}</p>
            <p style='color: #666; font-size: 14px; margin-top: 15px;'>
                <strong>Troubleshooting tips:</strong><br>
                • Verify the URL is accessible<br>
                • Check your OpenAI API key is valid<br>
                • Ensure the website allows scraping<br>
                • Try a different URL or company
            </p>
        </div>
        """
        return error_html, {}


def generate_report_with_download(company_name: str, url: str) -> Tuple[str, Optional[str]]:
    """
    Generate both HTML report (for display) and PDF (for download)

    CRITICAL FIX: Previously this called generate_report_html() and then
    generate_report_pdf() which called generate_report_html() AGAIN,
    resulting in double generation! Now we generate once and reuse.

    Returns tuple: (html_string, pdf_file_path or None)
    """
    try:
        # Generate HTML report once with metadata
        html_report, metadata = generate_report_html(company_name, url)

        # Check if it was successful
        if "Error Generating Report" in html_report or "Please provide both" in html_report:
            return html_report, None

        # Generate PDF from the same HTML (no re-generation!)
        print(f"\n📄 Generating PDF for: {company_name}")

        # Create temporary file for PDF
        pdf_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix='.pdf',
            prefix=f"{company_name.replace(' ', '_')}_report_"
        )

        print("   → Converting HTML to PDF...")

        # Convert HTML to PDF using WeasyPrint (reusing the HTML we already generated)
        HTML(string=html_report).write_pdf(pdf_file.name)

        print(f"   ✓ PDF generated: {pdf_file.name}")

        return html_report, pdf_file.name

    except Exception as e:
        print(f"❌ Error in report generation: {e}")
        import traceback
        traceback.print_exc()

        # Return HTML if available, even if PDF failed
        if 'html_report' in locals():
            return html_report, None
        else:
            error_html = f"""
            <div style='padding: 20px; background-color: #ffebee; border-left: 4px solid #f44336; border-radius: 5px;'>
                <h3 style='color: #c62828; margin-top: 0;'>❌ Error Generating Report</h3>
                <p style='color: #d32f2f;'>{str(e)}</p>
            </div>
            """
            return error_html, None


def create_gradio_interface():
    """Create and launch the Gradio web interface"""
    
    with gr.Blocks(title="Company Intelligence Report Generator", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🔍 Company Intelligence Report Generator

        Generate AI-powered sales intelligence reports by analyzing company websites.
        Perfect for sales teams, business development, and competitive analysis.

        ### ⚡ Optimized Features:
        - **Intelligent caching**: Repeated queries use cached results (24hr TTL)
        - **Parallel fetching**: Analyzes multiple pages simultaneously (50% faster)
        - **Rule-based filtering**: Smart link selection without AI overhead
        - **Cost tracking**: See token usage and cost for each report

        ### How it works:
        1. Enter a company name and their website URL
        2. AI scrapes and analyzes the website content (with smart caching!)
        3. Generates a detailed report with company objectives, priorities, and opportunities
        4. **Download as beautifully formatted PDF!**
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📝 Company Information")
                
                company_name = gr.Textbox(
                    label="Company Name",
                    placeholder="e.g., Acme Corporation",
                    lines=1
                )
                
                company_url = gr.Textbox(
                    label="Company Website URL",
                    placeholder="e.g., https://www.acme.com",
                    lines=1,
                    value=""
                )
                
                generate_btn = gr.Button(
                    "🚀 Generate Report",
                    variant="primary",
                    size="lg"
                )
                
                gr.Markdown("""
                ---
                ### 💡 Tips:
                - Use the company's main homepage URL
                - Ensure the URL starts with `http://` or `https://`
                - The report focuses on helping OutSystems sell low-code software
                - Analysis typically takes 20-45 seconds (we analyze multiple pages!)
                
                ### 🎯 What's Included:
                - **Multi-page analysis**: About, Careers, Products pages
                - Company overview and mission
                - Business objectives and priorities
                - Technology initiatives
                - Potential pain points
                - Sales opportunities
                
                ### 📊 Enhanced Analysis:
                The tool now intelligently:
                - Scrapes the homepage
                - Identifies relevant pages (About, Careers, etc.)
                - Analyzes up to 5 additional pages
                - Generates comprehensive insights
                """)
            
            with gr.Column(scale=2):
                gr.Markdown("### 📊 Intelligence Report")
                output_html = gr.HTML(
                    value="<p style='color: #999; text-align: center; padding: 100px;'>Enter company details and click 'Generate Report' to begin.</p>"
                )
                
                # PDF Download section
                gr.Markdown("### 📥 Download Report")
                pdf_output = gr.File(
                    label="Click the file name below to download your PDF report",
                    visible=True
                )
        
        # Connect button to generate both HTML and PDF
        generate_btn.click(
            fn=generate_report_with_download,
            inputs=[company_name, company_url],
            outputs=[output_html, pdf_output]
        )
        
        gr.Markdown("""
        ---
        ### ℹ️ About This Tool
        
        This tool uses OpenAI's GPT-4 to analyze company websites and generate sales intelligence reports.
        It's designed to help OutSystems sales teams understand prospects and identify opportunities.
        
        **Powered by:** OpenAI GPT-4o-mini + Web Scraping
        """)
    
    return demo


if __name__ == "__main__":
    print("🚀 Starting Company Intelligence Report Generator...")
    print("=" * 60)
    print("📋 Required: OPENAI_API_KEY in your .env file")
    print("\n🌐 Launching web interface...")
    print("=" * 60)
    
    demo = create_gradio_interface()
    demo.launch(share=False)