import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sentence_transformers import SentenceTransformer
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
import random
import string

# Generate mock dataset
random.seed(42)
np.random.seed(42)

# Simulate tags and features for 100 songs
tags = [
    "sad cinematic", "happy pop", "energetic workout", "melancholy indie",
    "romantic ballad", "dark orchestral", "upbeat dance", "mellow chill",
    "intense metal", "lofi study", "funk groove", "epic soundtrack",
    "jazzy smooth", "angry punk", "emotional acoustic"
]
data = []

for _ in range(100):
    tag = random.choice(tags)
    features = {
        "danceability": np.clip(np.random.normal(0.5, 0.2), 0, 1),
        "energy": np.clip(np.random.normal(0.5, 0.3), 0, 1),
        "valence": np.clip(np.random.normal(0.5, 0.3), 0, 1),
        "tempo": np.clip(np.random.normal(120, 30), 60, 200)
    }
    data.append({"tags": tag, **features})

df = pd.DataFrame(data)

# Embed tags using SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(df["tags"].tolist())

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(embeddings, df[["danceability", "energy", "valence", "tempo"]].values, test_size=0.2, random_state=42)

# Train regressor
regressor = MLPRegressor(hidden_layer_sizes=(128, 64), activation='relu', max_iter=500, random_state=42)
regressor.fit(X_train, y_train)

# Predict and evaluate
predictions = regressor.predict(X_test)
mse = mean_squared_error(y_test, predictions)
print(f"Mean Squared Error: {mse:.4f}")

# Show some results
results_df = pd.DataFrame({
    "tags": df.iloc[y_test.argmax(axis=1)]['tags'].values,
    "predicted_danceability": predictions[:, 0],
    "predicted_energy": predictions[:, 1],
    "predicted_valence": predictions[:, 2],
    "predicted_tempo": predictions[:, 3],
    "true_danceability": y_test[:, 0],
    "true_energy": y_test[:, 1],
    "true_valence": y_test[:, 2],
    "true_tempo": y_test[:, 3],
})

# print while the ai is training to see live results
print("Predictions vs Ground Truth:")
print("--------------------------------------------------")
print("tags\t\tpredicted_danceability\tpredicted_energy\tpredicted_valence\tpredicted_tempo\ttrue_danceability\ttrue_energy\ttrue_valence\ttrue_tempo")
for i in range(len(results_df)):
    print(f"{results_df.iloc[i]['tags']}\t{results_df.iloc[i]['predicted_danceability']:.2f}\t\t{results_df.iloc[i]['predicted_energy']:.2f}\t\t{results_df.iloc[i]['predicted_valence']:.2f}\t\t{results_df.iloc[i]['predicted_tempo']:.2f}\t\t{results_df.iloc[i]['true_danceability']:.2f}\t\t{results_df.iloc[i]['true_energy']:.2f}\t\t{results_df.iloc[i]['true_valence']:.2f}\t\t{results_df.iloc[i]['true_tempo']:.2f}")
print("--------------------------------------------------")
print(results_df.head(10).to_string(index=False))

results_df.to_csv("prediction_vs_actual.csv", index=False)


# import ace_tools as tools; tools.display_dataframe_to_user(name="Prediction vs Ground Truth", dataframe=results_df.head(10))
