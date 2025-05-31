import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import os
from google.cloud import storage  # Only needed if using GCP upload

# Set page config
st.set_page_config(
    page_title="Retail Sales Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_data():
    """Load and preprocess data with comprehensive error handling"""
    try:
        # Verify file exists
        if not os.path.exists("data/superstore.csv"):
            st.error("Error: File 'data/superstore.csv' not found")
            return None

        # Load with multiple encoding attempts
        encodings = ['utf-8', 'latin1', 'windows-1252']
        for encoding in encodings:
            try:
                df = pd.read_csv("data/superstore.csv", encoding=encoding)
                
                # Standardize column names (case-insensitive, strip whitespace)
                df.columns = df.columns.str.strip().str.lower()
                df = df.rename(columns={
                    'profit': 'profit',
                    'discount': 'discount',
                    'order date': 'order_date',
                    'sales': 'sales',
                    'region': 'region'
                })
                
                # Convert date with multiple format attempts
                date_formats = ['%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d']
                for fmt in date_formats:
                    try:
                        df['order_date'] = pd.to_datetime(df['order_date'], format=fmt)
                        break
                    except:
                        continue
                else:
                    df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
                
                # Create month-year column
                df['month_year'] = df['order_date'].dt.strftime('%b-%Y')
                
                # Ensure numeric columns
                num_cols = ['profit', 'discount', 'sales']
                for col in num_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                return df
                
            except Exception as e:
                continue
                
        st.error("Failed to load data with all encoding attempts")
        return None
        
    except Exception as e:
        st.error(f"Unexpected error loading data: {str(e)}")
        return None

# Load data
df = load_data()

if df is None:
    st.stop()  # Stop execution if data loading failed

# --- Dashboard Layout ---
st.title("📊 Retail Sales Visualizer")
st.markdown("Analyzing sales trends and profitability")

# --- Sidebar Filters ---
st.sidebar.header("Filters")
available_regions = df['region'].unique() if 'region' in df.columns else []
selected_region = st.sidebar.multiselect(
    "Select Regions",
    options=available_regions,
    default=available_regions[:2] if len(available_regions) > 0 else []
)

# Filter data
filtered_df = df[df['region'].isin(selected_region)] if 'region' in df.columns else df

# --- Visualizations ---
tab1, tab2, tab3 = st.tabs(["Sales Trends", "Regional Analysis", "Profit Correlation"])

with tab1:
    if 'month_year' in filtered_df.columns and 'sales' in filtered_df.columns:
        st.subheader("📈 Monthly Sales Trend")
        monthly_sales = filtered_df.groupby('month_year')['sales'].sum().reset_index()
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(monthly_sales['month_year'], monthly_sales['sales'], marker='o')
        plt.xticks(rotation=45)
        st.pyplot(fig)
    else:
        st.warning("Required columns for sales trend not available")

with tab2:
    if 'region' in filtered_df.columns and 'sales' in filtered_df.columns:
        st.subheader("🌍 Sales by Region")
        region_sales = filtered_df.groupby('region')['sales'].sum().reset_index()
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(x='region', y='sales', data=region_sales, ax=ax)
        st.pyplot(fig)
    else:
        st.warning("Required columns for regional analysis not available")

with tab3:
    if 'profit' in filtered_df.columns and 'discount' in filtered_df.columns:
        st.subheader("🔥 Profit vs Discount Correlation")
        correlation = filtered_df[['profit', 'discount']].corr()
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(correlation, annot=True, fmt=".2f", cmap='coolwarm', center=0, ax=ax)
        st.pyplot(fig)
    else:
        missing = []
        if 'profit' not in filtered_df.columns:
            missing.append("profit")
        if 'discount' not in filtered_df.columns:
            missing.append("discount")
        st.warning(f"Missing columns for correlation analysis: {', '.join(missing)}")

# --- GCP Upload (Optional) ---
if st.sidebar.checkbox("Enable GCP Upload"):
    try:
        # Save visualizations
        if 'month_year' in filtered_df.columns and 'sales' in filtered_df.columns:
            plt.savefig("monthly_sales.png")
        if 'region' in filtered_df.columns and 'sales' in filtered_df.columns:
            plt.savefig("region_sales.png")
        if 'profit' in filtered_df.columns and 'discount' in filtered_df.columns:
            plt.savefig("profit_discount.png")
        
        # Upload to GCP
        bucket_name = st.sidebar.text_input("GCP Bucket Name", "your-bucket-name")
        if st.sidebar.button("Upload to GCP"):
            try:
                from scripts.gcp_upload import upload_to_gcp
                upload_to_gcp(bucket_name, "monthly_sales.png", "monthly_sales.png")
                upload_to_gcp(bucket_name, "region_sales.png", "region_sales.png")
                upload_to_gcp(bucket_name, "profit_discount.png", "profit_discount.png")
                st.sidebar.success("Upload completed!")
            except Exception as e:
                st.sidebar.error(f"Upload failed: {str(e)}")
    except Exception as e:
        st.sidebar.error(f"Visualization save failed: {str(e)}")

# --- Data Summary ---
st.sidebar.header("Data Summary")
if st.sidebar.checkbox("Show raw data"):
    st.write(filtered_df)

if st.sidebar.checkbox("Show column info"):
    st.write(pd.DataFrame({
        'Column': df.columns,
        'Data Type': df.dtypes.astype(str),
        'Missing Values': df.isna().sum(),
        'Unique Values': df.nunique()
    }))