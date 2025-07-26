import os
import qrcode
from flask import Flask, render_template
#from selenium import webdriver
#from selenium.webdriver.chrome.service import Service as ChromeService
#from webdriver_manager.chrome import ChromeDriverManager
from threading import Thread
import time
import socket
import requests
#import tempfile
from playwright.sync_api import sync_playwright

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def entry_screen():
    return render_template('entry.html')

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def generate_qr_code():
    local_ip = get_local_ip()
    host_ip = f'http://{local_ip}:5000'
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(host_ip)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    img.save(os.path.join(app.static_folder, 'qrcode.png'))

def start_flask_app():
    if not os.path.exists(app.static_folder):
        os.makedirs(app.static_folder)
    generate_qr_code()
    app.run(host='0.0.0.0', port=5003)

def wait_for_flask():
    while True:
        try:
            response = requests.get('http://localhost:5003')
            if response.status_code == 200:
                break
        except requests.ConnectionError:
            time.sleep(1)

#def start_selenium():
#    options = webdriver.ChromeOptions()
#    options.add_argument('--start-fullscreen')
#    options.add_argument('--disable-dev-shm-usage')
#    options.binary_location = "/usr/bin/chromium"
#    user_data_dir = tempfile.mkdtemp()
#    options.add_argument(f'--user-data-dir={user_data_dir}')
#    wait_for_flask()
#    driver = webdriver.Chrome(service=ChromeService('/usr/bin/chromedriver'), options=options)
#     # Wait for the Flask server to start
#    driver.get('http://localhost:5003')

def start_playwright():
    wait_for_flask()
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--start-fullscreen",
                "--kiosk",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-features=TranslateUI",
                "--disable-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-extensions",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--disable-default-apps",
                "--disable-popup-blocking",
                "--disable-notifications",
                "--disable-translate",
                "--disable-sync",
                "--disable-background-networking",
                "--disable-breakpad",
                "--disable-client-side-phishing-detection",
                "--disable-component-update",
                "--disable-domain-reliability",
                "--disable-hang-monitor",
                "--disable-prompt-on-repost",
                "--disable-web-resources",
                "--disable-zero-browsers-open-for-tests",
                "--foreground-tab"  # Tenta abrir em primeiro plano
            ]
        )
        page = browser.new_page()
        page.goto("http://localhost:5003")
        page.wait_for_timeout(60000)

if __name__ == '__main__':
    flask_thread = Thread(target=start_flask_app)
    flask_thread.start()

    #selenium_thread = Thread(target=start_selenium)
    #selenium_thread.start()

    playwright_thread = Thread(target=start_playwright)
    playwright_thread.start()

    flask_thread.join()
    #selenium_thread.join()
    playwright_thread.join()