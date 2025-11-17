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

prompt = (
    "分成5步生成收支餘絀表："
    "1. 利用OCR在pdf當中找到收支餘絀表的頁面，擷取該頁面。"
    "2. 將該頁面蓋到文字的紅色印章去除。"
    "3. 利用當年度欄位資料生成.csv收支餘絀決算表。"
	"4. 將其轉換成易轉成sankey圖的形式，如下：
	來源,目標,金額,金額（萬元）,金額（萬元）（手動調整）,step from,step to
捐款收入,收入,96977205,9697.7,9697.7,1,2
補助收入,收入,6219273,621.9,621.9,1,2
利息收入,收入,583015,58.3,58.3,1,2
其他收入,收入,39200,3.9,3.9,1,2
會員年費收入,收入,31000,3.1,3.1,1,2
入會費收入,收入,1000,0.1,0.1,1,2
兌換盈益,收入,1,0.0,0.0,1,2
本期短絀,收入,8257077,825.7,825.7,1,2
收入,業務費,76100720,7610.1,7610.1,2,3
收入,人事費,21570128,2157.0,2157.0,2,3
收入,推廣費,9336242,933.6,933.6,2,3
收入,辦公費,2666214,266.6,266.6,2,3
收入,其他費用,2434467,243.4,243.4,2,3
業務費,絕育-認捐專案,65159545,6516.0,6516.0,3,4
業務費,絕育補助專案,5640900,564.1,564.1,3,4
業務費,絕育-下鄉專案費,3327459,332.7,332.7,3,4
業務費,絕育-中苗絕育計畫,903634,90.4,90.4,3,4
業務費,急難救助費,525789,52.6,52.6,3,4
業務費,絕育-駐紮計畫,200324,20.0,20.0,3,4
業務費,愛心人士支援計畫,136362,13.6,13.6,3,4
業務費,教育宣導,105061,10.5,10.5,3,4
業務費,境內送養費,101646,10.2,10.2,3,4
"
	"最後用'The csv is:'接上.csv內容以純文字印出"
)

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

