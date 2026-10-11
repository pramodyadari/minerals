import pandas as pd
import numpy as np
import os

np.random.seed(42)

# Create 10 years of monthly demo data = 120 records
dates = pd.date_range(
    start="2016-01-01",
    periods=120,
    freq="MS"
)

data = []

for date in dates:

    # Simulated rainfall
    rainfall = np.random.uniform(0, 250)

    # Simulated equipment conditions
    equipment_downtime = np.random.uniform(2, 35)
    blasting_delay = np.random.uniform(0, 20)
    equipment_availability = np.random.uniform(65, 98)

    # Planned production
    planned_production = np.random.uniform(9000, 13000)

    # Production calculation
    rainfall_effect = rainfall * 3
    downtime_effect = equipment_downtime * 80
    blasting_effect = blasting_delay * 60

    production_loss = (
        rainfall_effect
        + downtime_effect
        + blasting_effect
    )

    # Add some natural variation
    noise = np.random.normal(0, 150)

    actual_production = (
        planned_production
        - production_loss
        + noise
    )

    # Prevent unrealistic values
    actual_production = max(
        actual_production,
        1000
    )

    # Calculate shortfall
    shortfall = max(
        planned_production - actual_production,
        0
    )

    data.append({
        "Date": date,
        "Rainfall_mm": round(rainfall, 2),
        "Equipment_Downtime_hr": round(
            equipment_downtime, 2
        ),
        "Blasting_Delay_hr": round(
            blasting_delay, 2
        ),
        "Equipment_Availability_pct": round(
            equipment_availability, 2
        ),
        "Planned_Production_tonnes": round(
            planned_production, 2
        ),
        "Actual_Production_tonnes": round(
            actual_production, 2
        ),
        "Production_Shortfall_tonnes": round(
            shortfall, 2
        )
    })


# Convert to DataFrame
df = pd.DataFrame(data)

# Save dataset
os.makedirs(
    "data/processed",
    exist_ok=True
)

output_file = (
    "data/processed/production_data.csv"
)

df.to_csv(
    output_file,
    index=False
)

print("Improved production dataset created successfully!")
print("Rows:", len(df))
print("Columns:", len(df.columns))
print("File:", output_file)

print("\nFirst 5 records:")
print(df.head())