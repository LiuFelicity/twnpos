from google import genai
from google.genai import types, errors
import argparse
import pathlib
import time

import dotenv

# ---------------------------
# CLI / env setup
# ---------------------------
parser = argparse.ArgumentParser()
parser.add_argument("file", type=pathlib.Path, help="Path to the PDF file to summarize")
args = parser.parse_args()

dotenv.load_dotenv()

api_key = dotenv.get_key(".env", "GEMINI_API_KEY")
if api_key is None:
    raise RuntimeError(
        "GEMINI_API_KEY not found in .env file. Please set it before running this script."
    )

client = genai.Client(api_key=api_key)

filepath = args.file

script_dir = pathlib.Path(__file__).resolve().parent
prompt_path = script_dir / "prompt.txt"
prompt = prompt_path.read_text(encoding="utf-8")
# ---------------------------
# Call Gemini with retry
# ---------------------------

def call_gemini_with_retry(
    pdf_path: pathlib.Path,
    prompt: str,
    model: str = "gemini-2.5-flash",
    max_retries: int = 5,
    base_delay: float = 1.0,  # seconds
):
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(
                        data=pdf_path.read_bytes(),
                        mime_type="application/pdf",
                    ),
                    prompt,
                ],
            )
            return response
        except errors.ServerError as e:
            msg = str(e)
            # Retry only when service is overloaded / unavailable
            if "503" in msg or "UNAVAILABLE" in msg or "overloaded" in msg:
                if attempt == max_retries:
                    print("Model is still overloaded after retries; giving up.")
                    raise
                delay = base_delay * (2 ** (attempt - 1))  # 1, 2, 4, 8, ...
                print(
                    f"[retry {attempt}/{max_retries}] "
                    f"Server overloaded (503). Sleeping {delay:.1f}s..."
                )
                time.sleep(delay)
            else:
                # Different server error – don't blindly loop forever
                raise

# ---------------------------
# Run
# ---------------------------

response = call_gemini_with_retry(filepath, prompt)
print(response.text)

