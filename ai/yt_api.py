from ytmusicapi import YTMusic

ytmusic = YTMusic()  # You can use anonymous requests, or auth if desired

search_results = ytmusic.search("faded", filter="songs")

for song in search_results[:10]:  # get top 10 results
    print(f"{song['title']} by {song['artists'][0]['name']}")
