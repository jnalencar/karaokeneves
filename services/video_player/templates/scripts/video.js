var player;
var overlay;
var nextSongBadge;
var nextSongTitle;
var nextSongRequester;
var nextSongRequesterName;
var scoreOverlay;
var scoreRequester;
var scoreValue;
var scoreRankingList;
var scorePresentationStarted = false;
window.karaokePlayerReady = false;

var tag = document.createElement('script');
tag.src = 'https://www.youtube.com/iframe_api';
document.head.appendChild(tag);

function finishPlayback() {
    fetch('/finished', { method: 'POST', keepalive: true });
}

function showSongScore() {
    if (scorePresentationStarted) {
        return;
    }
    scorePresentationStarted = true;
    scoreOverlay.hidden = false;
    scoreOverlay.setAttribute('aria-live', 'off');
    document.querySelector('.score-kicker').textContent = 'SORTEANDO A NOTA...';
    scoreRequester.textContent = 'Sorteando...';
    scoreValue.textContent = '...';

    fetch('/score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            playback_id: document.body.dataset.playbackId
        })
    })
        .then(function (response) {
            if (!response.ok) {
                throw new Error('HTTP ' + response.status);
            }
            return response.json();
        })
        .then(function (result) {
            scoreRequester.textContent = result.name;
            renderScoreRanking(result.ranking_before, '');
            return animateScore(result.score).then(function () {
                document.querySelector('.score-kicker').textContent =
                    'A SUA NOTA FOI:';
                scoreOverlay.setAttribute('aria-live', 'assertive');
                renderScoreRanking(result.ranking, result.name);
            });
        })
        .catch(function (error) {
            console.error('Falha ao dar a nota:', error);
            scoreOverlay.setAttribute('aria-live', 'assertive');
            scoreRequester.textContent = 'Não foi possível dar a nota';
            scoreValue.textContent = '—';
        })
        .finally(function () {
            window.setTimeout(finishPlayback, 5500);
        });
}

function animateScore(finalScore) {
    scoreValue.classList.add('score-value--rolling');
    return new Promise(function (resolve) {
        var animationDuration = 2400;
        var animationStarted = Date.now();
        var counter = window.setInterval(function () {
            var elapsed = Date.now() - animationStarted;
            if (elapsed >= animationDuration) {
                window.clearInterval(counter);
                scoreValue.textContent = finalScore;
                scoreValue.classList.remove('score-value--rolling');
                resolve();
                return;
            }

            scoreValue.textContent = Math.floor(Math.random() * 101);
        }, 75);
    });
}

function renderScoreRanking(ranking, highlightedName) {
    scoreRankingList.replaceChildren();
    ranking.forEach(function (entry) {
        var item = document.createElement('li');
        item.textContent = entry.name + ' — ' + entry.score + ' pontos';
        if (
            highlightedName &&
            entry.name.toLocaleLowerCase('pt-BR') ===
                highlightedName.toLocaleLowerCase('pt-BR')
        ) {
            item.classList.add('score-ranking-entry--highlight');
        }
        scoreRankingList.appendChild(item);
    });
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
                    showSongScore();
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
    nextSongRequester = document.getElementById('next-song-requester');
    nextSongRequesterName = document.getElementById('next-song-requester-name');
    scoreOverlay = document.getElementById('score-overlay');
    scoreRequester = document.getElementById('score-requester');
    scoreValue = document.getElementById('score-value');
    scoreRankingList = document.getElementById('score-ranking-list');
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
                var separator = data.next_song.lastIndexOf(' - ');
                if (separator > 0) {
                    nextSongTitle.textContent = data.next_song.slice(0, separator);
                    nextSongRequesterName.textContent =
                        data.next_song.slice(separator + 3);
                    nextSongRequester.hidden = !nextSongRequesterName.textContent;
                } else {
                    nextSongTitle.textContent = data.next_song;
                    nextSongRequesterName.textContent = '';
                    nextSongRequester.hidden = true;
                }
                nextSongBadge.hidden = false;
            } else {
                nextSongBadge.hidden = true;
                nextSongRequester.hidden = true;
            }
        })
        .catch(function (error) {
            console.error('Falha ao atualizar a próxima música:', error);
            nextSongTitle.textContent =
                'Não foi possível verificar a próxima música';
            nextSongRequester.hidden = true;
            nextSongBadge.hidden = false;
        });
}
