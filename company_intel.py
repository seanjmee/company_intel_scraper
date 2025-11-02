import os
import json
from typing import Dict
from dotenv import load_dotenv
import gradio as gr
import markdown
from scraper import fetch_website_links, fetch_website_contents
from openai import OpenAI

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
    """
    user_prompt += fetch_website_links(url)
    return user_prompt


def get_links(url: str) -> Dict:
    """Get relevant links from a company website using AI"""
    try:
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": LINK_SYSTEM_PROMPT},
                {"role": "user", "content": get_links_user_prompt(url)}
            ],
            response_format={"type": "json_object"}
        )
        result = response.choices[0].message.content
        return json.loads(result)
    except Exception as e:
        print(f"Error getting links: {e}")
        return {"links": []}


def get_company_intel_user_prompt(company_name: str, url: str) -> str:
    """Build prompt for company intelligence gathering"""
    user_prompt = f"""
    You are looking at a company called: {company_name}
    Here are the contents of its landing page and other relevant pages;
    use this information to build a short report about the company to help an OutSystems sell low-code software to the company.
    """
    user_prompt += fetch_website_contents(url)
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
        return response.choices[0].message.content
    except Exception as e:
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
        # Generate the markdown report
        markdown_report = get_company_intel(company_name, url)
        
        # Convert markdown to HTML
        html_report = markdown.markdown(markdown_report, extensions=['tables', 'fenced_code'])
        
        # Wrap in styled container
        styled_html = f"""
        <div style='font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;'>
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; color: white;'>
                <h1 style='margin: 0; font-size: 28px;'>📊 Company Intelligence Report</h1>
                <p style='margin: 10px 0 0 0; opacity: 0.9; font-size: 18px;'>{company_name}</p>
                <p style='margin: 5px 0 0 0; font-size: 14px; opacity: 0.8;'><a href='{url}' target='_blank' style='color: white;'>{url}</a></p>
            </div>
            <div style='padding: 30px; background-color: white; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); line-height: 1.6;'>
                {html_report}
            </div>
            <div style='margin-top: 20px; padding: 15px; background-color: #f5f5f5; border-radius: 5px; font-size: 12px; color: #666;'>
                <strong>Note:</strong> This report was generated using AI analysis of publicly available website content.
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
                - Analysis typically takes 10-30 seconds
                
                ### 🎯 What's Included:
                - Company overview and mission
                - Business objectives and priorities
                - Technology initiatives
                - Potential pain points
                - Sales opportunities
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