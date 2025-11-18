# Financial report pdf to sankey diagram using Gemini API

This repository contains a Python script that extracts financial data from PDF reports and generates interactive Sankey diagrams using the Gemini API.

## Requirements
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

## Usage
Optionally download a sample PDF
```
bash get_pdf.sh
```

Generate the Sankey diagram by passing the PDF file path to the script:
```
bash pdf_to_sankey.sh report.pdf
```

The script launches a local web server to serve the generated Sankey diagram. Open your browser to localhost:8000 to view the generated Sankey diagram.

## About `pdf_to_sankey.sh`

The `pdf_to_sankey.sh` script is a convenience wrapper that runs the main Python script to extract financial data from a PDF file and generate an interactive Sankey diagram. It accepts a single argument: the path to the PDF file you want to process. The script ensures the required environment variables (such as your Gemini API key) are set, and then calls the Python script, which uses the Gemini API to analyze the PDF and produce the Sankey diagram output.