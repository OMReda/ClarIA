import pandas as pd

def independent_sum():
    file_path = "Fake_SAP_Dataset_5000_Rows.xlsx"
    print(f"Reading {file_path} independently...")
    df = pd.read_excel(file_path)
    
    total_unfiltered = df['Amount'].sum()
    print(f"Independent Pandas Sum (Unfiltered): {total_unfiltered:.2f}")
    
    total_2024 = df[df['Year'] == 2024]['Amount'].sum()
    print(f"Independent Pandas Sum (Year=2024): {total_2024:.2f}")

if __name__ == "__main__":
    independent_sum()
