const socket = io();

document.getElementById('add-song-form').addEventListener('submit', function (event) {
    event.preventDefault();
    const song = document.getElementById('song-input').value;
    socket.emit('add_song', { song: song });
});

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
    currentSongName.innerText = data.current_song || 'Nenhuma música tocando';
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