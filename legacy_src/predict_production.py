import joblib
import pandas as pd

# Load trained production model
model_file = "models/production_random_forest.pkl"

model = joblib.load(model_file)

print("Production model loaded successfully!")


# --------------------------------------------------
# Example future operating conditions
# --------------------------------------------------

rainfall = 150
equipment_downtime = 20
blasting_delay = 8
equipment_availability = 85
planned_production = 11000


# Create input for the model
input_data = pd.DataFrame({
    "Rainfall_mm": [rainfall],
    "Equipment_Downtime_hr": [equipment_downtime],
    "Blasting_Delay_hr": [blasting_delay],
    "Equipment_Availability_pct": [equipment_availability],
    "Planned_Production_tonnes": [planned_production]
})


# Predict production
predicted_production = model.predict(input_data)[0]

# Calculate expected shortfall
shortfall = max(
    planned_production - predicted_production,
    0
)


# Determine risk level
if shortfall >= 2500:
    risk = "HIGH"
elif shortfall >= 1000:
    risk = "MEDIUM"
else:
    risk = "LOW"


# Recommend corrective action
if risk == "HIGH":
    action = (
        "Redeploy equipment, optimize blasting schedule, "
        "and adjust mine production plan."
    )

elif risk == "MEDIUM":
    action = (
        "Monitor equipment downtime and optimize "
        "blasting and mine scheduling."
    )

else:
    action = (
        "Continue normal operations and monitor "
        "weather and equipment performance."
    )


# Display results
print("\n========================================")
print("     MANGANESE PRODUCTION FORECAST")
print("========================================")

print("\nInput Conditions")
print("----------------------------------------")
print("Rainfall:", rainfall, "mm")
print("Equipment Downtime:", equipment_downtime, "hours")
print("Blasting Delay:", blasting_delay, "hours")
print("Equipment Availability:", equipment_availability, "%")
print("Planned Production:", planned_production, "tonnes")

print("\nAI Prediction")
print("----------------------------------------")
print(
    "Predicted Production:",
    round(predicted_production, 2),
    "tonnes"
)

print(
    "Expected Shortfall:",
    round(shortfall, 2),
    "tonnes"
)

print("Risk Level:", risk)

print("\nRecommended Action")
print("----------------------------------------")
print(action)

print("\n========================================")