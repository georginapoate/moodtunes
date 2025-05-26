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

def collect_expanded_tags(tag_limit=50, track_limit=10):
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

    return sorted(all_tags)

if __name__ == "__main__":
    tags = collect_expanded_tags(tag_limit=50, track_limit=15)
    print(f"\n✅ Total collected tags: {len(tags)}\n")
    for tag in tags:
        print(tag)
        output_path = os.path.join(os.path.dirname(__file__), "..", "data", "tags_list.pkl")
        joblib.dump(tags, output_path)
    print(f"\n📦 Tags saved to {output_path}")