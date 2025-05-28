from sentence_transformers import SentenceTransformer
import joblib

# Load models
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
classifier = joblib.load('genre_classifier.pkl')
mlb = joblib.load('tag_binarizer.pkl')

def predict_tags(prompt: str):
    embedding = embedding_model.encode([prompt])
    y_pred = classifier.predict(embedding)
    predicted_tags = mlb.inverse_transform(y_pred)[0]
    return list(predicted_tags)

# Example usage
test_prompt = "i woke up in the past"
print(predict_tags(test_prompt))
