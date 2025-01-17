import time
import requests
import webbrowser
from flask import Flask, render_template
from youtube_search import YoutubeSearch
import yt_dlp as youtube_dl
import os

YOUTUBE_API_KEY = 'AIzaSyBYLp4uoljYAlGRGj_E_OJ8mNw_gHOr2yQ'

app = Flask(__name__)

@app.route('/play/<video_id>')
def play_video(video_id):
    return render_template('video.html', video_id=video_id)

def is_video_embeddable(video_id):
    url = f'https://www.googleapis.com/youtube/v3/videos?part=status&id={video_id}&key={YOUTUBE_API_KEY}'
    response = requests.get(url)
    data = response.json()
    print(data)
    if 'items' in data and len(data['items']) > 0:
        return data['items'][0]['status']['embeddable']
    return False

def search_and_play_song():
    while True:
        response = requests.get('http://localhost:5001/next')
        song = response.json().get('song')
        print(song)
        if song:
            search_query = f"{song} karaoke"
            print(search_query)
            
            # Search for the video on YouTube
            results = YoutubeSearch(search_query, max_results=5).to_dict()
            video_url = None
            for result in results:
                video_id = result.get('id')
                if is_video_embeddable(video_id):
                    video_url = f"http://localhost:5002/play/{video_id}"
                    video = result
                    break
            if not video_url:
                video_id = results[0]['id']
                video_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1&fs=1"
            print(video.get('title'))
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

if __name__ == '__main__':
    from threading import Thread
    Thread(target=search_and_play_song).start()
    app.run(host='0.0.0.0', port=5002)