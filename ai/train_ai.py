from tag_predictor import TagPredictor, MLP_MODEL_PATH # Import the class
import os
import pandas as pd

if __name__ == "__main__":
    print("Starting the AI model training process...")

    # 1. Prepare or ensure your training data exists
    # (This part was also in the __main__ block of tag_predictor.py,
    #  but it's better organized here for a dedicated training script)
    training_data_path = os.path.join(os.path.dirname(__file__), "..", "data", "prompts_tags.csv")
    # training_data_path = "../data/prompts_tags.csv" # Adjust path if running from root
    
    path_to_data = os.path.join(os.path.dirname(__file__), "..", "data")
    if not os.path.exists(path_to_data):
        os.makedirs(path_to_data)

    if not os.path.exists(training_data_path):
        print(f"Training data {training_data_path} not found. Creating dummy data...")
        dummy_df = pd.DataFrame([
            {"prompt_text": "sad songs for a rainy day", "tags": "sad;mellow;acoustic"},
            {"prompt_text": "energetic workout music", "tags": "electronic;energetic;upbeat;dance"},
            {"prompt_text": "chill study session", "tags": "lofi;chill;instrumental;study"},
            {"prompt_text": "80s party mix", "tags": "80s;pop;synthpop;party"},
            {"prompt_text": "calm meditation sounds", "tags": "ambient;meditation;calm;instrumental"},
            {"prompt_text": "upbeat morning commute", "tags": "upbeat;pop;happy;morning"},
            {"prompt_text": "dark and broody atmosphere", "tags": "dark ambient;industrial;goth"},
            {"prompt_text": "songs for coding late night", "tags": "electronic;focus;instrumental;lofi"},
            {"prompt_text": "romantic dinner playlist", "tags": "jazz;soul;romantic;mellow"},
            {"prompt_text": "aggressive gym session", "tags": "metal;hard rock;energetic;workout"}
        ])
        dummy_df.to_csv(training_data_path, index=False)
        print(f"Created dummy data at {training_data_path}")
    else:
        print(f"Using existing training data from {training_data_path}")

    # 2. Initialize the TagPredictor
    #    The TagPredictor class itself is defined in ai/tag_predictor.py
    predictor_instance = TagPredictor()

    # 3. Run the training process
    #    This calls the .train() method of the TagPredictor class.
    print("Starting model training...")
    predictor_instance.train(data_path=training_data_path, epochs=50, lr=1e-4, batch_size=16) # Adjust params as needed
    print("Model training complete.")

    # 4. (Optional) Test prediction after training
    print("\nTesting prediction with the newly trained model:")
    test_prompt = "I'm getting bullied in school"
    predicted_tags = predictor_instance.predict(test_prompt, threshold=0.2, top_n=3)
    print(f"Test Prediction - Prompt: '{test_prompt}' -> Predicted tags: {predicted_tags}")

    test_prompt_2 = "feeling down, need something mellow"
    predicted_tags_2 = predictor_instance.predict(test_prompt_2, threshold=0.2, top_n=3)
    print(f"Test Prediction - Prompt: '{test_prompt_2}' -> Predicted tags: {predicted_tags_2}")