import time
import requests
import webbrowser
from youtube_search import YoutubeSearch
import yt_dlp as youtube_dl

while True:
    response = requests.get('http://localhost:5001/next')
    song = response.json().get('song')
    print(song)
    if song:
        search_query = f"{song} karaoke"
        print(search_query)
        
        # Search for the video on YouTube
        results = YoutubeSearch(search_query, max_results=1).to_dict()
        if results:
            video_id = results[0]['id']
            video_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1&fs=1"
            print(results[0]['title'])
            print(video_url)
            
            # Get video duration using yt-dlp
            ydl_opts = {}
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                video_duration = info_dict.get('duration', 300)  # Default to 5 minutes if duration is not available
            print(f"Video duration: {video_duration} seconds")
            
            # Open the video in a web browser
            webbrowser.open(video_url)
            
            # Remove the song from the queue after playing
            requests.post('http://localhost:5001/pop')
            
            # Sleep for the duration of the video
            time.sleep(video_duration)
    
    time.sleep(10)