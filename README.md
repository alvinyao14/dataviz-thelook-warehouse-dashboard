# TheLook Warehouse Fulfillment Dashboard

An interactive data application to track logistics performance, identify shipping bottlenecks, and calculate revenue leakage for TheLook Ecommerce.

## Streamlit App Structure
This app follows a modular architecture. Please do not dump code into `main.py`.

### File Structure
```text
thelook-warehouse-dashboard/
├── main.py                  # Entry point (Navigation & Layout)
├── data_loader.py           # Data processing & Caching
├── requirements.txt         # Python dependencies
├── data/
│   └── warehouse_data.csv   # (IGNORED BY GIT - Must add manually!)
└── tabs/                    # Feature Modules
    ├── tab_exceptions.py    # (Ops) Late deliveries & risk flags
    ├── tab_network.py       # (Logistics) Geo-maps
    ├── tab_revenue.py       # (Finance) Revenue leakage
    └── tab_dead_stock.py    # (Inventory) Aging stock
```

## Getting Started

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment
```bash
conda create -n warehouse_env python=3.12 -y
conda activate warehouse_env
```

### 3. Import Data Manually [IMPORTANT]
The dataset is git-ignored because it exceeds GitHub's file size limit, please download 'BigQuery_Output_20251206_v1.csv' from the Google Drive.
1. Download 'BigQuery_Output_20251206_v1.csv'
2. Move the CSV under the data/ folder

### 4. Install Packages and Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the App
```bash
streamlit run main.py
```

## Developer Rules

Each tab file must contain a primary render function that accepts the dataframe:
```python
def render_tab(df):
    st.header("My Feature Title")
    # Your logic here
```
