# Gemini document understanding

This script summarizes the content of a PDF document using the Gemini API.

# Requirements
- python 3.14

[//]: # (python 3.10 also works but I don't like it)

Install dependencies:
```
pip3 install -r requirements.txt
```

Put your API key in a `.env` file in the same directory as the script:

```
GEMINI_API_KEY="your_api_key_here"
```

# Usage

Optionally download a sample PDF
```
bash get_pdf.sh
```

Summarize a PDF document by providing the file path as an argument:
```
python3 doc_summary.py report.pdf
```