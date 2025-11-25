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

# --- 2. 讀取與準備資料 ---
if not os.path.isfile(file_path):
    sys.stderr.write("!!! 錯誤：找不到檔案。\n")
    sys.exit(1)

try:
    if file_path.lower().endswith('.csv'):
        df = pd.read_csv(file_path, header=0)
    else:
        df = pd.read_excel(file_path, header=0)
except Exception as e:
    raise SystemExit(f"讀取檔案時出錯: {e}\n")

# --- 3. 透過索引取得欄位名稱 ---
try:
    source_col = df.columns[SOURCE_COL_INDEX]
    target_col = df.columns[TARGET_COL_INDEX]
    value_col = df.columns[VALUE_COL_INDEX]
except IndexError:
    sys.stderr.write("!!! 錯誤：欄位索引超出範圍。\n")
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

# --- 4B. 計算門檻與所有標籤 ---
all_labels = list(pd.concat([df[source_col], df[target_col]]).unique())
node_totals = {}
for label in all_labels:
    node_totals[label] = max(node_sum_in[label], node_sum_out[label])

all_targets = set(df[target_col])
root_nodes = [label for label in all_labels if label not in all_targets and node_sum_out[label] > 0]

total_sum = sum(node_totals[root] for root in root_nodes)
value_threshold = total_sum * (args.node_percentage / 100)

print("--- 處理中 ---")
print(f"總收入 (根節點總和): {total_sum:,.2f}")
print(f"節點標籤顯示門檻: {args.node_percentage}% ( > {value_threshold:,.2f} 萬元)")
print("---------------\n")

# --- 4C. ★★★ 智慧分層排序 (Smart Layered Sort) ★★★ ---

# 1. 建立層級 (BFS)
layers = defaultdict(list)
node_depth = {}

current_layer_nodes = sorted(root_nodes, key=lambda x: node_totals[x], reverse=True)
# 特殊處理：把短絀/餘絀移到該層最後
special_nodes = [n for n in current_layer_nodes if "短絀" in n or "餘絀" in n]
normal_nodes = [n for n in current_layer_nodes if n not in special_nodes]
current_layer_nodes = normal_nodes + special_nodes

for node in current_layer_nodes:
    node_depth[node] = 0
    layers[0].append(node)

depth = 0
while current_layer_nodes:
    next_layer_nodes = []
    for parent in current_layer_nodes:
        children = df[df[source_col] == parent][target_col].unique()
        children = sorted(children, key=lambda x: node_totals[x], reverse=True)
        
        for child in children:
            if child not in node_depth: 
                node_depth[child] = depth + 1
                layers[depth + 1].append(child)
                next_layer_nodes.append(child)
    
    depth += 1
    current_layer_nodes = next_layer_nodes

# 2. 建立最終的排序列表
final_sorted_nodes = []
for d in sorted(layers.keys()):
    layer_nodes = layers[d]
    
    # 在每一層內部，再次確保 "短絀/餘絀" 在最後面
    layer_special = [n for n in layer_nodes if "短絀" in n or "餘絀" in n]
    layer_normal = [n for n in layer_nodes if n not in layer_special]
    
    final_sorted_nodes.extend(layer_normal)
    final_sorted_nodes.extend(layer_special)

# --- 4D. 建立 Nodes Data (包含強制上色) ---
nodes_data = []
for label in final_sorted_nodes:
    node_total = node_totals[label]
    
    # 1. 建立標籤設定
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

    # 2. 建立基本節點資料
    node_data_item = {
        "name": label,
        "label": node_label_opts 
    }

    # 3. ★★★ 強力上色 (使用 itemStyle 原始字典) ★★★
    # 這能繞過 Pyecharts 的 levels 覆蓋
    
    if "餘絀" in label: # 包含 "餘絀" (盈餘) -> 深藍色
        node_data_item["itemStyle"] = {"color": "#2C7BB6", "borderColor": "#2C7BB6"}
        print(f"-> 強制上色 (藍): {label}")
    
    elif "短絀" in label: # 包含 "短絀" (虧損) -> 綠色
        node_data_item["itemStyle"] = {"color": "#11B795", "borderColor": "#11B795"}
        print(f"-> 強制上色 (綠): {label}")

    nodes_data.append(node_data_item)

# --- 5. 建立 Sankey 圖表 (Pyecharts) ---
c = (
    Sankey()
    .add(
        series_name="財務流向",
        nodes=nodes_data, 
        links=links_data,
        node_align="left", 
        
        # 保持關閉自動佈局，依賴我們的「智慧分層排序」
        layout_iterations=0, 
        
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
        title_opts=opts.TitleOpts(title=""),
        legend_opts=opts.LegendOpts(is_show=False),
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

print("Pyecharts Sankey 圖表已成功生成！")
print(f"檔案已儲存為: {os.path.realpath(output_file_path)}")