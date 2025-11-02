import os
import sys
import json
from typing import Dict
from dotenv import load_dotenv
import gradio as gr
import markdown
from openai import OpenAI

# Add parent directory to path to import scraper
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scraper import fetch_website_links, fetch_website_contents

load_dotenv()
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Constants
MODEL = "gpt-4o-mini"

# System Prompts
LINK_SYSTEM_PROMPT = """
You are provided with a list of links found on a webpage.
You are able to decide which of the links would be most relevant to include in a report about the company.
You should respond in JSON as in this example:
{
    "links": [
        {"type": "about page", "url": "https://full.url/goes/here/about"},
        {"type": "careers page", "url": "https://another.full.url/careers"}
    ]
}
"""

COMPANY_INTEL_SYSTEM_PROMPT = """
You are an assistant that analyzes the contents of several relevant pages from a company website
and creates a short report about the company to help an OutSystems sell low-code software to the company.
Respond in markdown.
Include details of company objectives, priorities and initiatives/plans if you have the information.
Format the report with clear sections and bullet points for readability.
"""


def get_links_user_prompt(url: str) -> str:
    """Build prompt for link selection"""
    user_prompt = f"""
    Here is the list of links on the website {url} -
    Please decide which of these are relevant web links for a report about the company,
    respond with the full https URL in JSON format.
    Do not include Terms of Service, Privacy, email links.
    Focus on: About, Careers, Products, Services, Team, News, Blog pages.
    """
    try:
        links = fetch_website_links(url)
        
        if not links:
            print("   ⚠️  fetch_website_links returned empty list")
            return user_prompt + "\n\nNo links found on page."
        
        print(f"   → Found {len(links)} total links on page")
        
        # Filter out obviously irrelevant links and make them absolute URLs
        from urllib.parse import urljoin
        filtered_links = []
        for link in links[:100]:  # Limit to first 100 to avoid token limits
            # Make relative URLs absolute
            absolute_url = urljoin(url, link)
            # Skip anchors, javascript, and common irrelevant patterns
            if (absolute_url.startswith(('http://', 'https://')) and 
                '#' not in absolute_url and
                'javascript:' not in absolute_url.lower() and
                not any(skip in absolute_url.lower() for skip in ['login', 'signup', 'cart', 'checkout'])):
                filtered_links.append(absolute_url)
        
        print(f"   → Filtered to {len(filtered_links)} relevant links")
        
        if not filtered_links:
            return user_prompt + "\n\nNo relevant links found."
        
        # Convert list to string representation
        user_prompt += "\n\nLinks found:\n" + "\n".join(filtered_links[:50])  # Limit to 50 to avoid token limits
    except Exception as e:
        print(f"   ❌ Error in get_links_user_prompt: {e}")
        user_prompt += f"\n\nError fetching links: {str(e)}"
    return user_prompt


def get_links(url: str) -> Dict:
    """Get relevant links from a company website using AI"""
    try:
        print(f"   → Fetching all links from {url[:50]}...")
        links_prompt = get_links_user_prompt(url)
        
        # Check if we got any links
        if "Error fetching links:" in links_prompt or "Links found:\n\n" in links_prompt:
            print("   ⚠️  No links were found on the page")
            return {"links": []}
        
        print(f"   → Sending {len(links_prompt)} chars to AI for link selection...")
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": LINK_SYSTEM_PROMPT},
                {"role": "user", "content": links_prompt}
            ],
            response_format={"type": "json_object"}
        )
        result = response.choices[0].message.content
        print(f"   → AI selected links: {result[:200]}...")
        
        parsed = json.loads(result)
        if parsed and 'links' in parsed:
            print(f"   ✓ AI identified {len(parsed['links'])} relevant pages")
        return parsed
    except Exception as e:
        print(f"   ❌ Error getting links: {e}")
        return {"links": []}


