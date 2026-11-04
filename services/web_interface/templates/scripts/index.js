document.addEventListener('DOMContentLoaded', function () {
    const socket = io();
    const form = document.getElementById('add-song-form');
    const songInput = document.getElementById('song-input');
    const skipButton = document.getElementById('skip-button');
    const messageElement = document.getElementById('message');
    let messageTimeout;
    let pendingSong;

    function showMessage(message, isError) {
        messageElement.innerText = message;
        messageElement.classList.toggle('error', Boolean(isError));
        messageElement.style.display = 'block';
        clearTimeout(messageTimeout);
        messageTimeout = setTimeout(function () {
            messageElement.style.display = 'none';
        }, 2500);
    }

    function refreshState() {
        socket.emit('get_queue');
        socket.emit('get_current_song');
    }

    form.addEventListener('submit', function (event) {
        event.preventDefault();
        pendingSong = songInput.value.trim();
        if (!pendingSong) {
            showMessage('Informe o nome da música.', true);
            return;
        }
        form.querySelector('button[type="submit"]').disabled = true;
        socket.emit('add_song', { song: pendingSong });
    });

    skipButton.addEventListener('click', function () {
        skipButton.disabled = true;
        socket.emit('skip');
    });

    socket.on('song_added', function (data) {
        if (songInput.value.trim() === pendingSong) {
            songInput.value = '';
        }
        pendingSong = null;
        form.querySelector('button[type="submit"]').disabled = false;
        showMessage(data.message, false);
        refreshState();
    });

    socket.on('song_error', function (data) {
        pendingSong = null;
        form.querySelector('button[type="submit"]').disabled = false;
        showMessage(data.message, true);
    });

    socket.on('service_error', function (data) {
        pendingSong = null;
        form.querySelector('button[type="submit"]').disabled = false;
        skipButton.disabled = false;
        showMessage(data.message, true);
    });

    socket.on('queue', function (data) {
        const queueList = document.getElementById('queue-list');
        queueList.replaceChildren();
        if (!Array.isArray(data.queue)) {
            return;
        }
        data.queue.forEach(function (song, index) {
            const item = document.createElement('li');
            const label = document.createElement('span');
            label.innerText = song;
            const deleteButton = document.createElement('button');
            deleteButton.type = 'button';
            deleteButton.innerText = 'Remover';
            deleteButton.setAttribute('aria-label', `Remover ${song} da fila`);
            deleteButton.addEventListener('click', function () {
                socket.emit('delete_song', { pos: index });
            });
            item.append(label, deleteButton);
            queueList.appendChild(item);
        });
    });

    socket.on('current_song', function (data) {
        const currentSong = document.getElementById('current-song-name');
        const hasCurrentSong = data.current_song
            && data.current_song !== 'Nenhuma música tocando';
        currentSong.innerText = hasCurrentSong
            ? data.current_song
            : 'Nenhuma música tocando';
        skipButton.style.display = hasCurrentSong ? 'block' : 'none';
        skipButton.disabled = false;
    });

    socket.on('song_deleted', function (data) {
        showMessage(data.message, false);
        refreshState();
    });

    socket.on('song_skipped', function (data) {
        showMessage(data.message, false);
        refreshState();
    });

    socket.on('connect_error', function () {
        form.querySelector('button[type="submit"]').disabled = false;
        skipButton.disabled = false;
        showMessage('Conexão perdida com o karaokê.', true);
    });

    socket.on('connect', refreshState);
    socket.on('disconnect', function () {
        form.querySelector('button[type="submit"]').disabled = false;
        skipButton.disabled = false;
        showMessage('Conexão perdida com o karaokê.', true);
    });

    refreshState();
    setInterval(refreshState, 5000);
});
