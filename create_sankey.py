import pandas as pd
from pyecharts.charts import Sankey
from pyecharts import options as opts
import os       # 導入 os 模組
import sys      # 導入 sys 模組
import argparse # 導入 argparse 模組

# --- 0. 設定參數解析 ---
parser = argparse.ArgumentParser(description="從 Excel 檔案生成 Sankey 圖表 HTML。")
parser.add_argument("input_file", help="來源 Excel 檔案的路徑 (例如: data/A0226_112.xlsx)")
args = parser.parse_args()

# --- 1. 設定固定參數 ---
SOURCE_COL_INDEX = 0  # 第 A 欄 '來源'
TARGET_COL_INDEX = 1  # 第 B 欄 '目標'
VALUE_COL_INDEX = 4   # 第 E 欄 '金額（萬元）（手動調整）'

# 使用參數傳入的檔案路徑
file_path = args.input_file

# --- 2. 讀取與準備資料 ---
try:
    df = pd.read_excel(file_path, header=0) 
except FileNotFoundError:
    sys.stderr.write(f"!!! 錯誤：找不到檔案。\n")
    sys.stderr.write(f"請確認路徑是否正確: {file_path}\n")
    sys.exit(1) # 錯誤退出
except Exception as e:
    sys.stderr.write(f"讀取檔案時出錯: {e}\n")
    sys.exit(1) # 錯誤退出

# --- 3. 透過索引取得欄位名稱 ---
try:
    source_col = df.columns[SOURCE_COL_INDEX]
    target_col = df.columns[TARGET_COL_INDEX]
    value_col = df.columns[VALUE_COL_INDEX]
except IndexError:
    sys.stderr.write(f"!!! 錯誤：欄位索引超出範圍。\n")
    sys.stderr.write(f"您的 Excel 檔案可能沒有 A, B, 或 E 欄。\n")
    sys.exit(1) # 錯誤退出

print(f"--- 成功讀取檔案: {file_path} ---")
print(f"來源 (Source) 欄: '{source_col}' (A欄)")
print(f"目標 (Target) 欄: '{target_col}' (B欄)")
print(f"數值 (Value)  欄: '{value_col}' (E欄)")
print("---------------------------------\n")

# --- 4. 準備 Pyecharts 所需的資料格式 ---
df = df.dropna(subset=[source_col, target_col, value_col])
df[value_col] = pd.to_numeric(df[value_col], errors='coerce')
df = df.dropna(subset=[value_col])
df = df[df[value_col] > 0]

df[source_col] = df[source_col].astype(str).str.strip()
df[target_col] = df[target_col].astype(str).str.strip()

all_labels = list(pd.concat([df[source_col], df[target_col]]).unique())
nodes_data = [{"name": label} for label in all_labels]

links_data = []
for idx, row in df.iterrows():
    links_data.append({
        "source": row[source_col],
        "target": row[target_col],
        "value": row[value_col]
    })

# --- 5. 建立 Sankey 圖表 (Pyecharts) ---
# (這部分的圖表邏輯與您提供的版本相同)
c = (
    Sankey()
    .add(
        series_name="財務流向",
        nodes=nodes_data,
        links=links_data,
        linestyle_opt=opts.LineStyleOpts(opacity=0.3, curve=0.5, color="source"),
        levels=[
            opts.SankeyLevelsOpts(depth=0, itemstyle_opts=opts.ItemStyleOpts(color="#5470C6")),
            opts.SankeyLevelsOpts(depth=1, itemstyle_opts=opts.ItemStyleOpts(color="#91CC75")),
            opts.SankeyLevelsOpts(depth=2, itemstyle_opts=opts.ItemStyleOpts(color="#FAC858")),
            opts.SankeyLevelsOpts(depth=3, itemstyle_opts=opts.ItemStyleOpts(color="#EE6666")),
            opts.SankeyLevelsOpts(depth=4, itemstyle_opts=opts.ItemStyleOpts(color="#FFC0CB")),
        ]
    )
    .set_series_opts(
        label_opts=opts.LabelOpts(
            is_show=True, position="right", formatter="{b}", font_size=10
        ),
        edge_label=opts.LabelOpts(
            is_show=True, position="middle", formatter="{c}", font_size=9, color="#000", font_weight="bold"
        )
    )
    .set_global_opts(
        title_opts=opts.TitleOpts(title="財務流向 Sankey 圖 (Pyecharts)"),
        tooltip_opts=opts.TooltipOpts(
            trigger="item",
            trigger_on="mousemove",
            formatter=lambda params: f"{params.data['source']} → {params.data['target']}<br/>金額: {params.data['value']}"
        )
    )
)

# --- 6. 輸出成 HTML 檔案 (存到 'result' 資料夾) ---

# 定義輸出資料夾
output_dir = "result"
# 確保 'result' 資料夾存在
os.makedirs(output_dir, exist_ok=True)

# 根據輸入檔名，自動產生輸出檔名
# (例如: 'data/A0226_112.xlsx' -> 'A0226_112_sankey.html')
base_name = os.path.basename(file_path)
file_name_without_ext = os.path.splitext(base_name)[0]
output_name = f"{file_name_without_ext}_sankey.html"

# 組合出完整的輸出路徑
output_file_path = os.path.join(output_dir, output_name)

# 渲染 HTML 檔案
c.render(output_file_path)

print(f"Pyecharts Sankey 圖表已成功生成！")
print(f"檔案已儲存為: {os.path.realpath(output_file_path)}")