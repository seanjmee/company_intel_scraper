# 🚀 Quick Start Guide

## The Import Error - FIXED! ✅

The error `ImportError: cannot import name 'fetch_website_links' from 'scraper'` has been resolved.

**The Problem:** 
- The `company_intel.py` file moved to `week1/company_intel/` subdirectory
- The `scraper.py` file is in the parent directory `week1/`
- Python couldn't find the scraper module

**The Solution:**
Added path manipulation to import from parent directory:

```python
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scraper import fetch_website_links, fetch_website_contents
```

## 🏃 Running the Application

### Option 1: From the company_intel directory

```bash
cd /Users/seanmee/AIProjects/llm_engineering/week1/company_intel
python company_intel.py
```

### Option 2: From the week1 directory

```bash
cd /Users/seanmee/AIProjects/llm_engineering/week1
python company_intel/company_intel.py
```

### Option 3: From anywhere with full path

```bash
python /Users/seanmee/AIProjects/llm_engineering/week1/company_intel/company_intel.py
```

## 📋 Prerequisites

### 1. Install Dependencies

Make sure you have all required packages:

```bash
cd /Users/seanmee/AIProjects/llm_engineering
pip install -r requirements.txt
```

Key packages needed:
- `gradio` - Web interface
- `openai` - AI API
- `beautifulsoup4` - Web scraping
- `requests` - HTTP requests
- `markdown` - Markdown to HTML conversion
- `python-dotenv` - Environment variables

### 2. Set Up Environment

Create or verify your `.env` file in the project root:

```bash
# Location: /Users/seanmee/AIProjects/llm_engineering/.env
OPENAI_API_KEY=sk-proj-your_key_here
```

## 🌐 Access the Web Interface

Once running, open your browser to:

**http://localhost:7860**

You should see:
- A form with Company Name and URL inputs
- A "Generate Report" button
- Instructions and tips on the left
- Empty report area on the right

## ✅ Testing It Works

### Quick Test:

1. **Company Name:** `OpenAI`
2. **Company URL:** `https://openai.com`
3. Click **Generate Report**
4. Wait 10-20 seconds
5. See a beautiful styled report!

### Expected Output:

- Purple gradient header with company name
- Markdown-formatted report with sections
- Company overview, objectives, tech stack
- Sales opportunities for OutSystems
- Disclaimer footer

## 🐛 Troubleshooting

### Import Error Still Occurring?

Check file structure:
```
week1/
├── scraper.py              ← Must be here
├── company_intel/
│   ├── company_intel.py    ← Running from here
│   └── QUICKSTART.md       ← You are here
```

### Module Not Found: gradio/markdown

```bash
pip install gradio markdown
```

### OpenAI API Error

Check your `.env` file:
```bash
cat /Users/seanmee/AIProjects/llm_engineering/.env
```

Should show:
```
OPENAI_API_KEY=sk-proj-...
```

### Website Scraping Fails

Some websites block scraping. Try these reliable ones:
- `https://openai.com`
- `https://www.microsoft.com`
- `https://www.github.com`

### Port Already in Use

If 7860 is busy:

```python
# Edit line 244 in company_intel.py:
demo.launch(share=False, server_port=7861)  # Use different port
```

## 📊 Usage Flow

```
1. Start Application
   └─> python company_intel.py
   
2. Open Browser
   └─> http://localhost:7860
   
3. Enter Details
   ├─> Company Name: "Acme Corp"
   └─> URL: "https://acme.com"
   
4. Generate Report
   └─> Click "Generate Report" button
   
5. AI Processing (10-30s)
   ├─> Scrapes website
   ├─> Sends to GPT-4o-mini
   └─> Generates markdown report
   
6. View Results
   └─> Beautiful HTML report appears
```

## 💡 Pro Tips

### Multiple Reports
- Leave the app running
- Generate multiple reports without restarting
- Each report is independent

### Save Reports
- Right-click on report → "Save As" → HTML
- Or copy the markdown from console if debugging

### Customize
- Edit `COMPANY_INTEL_SYSTEM_PROMPT` for different focus
- Change `MODEL` to "gpt-4o" for better quality
- Adjust HTML styling in `generate_report_html()`

### Performance
- First report may be slower (cold start)
- Subsequent reports are faster
- Large websites take longer to scrape

## 🔍 Verifying the Fix

To confirm the import issue is resolved, run this test:

```bash
cd /Users/seanmee/AIProjects/llm_engineering/week1/company_intel
python -c "import sys; import os; sys.path.insert(0, '..'); from scraper import fetch_website_links; print('✅ Import successful!')"
```

Should output:
```
✅ Import successful!
```

## 📁 File Dependencies

```
company_intel.py needs:
├── scraper.py (from parent directory)
│   ├── fetch_website_contents()
│   └── fetch_website_links()
├── .env (from project root)
│   └── OPENAI_API_KEY
└── requirements.txt packages
    ├── gradio
    ├── openai
    ├── markdown
    ├── beautifulsoup4
    └── requests
```

## 🎉 Success Indicators

When everything works, you'll see:

```
🚀 Starting Company Intelligence Report Generator...
============================================================
📋 Required: OPENAI_API_KEY in your .env file

🌐 Launching web interface...
============================================================
Running on local URL:  http://127.0.0.1:7860
```

Then in your browser:
- Clean web interface loads
- Form fields are interactive
- Generating report shows styled output
- No error messages

---

**Need Help?** Check the main README at `COMPANY_INTEL_README.md` for more details!

