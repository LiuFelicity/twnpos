from google import genai
from google.genai import types
import pathlib

import dotenv

dotenv.load_dotenv()

client = genai.Client(api_key = dotenv.get_key('.env', 'GEMINI_API_KEY'))

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
      prompt])
print(response.text)