def get_company_intel_user_prompt(company_name: str, url: str) -> str:
    """Build prompt for company intelligence gathering with multi-page analysis"""
    user_prompt = f"""
    You are looking at a company called: {company_name}
    Here are the contents of its landing page and other relevant pages;
    use this information to build a short report about the company to help an OutSystems sell low-code software to the company.
    
    ## LANDING PAGE CONTENT:
    """
    
    # Get main page content
    try:
        print(f"📄 Fetching main page: {url}")
        user_prompt += fetch_website_contents(url)
    except Exception as e:
        print(f"⚠️  Error fetching main page: {e}")
        user_prompt += f"\n[Error loading main page: {str(e)}]"
    
    # Get and analyze relevant links
    try:
        print("\n🔗 STEP 2: Finding relevant links...")
        relevant_links = get_links(url)
        
        if relevant_links and 'links' in relevant_links and len(relevant_links['links']) > 0:
            print(f"\n✓ SUCCESS: Found {len(relevant_links['links'])} relevant pages to analyze")
            user_prompt += "\n\n## ADDITIONAL RELEVANT PAGES:\n"
            
            # Fetch content from each relevant link (limit to 5 to avoid token limits)
            for idx, link_info in enumerate(relevant_links['links'][:5], 1):
                try:
                    link_url = link_info.get('url', '')
                    link_type = link_info.get('type', 'page')
                    
                    if link_url:
                        print(f"\n📄 STEP 2.{idx}: Fetching {link_type}...")
                        print(f"   URL: {link_url[:80]}...")
                        content = fetch_website_contents(link_url)
                        print(f"   ✓ Got {len(content)} characters of content")
                        user_prompt += f"\n\n### {link_type.upper()}:\n"
                        user_prompt += content
                except Exception as e:
                    print(f"   ❌ Error fetching {link_type}: {e}")
                    continue
            
            print(f"\n✓ Successfully fetched content from {idx} additional pages")
        else:
            print("\n⚠️  No additional relevant links found, using main page only")
            print("   This might happen if:")
            print("   • The website has few links")
            print("   • Links are hidden in JavaScript")
            print("   • AI didn't identify any as relevant")
            
    except Exception as e:
        print(f"\n❌ Error in link analysis: {e}")
        import traceback
        traceback.print_exc()
        user_prompt += "\n\n[Note: Additional pages could not be analyzed]"
    
    return user_prompt


def get_company_intel(company_name: str, url: str) -> str:
    """Generate company intelligence report"""
    try:
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": COMPANY_INTEL_SYSTEM_PROMPT},
                {"role": "user", "content": get_company_intel_user_prompt(company_name, url)}
            ]
        )
        print("report generated")
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating report: {e}")
        return f"Error generating report: {e}"


def generate_report_html(company_name: str, url: str) -> str:
    """
    Generate company intelligence report and return as HTML
    This is the main function called by the Gradio interface
    """
    if not company_name or not url:
        return "<p style='color: red;'>Please provide both company name and URL.</p>"
    
    if not url.startswith(('http://', 'https://')):
        return "<p style='color: red;'>URL must start with http:// or https://</p>"
    
    try:
        print(f"\n{'='*60}")
        print(f"🚀 Starting analysis for: {company_name}")
        print(f"{'='*60}")
        
        # Generate the markdown report (now with multi-page analysis)
        markdown_report = get_company_intel(company_name, url)
        
        print("="*60)
        print("✅ Report generation complete!")
        print("="*60 + "\n")
        
        # Convert markdown to HTML
        html_report = markdown.markdown(markdown_report, extensions=['tables', 'fenced_code'])
        
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
            </div>
        </div>
        """
        
        return styled_html
        
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
        return error_html


def create_gradio_interface():
    """Create and launch the Gradio web interface"""
    
    with gr.Blocks(title="Company Intelligence Report Generator", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🔍 Company Intelligence Report Generator
        
        Generate AI-powered sales intelligence reports by analyzing company websites.
        Perfect for sales teams, business development, and competitive analysis.
        
        ### How it works:
        1. Enter a company name and their website URL
        2. AI scrapes and analyzes the website content
        3. Generates a detailed report with company objectives, priorities, and opportunities
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
        
        generate_btn.click(
            fn=generate_report_html,
            inputs=[company_name, company_url],
            outputs=output_html
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