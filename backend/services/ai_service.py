# backend/services/ai_service.py
from typing import List
from ai.tag_predictor import predictor # Import the globally initialized predictor instance
from fastapi import HTTPException # Optional: for raising errors if model not ready

# You might want to configure default prediction parameters here or pass them from the endpoint
DEFAULT_PREDICTION_THRESHOLD = 0.3
DEFAULT_TOP_N_TAGS = 5

async def predict_tags_from_prompt(
    prompt: str,
    threshold: float = DEFAULT_PREDICTION_THRESHOLD,
    top_n: int = DEFAULT_TOP_N_TAGS
) -> List[str]:
    """
    Uses the pre-loaded AI model to predict tags from a user prompt.

    Args:
        prompt: The user's text prompt.
        threshold: The confidence threshold for a tag to be included.
        top_n: The maximum number of tags to return (after thresholding).

    Returns:
        A list of predicted tag strings.

    Raises:
        HTTPException: If the AI model is not loaded or an error occurs.
                       (Consider how you want to handle this: return empty list or raise)
    """
    if not predictor.mlp_model or not predictor.mlb:
        # This check ensures the model was successfully loaded by TagPredictor's __init__
        print("AI Service Error: Model not loaded. Ensure it has been trained and model files exist in ai/models/.")
        # Option 1: Raise an error that FastAPI can catch and return to the client
        raise HTTPException(status_code=503, detail="AI model is not available at the moment. Please try again later.")
        # Option 2: Return an empty list and let the calling function handle it
        # return []

    try:
        predicted_tags = predictor.predict(prompt_text=prompt, threshold=threshold, top_n=top_n)
        print(f"AI Service: Prompt='{prompt}', Predicted Tags='{predicted_tags}' (Threshold: {threshold}, Top N: {top_n})")
        return predicted_tags
    except Exception as e:
        # Catch any unexpected errors during prediction
        print(f"AI Service Error during prediction for prompt '{prompt}': {e}")
        # Option 1: Re-raise as HTTPException
        raise HTTPException(status_code=500, detail=f"An error occurred during AI tag prediction.")
        # Option 2: Return empty list
        # return []

# How it's used in backend/main.py (as you already have a similar placeholder):
# from .services.ai_service import predict_tags_from_prompt
#
# @app.post("/generate-playlist", ...)
# async def generate_playlist_endpoint(request: PromptRequest):
#     # ...
#     predicted_tags = await predict_tags_from_prompt(request.prompt) # You can override threshold/top_n here if needed
#     # ...