import pandas as pd
import numpy as np
from pathlib import Path

# Create a deterministic fake SAP dataset with exactly 5000 rows
np.random.seed(42)
rows = 5000

data = {
    'OrderID': [f"ORD-{i:05d}" for i in range(1, rows + 1)],
    'Amount': np.random.uniform(10.0, 1000.0, rows).round(2),
    'Category': np.random.choice(['Electronics', 'Clothing', 'Home', 'Toys'], rows),
    'Year': np.random.choice([2023, 2024], rows),
}

df = pd.DataFrame(data)

out_path = Path("Fake_SAP_Dataset_5000_Rows.xlsx")
df.to_excel(out_path, index=False)
print(f"Generated {out_path.absolute()}")

# Print exactly what the total amount is for verification
print(f"Total Amount for all rows: {df['Amount'].sum():.2f}")
print(f"Total Amount for Year 2024: {df[df['Year'] == 2024]['Amount'].sum():.2f}")
print(f"Total Amount for Year 2024 AND Category Electronics: {df[(df['Year'] == 2024) & (df['Category'] == 'Electronics')]['Amount'].sum():.2f}")
