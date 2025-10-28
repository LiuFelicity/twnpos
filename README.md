# Initialization

```bash
git submodule init
git submodule update

conda create -p .conda python=3.11
conda activate ./.conda
pip3 install -r requirements.txt

bash download_ckpt.sh
```

# Running

Run from the repository root:

```bash
streamlit run TableNet/app.py
```