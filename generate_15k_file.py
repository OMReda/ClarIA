import pandas as pd
import numpy as np
from pathlib import Path

np.random.seed(42)
rows = 15000

data = {
    'OrderID': [f"ORD-{i:05d}" for i in range(1, rows + 1)],
    'Amount': np.random.uniform(10.0, 1000.0, rows).round(2),
    'Category': np.random.choice(['Electronics', 'Clothing', 'Home', 'Toys'], rows),
    'Year': np.random.choice([2023, 2024], rows),
}

df = pd.DataFrame(data)

out_path = Path("Fake_SAP_Dataset_15000_Rows.xlsx")
df.to_excel(out_path, index=False)
print(f"Generated {out_path.absolute()}")
