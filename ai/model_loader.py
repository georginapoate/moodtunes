import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import MultiLabelBinarizer
import joblib

print("🔄 Training genre classifier...")
# Load and preprocess data
df = pd.read_csv("../data/tag_dataset.csv")
df['tags'] = df['tags'].apply(lambda x: [tag.strip() for tag in x.split(',')])

# Convert tags to binary vectors
mlb = MultiLabelBinarizer()
Y = mlb.fit_transform(df['tags'])

# Save tag names
joblib.dump(mlb, "tag_binarizer.pkl")

# Convert prompts to embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')
X = model.encode(df['prompt'].tolist())

# Train classifier
clf = MLPClassifier(hidden_layer_sizes=(128,), max_iter=500, random_state=42)
clf.fit(X, Y)

# Save model
joblib.dump(clf, "genre_classifier.pkl")
print("✅ Classifier and label binarizer saved.")
