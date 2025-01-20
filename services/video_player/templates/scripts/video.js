// Load the IFrame Player API code asynchronously.
var tag = document.createElement('script');
tag.src = "https://www.youtube.com/iframe_api";
var firstScriptTag = document.getElementsByTagName('script')[0];
firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

// Create an <iframe> (and YouTube player) after the API code downloads.
var player;
function onYouTubeIframeAPIReady() {
    player = new YT.Player('player', {
        height: '100%',
        width: '100%',
        videoId: '{{ video_id }}',
        playerVars: {
            'autoplay': 1,
            'controls': 0,
            'fs': 1,
            'rel': 0,
            'mute': 1,
            'showinfo': 0,
            'modestbranding': 1
        },
        events: {
            'onReady': onPlayerReady,
            'onStateChange': onPlayerStateChange
        }
    });
}

// The API will call this function when the video player is ready.
function onPlayerReady(event) {
    event.target.playVideo();
    // Simulate a click on the unmute overlay to unmute the video
    setTimeout(() => {
        const unmuteOverlay = document.getElementById('unmute-overlay');
        unmuteOverlay.click();
    }, 5000); // Wait for 1 second before simulating the click
}

// The API calls this function when the player's state changes.
function onPlayerStateChange(event) {
    if (event.data == YT.PlayerState.ENDED) {
        window.close();
    }
}

// Request fullscreen mode
document.addEventListener('DOMContentLoaded', () => {
    const iframe = document.getElementById('player');
    const requestFullscreen = iframe.requestFullscreen || iframe.mozRequestFullScreen || iframe.webkitRequestFullscreen || iframe.msRequestFullscreen;
    if (requestFullscreen) {
        requestFullscreen.call(iframe);
    }

    // Unmute the video on user interaction
    const unmuteOverlay = document.getElementById('unmute-overlay');
    unmuteOverlay.addEventListener('click', () => {
        player.unMute();
        player.setVolume(100); // Set volume to max
        unmuteOverlay.style.display = 'none'; // Hide the overlay
    });
});