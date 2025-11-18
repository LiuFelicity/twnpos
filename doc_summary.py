from google import genai
from google.genai import types, errors
import argparse
import pathlib
import time
import csv
import sys
import dotenv
import io

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
    model: str = "gemini-2.5-pro",
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
                    f"Server overloaded (503). Sleeping {delay:.1f}s...",
                    file=sys.stderr,
                )
                time.sleep(delay)
            else:
                # Different server error – don't blindly loop forever
                raise

# ---------------------------
# Helpers: extract and validate CSV code block
# ---------------------------

def extract_csv_code_block(text: str):
    lines = text.splitlines()
    if len(lines) < 3:
        return None, "Response too short to contain a CSV code block"
    if lines[0].strip() != "```csv":
        return None, "First line is not ```csv"
    if lines[-1].strip() != "```":
        return None, "Last line is not ```"
    return "\n".join(lines[1:-1]), None

def is_valid_csv(csv_str: str) -> bool:
    try:
        # Try to parse; ensure at least one row and consistent column counts
        f = io.StringIO(csv_str)
        reader = csv.reader(f)
        rows = list(reader)
        if not rows:
            return False
        width = len(rows[0])
        if width == 0:
            return False
        return all(len(r) == width for r in rows)
    except Exception as e:
        print(f"Unexpected error during CSV validation: {e}", file=sys.stderr)
        return False

# ---------------------------
# Run
# ---------------------------

response = call_gemini_with_retry(filepath, prompt)
csv_block, err = extract_csv_code_block(response.text)
if err:
    print(f"Invalid response format: {err}", file=sys.stderr)
    sys.exit(2)

if not is_valid_csv(csv_block):
    print("Invalid CSV content inside code block", file=sys.stderr)
    sys.exit(3)

# Only output the CSV lines in between, nothing else
if not csv_block.endswith("\n"):
    csv_block += "\n"
sys.stdout.write(csv_block)

