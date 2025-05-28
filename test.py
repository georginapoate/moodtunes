import pickle

# pkl file should contain a list of tags
def load_tags_from_pkl(file_path):
    try:
        with open(file_path, 'rb') as file:
            tags = pickle.load(file)
            if isinstance(tags, list):
                return tags
            else:
                raise ValueError("Loaded data is not a list.")
    except Exception as e:
        print(f"⚠️ Error loading tags from {file_path}: {e}")
        return []
    
if __name__ == "__main__":
    file_path = "data/tags_list.pkl"  # Adjust the path as needed
    tags = load_tags_from_pkl(file_path)
    
    if tags:
        print(f"✅ Loaded {len(tags)} tags from {file_path}")
        for tag in tags:
            print(tag)
    else:
        print("❌ No tags loaded or an error occurred.")