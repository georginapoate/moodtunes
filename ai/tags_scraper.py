import pylast
import time
import os
import joblib

from dotenv import load_dotenv
load_dotenv()
# Last.fm API credentials   


lastfm_key = os.getenv("LASTFM_API_KEY")
lastfm_secret = os.getenv("LASTFM_API_SECRET")
lastfm_username = os.getenv("LASTFM_USERNAME")
password_hash = pylast.md5(os.getenv("LASTFM_PASSWORD_HASH"))

network = pylast.LastFMNetwork(api_key=lastfm_key, api_secret=lastfm_secret, username=lastfm_username, password_hash=password_hash)

def collect_expanded_tags(tag_limit=100, track_limit=30):
    base_tags = network.get_top_tags(limit=tag_limit)
    all_tags = set()

    for tag_obj in base_tags:
        tag_name = tag_obj.item.get_name().lower()
        all_tags.add(tag_name)

        print(f"▶️ Expanding from tag: {tag_name}")
        try:
            tracks = tag_obj.item.get_top_tracks(limit=track_limit)
            for track_obj, _ in tracks:
                try:
                    track_tags = track_obj.get_top_tags(limit=5)
                    for t in track_tags:
                        all_tags.add(t.item.get_name().lower())
                except:
                    continue
            time.sleep(0.3)  # Rate limit safe
        except Exception as e:
            print(f"⚠️ Error on {tag_name}: {e}")

    tags = sorted(all_tags)
    print(f"\n✅ Total collected tags: {len(tags)}\n")
    for tag in tags:
        print(tag)
        output_path = os.path.join(os.path.dirname(__file__), "..", "data", "lastfm_tags_list.pkl")
        joblib.dump(tags, output_path)
    print(f"\n📦 Tags saved to {output_path}")

def save_spotify_tags(file):
    with open(file, "r") as f:
        tags = f.read().splitlines()
    tags = [tag.strip().lower() for tag in tags if tag.strip()]
    tags = sorted(set(tags))
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "genre_tags_list.pkl")
    joblib.dump(tags, output_path)
    print(tags)
    return tags

def compare_genres_lastfmtags(spotify_tags):
    # take each tag from spotify_tags and check if it exists in lastfm using the api
    # use network and pylast to check if the tag exists
    for tag in spotify_tags:
        try:
            network.get_tag(tag)
        except pylast.WSError as e:
            if e.code == 404:
                print(f"❌ Tag '{tag}' not found in Last.fm")
                spotify_tags.remove(tag)
            else:
                print(f"⚠️ Error checking tag '{tag}': {e}")
    print(f"\n✅ Common tags found: {len(spotify_tags)}")
    print(spotify_tags)
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "genre_tags_list.pkl")
    joblib.dump(spotify_tags, output_path)
    print(f"\n📦 Common tags saved to {output_path}")
    return spotify_tags

def append_lastfm_tags_to_spotify_tags(spotify_tags, lastfm_tags):
    # Append Last.fm tags to Spotify tags
    combined_tags = set(spotify_tags + lastfm_tags)
    combined_tags = sorted(combined_tags)
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "combined_tags_list.pkl")
    joblib.dump(combined_tags, output_path)
    print(f"\n📦 Combined tags saved to {output_path}")
    return combined_tags

def main():
    # Collect and save Last.fm tags
    # collect_expanded_tags(tag_limit=70, track_limit=25)
    # genres_file = os.path.join(os.path.dirname(__file__), "..", "data", "genres.txt")
    # spotify_tags = save_spotify_tags(genres_file)

    lastfm_tags = joblib.load(os.path.join(os.path.dirname(__file__), "..", "data", "lastfm_tags_list.pkl"))
    spotify_tags = joblib.load(os.path.join(os.path.dirname(__file__), "..", "data", "genre_tags_list.pkl"))
    common_tags = compare_genres_lastfmtags(spotify_tags)
    append_lastfm_tags_to_spotify_tags(common_tags, lastfm_tags)


if __name__ == "__main__":
    main()