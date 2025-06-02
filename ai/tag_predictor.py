import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sentence_transformers import SentenceTransformer
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
import numpy as np
import os

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODEL_DIR, exist_ok=True)
SBERT_MODEL_NAME = 'all-MiniLM-L6-v2' # Or another suitable model
MLP_MODEL_PATH = os.path.join(MODEL_DIR, "tag_mlp_model.pt")
MLB_CLASSES_PATH = os.path.join(MODEL_DIR, "mlb_classes.npy")

class PromptTagDataset(Dataset):
    def __init__(self, prompts, embeddings, labels):
        self.prompts = prompts
        self.embeddings = embeddings
        self.labels = labels

    def __len__(self):
        return len(self.embeddings)

    def __getitem__(self, idx):
        return self.embeddings[idx], self.labels[idx]

class TagMLP(nn.Module):
    def __init__(self, input_dim, num_tags):
        super(TagMLP, self).__init__()
        self.fc1 = nn.Linear(input_dim, 256)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(256, num_tags)
        self.sigmoid = nn.Sigmoid() # For multi-label classification

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        x = self.sigmoid(x)
        return x

class TagPredictor:
    def __init__(self, sbert_model_name=SBERT_MODEL_NAME):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")
        self.sbert_model = SentenceTransformer(sbert_model_name, device=self.device)
        self.mlp_model = None
        self.mlb = None # MultiLabelBinarizer

        # Try to load a pre-trained model
        if os.path.exists(MLP_MODEL_PATH) and os.path.exists(MLB_CLASSES_PATH):
            print(f"Loading pre-trained MLP model from {MLP_MODEL_PATH}")
            self.mlb = MultiLabelBinarizer()
            self.mlb.classes_ = np.load(MLB_CLASSES_PATH, allow_pickle=True)
            sbert_output_dim = self.sbert_model.get_sentence_embedding_dimension()
            self.mlp_model = TagMLP(sbert_output_dim, len(self.mlb.classes_))
            self.mlp_model.load_state_dict(torch.load(MLP_MODEL_PATH, map_location=self.device))
            self.mlp_model.to(self.device)
            self.mlp_model.eval()
        else:
            print("No pre-trained MLP model found. Call train() first.")

    def _preprocess_data(self, data_path="ai/data/prompts_tags.csv"):
        """
        Reads data from CSV (prompt_text, tags separated by ';').
        Returns prompts, one-hot encoded labels, and the MultiLabelBinarizer.
        """
        df = pd.read_csv(data_path)
        df['tags_list'] = df['tags'].apply(lambda x: [tag.strip() for tag in x.split(',')] if pd.notnull(x) else [])
        mlb = MultiLabelBinarizer()
        labels = mlb.fit_transform(df['tags_list'])
        np.save(MLB_CLASSES_PATH, mlb.classes_, allow_pickle=True) # Save classes for inference
        self.mlb = mlb # Store for later use

        prompts = df['prompt_text'].tolist()
        print(f"Generating embeddings for {len(prompts)} prompts...")
        # Batch processing for SBERT is much faster
        embeddings = self.sbert_model.encode(prompts, convert_to_tensor=True, show_progress_bar=True)
        return prompts, embeddings.cpu(), torch.tensor(labels, dtype=torch.float32)


    def train(self, data_path="ai/data/prompts_tags.csv", epochs=20, lr=1e-4, batch_size=32):
        if self.mlb is None: # Ensure MLB is fitted if not loaded
            prompts, embeddings, labels = self._preprocess_data(data_path)
        else: # MLB already loaded or fitted
            # This path might need adjustment if you call train multiple times with different data.
            # For simplicity, assuming data_path is consistent with mlb.
            df = pd.read_csv(data_path)
            df['tags_list'] = df['tags'].apply(lambda x: [tag.strip() for tag in x.split(',')] if pd.notnull(x) else [])
            labels_for_split = self.mlb.transform(df['tags_list']) # Use existing mlb
            prompts = df['prompt_text'].tolist()
            print(f"Generating embeddings for {len(prompts)} prompts...")
            embeddings = self.sbert_model.encode(prompts, convert_to_tensor=True, show_progress_bar=True).cpu()
            labels = torch.tensor(labels_for_split, dtype=torch.float32)


        # Split data
        train_embeddings, val_embeddings, train_labels, val_labels = train_test_split(
            embeddings, labels, test_size=0.2, random_state=42
        )

        # Create DataLoaders
        train_dataset = PromptTagDataset(None, train_embeddings, train_labels) # Prompts not needed for DataLoader
        val_dataset = PromptTagDataset(None, val_embeddings, val_labels)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size)

        sbert_output_dim = self.sbert_model.get_sentence_embedding_dimension()
        num_tags = len(self.mlb.classes_)
        self.mlp_model = TagMLP(sbert_output_dim, num_tags).to(self.device)

        criterion = nn.BCELoss() # Binary Cross-Entropy for multi-label
        optimizer = optim.Adam(self.mlp_model.parameters(), lr=lr)

        print(f"Training MLP with {num_tags} tags...")
        for epoch in range(epochs):
            self.mlp_model.train()
            total_loss = 0
            for emb_batch, label_batch in train_loader:
                emb_batch, label_batch = emb_batch.to(self.device), label_batch.to(self.device)
                optimizer.zero_grad()
                outputs = self.mlp_model(emb_batch)
                loss = criterion(outputs, label_batch)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            avg_train_loss = total_loss / len(train_loader)

            # Validation
            self.mlp_model.eval()
            total_val_loss = 0
            with torch.no_grad():
                for emb_batch, label_batch in val_loader:
                    emb_batch, label_batch = emb_batch.to(self.device), label_batch.to(self.device)
                    outputs = self.mlp_model(emb_batch)
                    loss = criterion(outputs, label_batch)
                    total_val_loss += loss.item()
            avg_val_loss = total_val_loss / len(val_loader)
            print(f"Epoch [{epoch+1}/{epochs}], Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")

        torch.save(self.mlp_model.state_dict(), MLP_MODEL_PATH)
        print(f"MLP model saved to {MLP_MODEL_PATH}")

    def predict(self, prompt_text: str, threshold=0.3, top_n=5) -> list[str]:
        if not self.mlp_model or not self.mlb:
            print("Model not trained or loaded. Please train or ensure model files exist.")
            return []

        self.mlp_model.eval()
        with torch.no_grad():
            embedding = self.sbert_model.encode(prompt_text, convert_to_tensor=True).to(self.device)
            # SBERT might return a 2D tensor if input is a list, ensure it's 1D for single prompt
            if embedding.ndim > 1:
                embedding = embedding.squeeze(0)
            
            output_probs = self.mlp_model(embedding.unsqueeze(0)) # Add batch dim for MLP

        output_probs = output_probs.squeeze().cpu().numpy() # Remove batch dim and move to numpy

        # Method 1: Thresholding
        # predicted_indices = np.where(output_probs > threshold)[0]
        # predicted_tags = self.mlb.classes_[predicted_indices].tolist()

        # Method 2: Top N
        sorted_indices = np.argsort(output_probs)[::-1] # Sort descending
        top_n_indices = sorted_indices[:top_n]
        # Filter by threshold as well for top_n to ensure relevance
        predicted_tags = [self.mlb.classes_[i] for i in top_n_indices if output_probs[i] > threshold]

        return predicted_tags

# Create a global predictor instance (can be loaded once in ai_service.py)
predictor = TagPredictor()
