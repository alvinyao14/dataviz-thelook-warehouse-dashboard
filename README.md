# TheLook Warehouse Fulfillment Dashboard

An interactive data application to track logistics performance, identify shipping bottlenecks, and calculate revenue leakage for TheLook Ecommerce.

## Streamlit App Structure
│
├── main.py		        # The "Container" (Navigation & Layout)
├── data_loader.py	    # The script to load/cache data
├── requirements.txt	
├── data/
│   └── BigQuery_Output_20251206_v1.csv	# The output from BigQuery
│
└── tabs/
    ├── __init__.py
    ├── tab_exceptions.py 
    ├── tab_network.py	
    ├── tab_revenue.py
    └── tab_dead_stock.py 

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