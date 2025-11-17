from google import genai
from google.genai import types
import pathlib

import dotenv

dotenv.load_dotenv()

api_key = dotenv.get_key('.env', 'GEMINI_API_KEY')
if api_key is None:
    raise RuntimeError("GEMINI_API_KEY not found in .env file. Please set it before running this script.")
client = genai.Client(api_key=api_key)

# Retrieve and encode the PDF byte
filepath = pathlib.Path('report.pdf')

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
