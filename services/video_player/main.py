import time
import requests
import webbrowser
from flask import Flask, render_template
from youtube_search import YoutubeSearch
import yt_dlp as youtube_dl
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pyautogui
from dotenv import load_dotenv
from flask_cors import CORS
from threading import Event, Thread

load_dotenv()

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

app = Flask(__name__)
CORS(app)

driver = None
skip_event = Event()


@app.route('/play/<video_id>')
def play_video(video_id):
    return render_template('video.html', video_id=video_id)

@app.route('/skip', methods=['POST'])
def skip():
    print('Skip requested')
    global driver
    if driver is not None:
        driver.quit()
    skip_event.set()
    return 'Skipped', 200

def is_video_embeddable(video_id):
    url = f'https://www.googleapis.com/youtube/v3/videos?part=status&id={video_id}&key={YOUTUBE_API_KEY}'
    response = requests.get(url)
    data = response.json()
    print(data)
    if 'items' in data and len(data['items']) > 0:
        return data['items'][0]['status']['embeddable']
    return False

def search_and_play_song():
    global driver
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
                video_id = results[0].get('id')
                video_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1&fs=1"
            print(video.get('title'))
            print(video_url)

            # Get the duration of the video
            ydl_opts = {}
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                video_duration = info_dict.get('duration', 300)  # Default to 5 minutes if duration is not available
            print(f"Video duration: {video_duration} seconds")
            
            #driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
            options = webdriver.ChromeOptions()
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--start-fullscreen')

            driver = webdriver.Chrome(service=ChromeService('/usr/lib/chromium-browser/chromedriver'), options = options)
            driver.get(video_url)
            try:
                unmute_overlay = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, 'unmute-overlay'))
                )
                location = unmute_overlay.location
                size = unmute_overlay.size
                screen_width, screen_height = pyautogui.size()
                center_x = screen_width / 2
                center_y = screen_height / 2
                pyautogui.click(center_x, center_y)
                pyautogui.move(-center_x+1, 0)
            except Exception as e:
                print(f"Error clicking unmute overlay: {e}")
            
            # Remove the song from the queue after playing
            requests.post('http://localhost:5001/pop')
            
            # Sleep for the duration of the video
            skip_event.wait(video_duration)
            skip_event.clear()

            # Close the browser
            driver.quit()

        time.sleep(10)



if __name__ == '__main__':
    Thread(target=search_and_play_song).start()
    app.run(host='0.0.0.0', port=5002)