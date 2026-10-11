import joblib
import pandas as pd
import numpy as np

rf = joblib.load('models/production_random_forest.pkl')
print('Type:', type(rf))
if hasattr(rf, 'feature_names_in_'):
    print('Features:', list(rf.feature_names_in_))
if hasattr(rf, 'feature_importances_'):
    print('Importances:', list(rf.feature_importances_))

# Test sample prediction
df_sample = pd.DataFrame([{
    'Rainfall_mm': 150.0,
    'Equipment_Downtime_hr': 20.0,
    'Blasting_Delay_hr': 8.0,
    'Equipment_Availability_pct': 85.0,
    'Planned_Production_tonnes': 11000.0
}])
pred = rf.predict(df_sample)
print('Predicted sample:', pred[0])
