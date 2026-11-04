var player;
var overlay;
window.karaokePlayerReady = false;

var tag = document.createElement('script');
tag.src = 'https://www.youtube.com/iframe_api';
document.head.appendChild(tag);

function finishPlayback() {
    fetch('/finished', { method: 'POST', keepalive: true });
}

function onYouTubeIframeAPIReady() {
    player = new YT.Player('player', {
        height: '100%',
        width: '100%',
        videoId: document.body.dataset.videoId,
        playerVars: {
            autoplay: 1,
            controls: 0,
            fs: 1,
            rel: 0,
            mute: 1,
            modestbranding: 1
        },
        events: {
            onReady: function (event) {
                event.target.mute();
                event.target.playVideo();
                window.karaokePlayerReady = true;
            },
            onStateChange: function (event) {
                if (event.data === YT.PlayerState.ENDED) {
                    finishPlayback();
                }
            },
            onError: finishPlayback
        }
    });
}

document.addEventListener('DOMContentLoaded', function () {
    overlay = document.getElementById('unmute-overlay');
    overlay.addEventListener('click', function () {
        if (!player) {
            return;
        }
        player.unMute();
        player.setVolume(100);
        overlay.hidden = true;
    });
});
