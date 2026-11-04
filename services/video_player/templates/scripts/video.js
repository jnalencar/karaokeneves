var player;
var overlay;
var nextSongBadge;
var nextSongTitle;
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
    nextSongBadge = document.getElementById('next-song');
    nextSongTitle = document.getElementById('next-song-title');
    overlay.addEventListener('click', function () {
        if (!player) {
            return;
        }
        player.unMute();
        player.setVolume(100);
        overlay.hidden = true;
    });

    updateNextSong();
    window.setInterval(updateNextSong, 4000);
});

function updateNextSong() {
    var currentSong = document.body.dataset.currentSong;
    if (!currentSong) {
        return;
    }

    fetch('/next-song?current_song=' + encodeURIComponent(currentSong), {
        cache: 'no-store'
    })
        .then(function (response) {
            if (!response.ok) {
                throw new Error('HTTP ' + response.status);
            }
            return response.json();
        })
        .then(function (data) {
            if (typeof data.next_song === 'string' && data.next_song) {
                nextSongTitle.textContent = data.next_song;
                nextSongBadge.hidden = false;
            } else {
                nextSongBadge.hidden = true;
            }
        })
        .catch(function (error) {
            console.error('Falha ao atualizar a próxima música:', error);
            nextSongTitle.textContent =
                'Não foi possível verificar a próxima música';
            nextSongBadge.hidden = false;
        });
}
