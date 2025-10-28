# Initialization

```bash
git submodule init
git submodule update

conda create -p .conda python=3.11
conda activate ./.conda
pip install -r requirements.txt
```

# Running

Run from the repository root:

```bash
streamlit run TableNet/app.py
```