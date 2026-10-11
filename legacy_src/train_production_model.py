import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score


# Load production dataset
file_path = "data/processed/production_data.csv"

df = pd.read_csv(file_path)

print("Dataset loaded successfully!")
print("Dataset shape:", df.shape)


# Features used by the ML model
features = [
    "Rainfall_mm",
    "Equipment_Downtime_hr",
    "Blasting_Delay_hr",
    "Equipment_Availability_pct",
    "Planned_Production_tonnes"
]

# Target = actual production
target = "Actual_Production_tonnes"


X = df[features]
y = df[target]


print("\nFeatures:", features)
print("Target:", target)


# Split data into training and testing
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

print("\nTraining samples:", X_train.shape)
print("Testing samples:", X_test.shape)


# Create Random Forest regression model
model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)

print("\nTraining Production Prediction Model...")

model.fit(X_train, y_train)

print("Training completed!")


# Predict production
y_pred = model.predict(X_test)


# Evaluate model
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)


print("\nModel Performance")
print("-------------------------")
print("Mean Absolute Error:", round(mae, 2))
print("R2 Score:", round(r2, 4))


# Save model
model_file = "models/production_random_forest.pkl"

joblib.dump(model, model_file)

print("\nProduction model saved successfully!")
print("File:", model_file)