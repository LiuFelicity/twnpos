import pandas as pd
from pyecharts.charts import Sankey
from pyecharts import options as opts
import os      
import sys     
import argparse 
from collections import defaultdict 

# --- 0. 設定參數解析 ---
parser = argparse.ArgumentParser(description="從 Excel 檔案生成 Sankey 圖表 HTML。")
parser.add_argument("input_file", help="來源 Excel 檔案的路徑 (例如: data/A0226_112.xlsx)")
parser.add_argument(
    "-np", "--node-percentage",
    type=float,
    default=5.0, 
    help="設定一個節點百分比門檻 (0-100)。只有「總流量」大於 '總收入 * 百分比' 的「節點」，才會在名稱後顯示其總金額。預設值: 5.0"
)
args = parser.parse_args()

# --- 1. 設定固定參數 ---
SOURCE_COL_INDEX = 0  # 第 A 欄 '來源'
TARGET_COL_INDEX = 1  # 第 B 欄 '目標'
VALUE_COL_INDEX = 4   # 第 E 欄 '金額（萬元）（手動調整）'

# 使用參數傳入的檔案路徑
file_path = args.input_file

# --- 2. 讀取與準備資料 --- (保持不變)
try:
    df = pd.read_excel(file_path, header=0) 
except FileNotFoundError:
    sys.stderr.write(f"!!! 錯誤：找不到檔案。\n")
    sys.exit(1)
except Exception as e:
    sys.stderr.write(f"讀取檔案時出錯: {e}\n")
    sys.exit(1)

# --- 3. 透過索引取得欄位名稱 --- (保持不變)
try:
    source_col = df.columns[SOURCE_COL_INDEX]
    target_col = df.columns[TARGET_COL_INDEX]
    value_col = df.columns[VALUE_COL_INDEX]
except IndexError:
    sys.stderr.write(f"!!! 錯誤：欄位索引超出範圍。\n")
    sys.exit(1)

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

# --- 4A. 建立 Links 並計算 Node 總和 --- 
links_data = []
node_sum_in = defaultdict(float)
node_sum_out = defaultdict(float)

for idx, row in df.iterrows():
    source_name = row[source_col]
    target_name = row[target_col]
    value = row[value_col]
    
    links_data.append({
        "source": source_name,
        "target": target_name,
        "value": value
    })
    node_sum_in[target_name] += value
    node_sum_out[source_name] += value

# --- 4B. 計算門檻 ---
all_labels = list(pd.concat([df[source_col], df[target_col]]).unique())
node_totals = {}
for label in all_labels:
    node_totals[label] = max(node_sum_in[label], node_sum_out[label])

all_targets = set(df[target_col])
root_nodes = [label for label in all_labels if label not in all_targets and node_sum_out[label] > 0]

total_sum = sum(node_totals[root] for root in root_nodes)
value_threshold = total_sum * (args.node_percentage / 100)

print(f"--- 處理中 ---")
print(f"總收入 (根節點 tổng hợp): {total_sum:,.2f}")
print(f"節點標籤顯示門檻: {args.node_percentage}% ( > {value_threshold:,.2f} 萬元)")
print("---------------\n")

# --- 4C. 建立排序過的 Nodes ★ --- 
node_total_list = []
for label in all_labels:
    node_total_list.append((label, node_totals.get(label, 0)))
    
node_total_list.sort(key=lambda x: x[1], reverse=True)

nodes_data = []
for label, node_total in node_total_list:
    
    node_label_opts = opts.LabelOpts(
        is_show=True, position="right", formatter="{b}", font_size=10
    )
    
    if node_total > value_threshold:
        node_label_opts = opts.LabelOpts(
            is_show=True,
            position="right",
            formatter=f"{{b}}  {node_total:,.1f}", 
            font_size=10,
            font_weight="bold" 
        )

    nodes_data.append({
        "name": label,
        "label": node_label_opts 
    })

# --- 5. 建立 Sankey 圖表 (Pyecharts) ---
c = (
    Sankey()
    .add(
        series_name="財務流向",
        nodes=nodes_data, # 傳入排序過的 nodes_data
        links=links_data,
        node_align="left", 
        levels=[
            opts.SankeyLevelsOpts(depth=0, itemstyle_opts=opts.ItemStyleOpts(color="#ABD9E9")),
            opts.SankeyLevelsOpts(depth=1, itemstyle_opts=opts.ItemStyleOpts(color="#2C7BB6")),
            opts.SankeyLevelsOpts(depth=2, itemstyle_opts=opts.ItemStyleOpts(color="#FEE090")),
            opts.SankeyLevelsOpts(depth=3, itemstyle_opts=opts.ItemStyleOpts(color="#D7191C")),
            opts.SankeyLevelsOpts(depth=4, itemstyle_opts=opts.ItemStyleOpts(color="#FFC0CB")),
        ],
        linestyle_opt=opts.LineStyleOpts(opacity=0.3, curve=0.5, color="gradient"),
    )
    .set_series_opts(
        edge_label=opts.LabelOpts(
            is_show=False, 
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

output_dir = "result"
os.makedirs(output_dir, exist_ok=True)

base_name = os.path.basename(file_path)
file_name_without_ext = os.path.splitext(base_name)[0]
output_name = f"{file_name_without_ext}_sankey_np{args.node_percentage}.html"

output_file_path = os.path.join(output_dir, output_name)

c.render(output_file_path)

print(f"Pyecharts Sankey 圖表已成功生成！")
print(f"檔案已儲存為: {os.path.realpath(output_file_path)}")