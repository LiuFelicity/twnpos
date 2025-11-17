from google import genai
from google.genai import types
import argparse
import pathlib

import dotenv

parser = argparse.ArgumentParser()
parser.add_argument('file', type=pathlib.Path, help='Path to the PDF file to summarize')
args = parser.parse_args()

dotenv.load_dotenv()

api_key = dotenv.get_key('.env', 'GEMINI_API_KEY')
if api_key is None:
    raise RuntimeError("GEMINI_API_KEY not found in .env file. Please set it before running this script.")
client = genai.Client(api_key=api_key)

# Retrieve and encode the PDF byte
filepath = args.file

prompt = "Summarize this document"
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        types.Part.from_bytes(
            data=filepath.read_bytes(),
            mime_type='application/pdf',
        ),
        prompt
    ]
)
print(response.text)
