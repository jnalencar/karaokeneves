document.addEventListener('DOMContentLoaded', function () {
    const socket = io();

    const addSongForm = document.getElementById('add-song-form');
    if (addSongForm) {
        addSongForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const song = document.getElementById('song-input').value;
            socket.emit('add_song', { song: song });
        });
    }

    const skipButton = document.getElementById('skip-button');
    if (skipButton) {
        const skipHandler = function () {
            fetch('http://localhost:5002/skip', { method: 'POST' })
                .then(response => response.text())
                .then(data => {
                    console.log(data);
                    socket.emit('get_queue');
                    socket.emit('get_current_song');
                });
        };
        skipButton.addEventListener('click', skipHandler);
        skipButton.addEventListener('touchstart', skipHandler);
    }

    socket.on('song_added', function (data) {
        const messageElement = document.getElementById('message');
        messageElement.innerText = data.message;
        messageElement.style.display = 'block';
        setTimeout(() => {
            messageElement.style.display = 'none';
        }, 2000);
        socket.emit('get_queue');
        socket.emit('get_current_song');
    });

    socket.on('queue', function (data) {
        const queueList = document.getElementById('queue-list');
        queueList.innerHTML = '';
        data.queue.forEach(function (song, index) {
            const li = document.createElement('li');
            li.innerText = song;
            const deleteButton = document.createElement('button');
            deleteButton.innerText = 'X';
            deleteButton.style.marginLeft = '10px';
            deleteButton.style.cursor = 'pointer';
            deleteButton.style.backgroundColor = 'red';
            deleteButton.style.color = 'white';
            deleteButton.style.height = '100%';
            deleteButton.style.width = '5vh';
            deleteButton.addEventListener('click', function () {
                socket.emit('delete_song', { pos: index });
            });
            li.appendChild(deleteButton);
            queueList.appendChild(li);
        });
    });

    socket.on('current_song', function (data) {
        const currentSongName = document.getElementById('current-song-name');
        const skipButton = document.getElementById('skip-button');
        currentSongName.innerText = data.current_song || 'Nenhuma música tocando';
        if (data.current_song && data.current_song !== 'Nenhuma música tocando') {
            currentSongName.innerText = data.current_song;
            skipButton.style.display = 'block';
        } else {
            currentSongName.innerText = 'Nenhuma música tocando';
            skipButton.style.display = 'none';
        }
    });

    socket.on('song_deleted', function (data) {
        const messageElement = document.getElementById('message');
        messageElement.innerText = data.message;
        messageElement.style.display = 'block';
        setTimeout(() => {
            messageElement.style.display = 'none';
        }, 2000);
        socket.emit('get_queue');
        socket.emit('get_current_song');
    });

    socket.emit('get_queue');
    socket.emit('get_current_song');
});