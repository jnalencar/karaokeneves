document.addEventListener('DOMContentLoaded', function () {
    const connectionStatus = document.getElementById('connection-status');
    const connectionLabel = document.getElementById('connection-label');
    const form = document.getElementById('add-song-form');
    const songInput = document.getElementById('song-input');
    const submitButton = form.querySelector('button[type="submit"]');
    const skipButton = document.getElementById('skip-button');
    const skipDialog = document.getElementById('skip-dialog');
    const confirmSkipButton = document.getElementById('confirm-skip');
    const messageElement = document.getElementById('message');
    const queueList = document.getElementById('queue-list');
    const queueCount = document.getElementById('queue-count');
    const queueFilter = document.getElementById('queue-filter');
    const queueFilterField = queueFilter.closest('.search-field');
    const queueEmpty = document.getElementById('queue-empty');
    const queueFilterEmpty = document.getElementById('queue-filter-empty');
    let messageTimeout;
    let pendingSong;
    let songs = [];
    let skipPending = false;

    function setConnectionState(state, label) {
        connectionStatus.dataset.state = state;
        connectionLabel.textContent = label;
    }

    function showMessage(message, isError) {
        messageElement.textContent = message;
        messageElement.classList.toggle('is-error', Boolean(isError));
        messageElement.classList.add('is-visible');
        clearTimeout(messageTimeout);
        messageTimeout = setTimeout(function () {
            messageElement.classList.remove('is-visible');
        }, 2800);
    }

    function refreshState() {
        socket.emit('get_queue');
        socket.emit('get_current_song');
    }

    function createQueueAction(label, icon, className, disabled, onClick) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `queue-action ${className || ''}`.trim();
        button.setAttribute('aria-label', label);
        button.title = label;
        button.textContent = icon;
        button.disabled = disabled;
        button.addEventListener('click', onClick);
        return button;
    }

    function renderQueue() {
        const query = queueFilter.value.trim().toLocaleLowerCase('pt-BR');
        const visibleSongs = songs
            .map(function (song, index) {
                return { song: song, index: index };
            })
            .filter(function (item) {
                return item.song.toLocaleLowerCase('pt-BR').includes(query);
            });

        queueList.replaceChildren();
        visibleSongs.forEach(function (item) {
            const row = document.createElement('li');
            row.className = 'queue-item';

            const title = document.createElement('span');
            title.className = 'queue-song';
            title.textContent = item.song;

            const actions = document.createElement('div');
            actions.className = 'queue-actions';
            actions.append(
                createQueueAction(
                    `Mover ${item.song} para cima`,
                    '↑',
                    '',
                    item.index === 0,
                    function () {
                        socket.emit('move_song', {
                            source: item.index,
                            target: item.index - 1,
                        });
                    }
                ),
                createQueueAction(
                    `Mover ${item.song} para baixo`,
                    '↓',
                    '',
                    item.index === songs.length - 1,
                    function () {
                        socket.emit('move_song', {
                            source: item.index,
                            target: item.index + 1,
                        });
                    }
                ),
                createQueueAction(
                    `Remover ${item.song} da fila`,
                    '×',
                    'remove',
                    false,
                    function () {
                        socket.emit('delete_song', { pos: item.index });
                    }
                )
            );
            row.append(title, actions);
            queueList.appendChild(row);
        });

        queueCount.textContent = songs.length === 1
            ? '1 música'
            : `${songs.length} músicas`;
        queueEmpty.hidden = songs.length > 0;
        queueFilterEmpty.hidden = songs.length === 0 || visibleSongs.length > 0;
        queueFilterField.hidden = songs.length === 0 && !query;
    }

    function sendSkipRequest() {
        skipPending = true;
        skipButton.disabled = true;
        confirmSkipButton.disabled = true;
        socket.emit('skip');
    }

    if (typeof io !== 'function') {
        setConnectionState('offline', 'Sem conexão');
        showMessage('Não foi possível carregar os controles em tempo real.', true);
        return;
    }

    const socket = io();

    form.addEventListener('submit', function (event) {
        event.preventDefault();
        const song = songInput.value.trim();
        if (!song) {
            showMessage('Digite o nome da música ou do artista.', true);
            songInput.focus();
            return;
        }

        pendingSong = song;
        submitButton.disabled = true;
        socket.emit('add_song', { song: song });
    });

    skipButton.addEventListener('click', function () {
        if (typeof skipDialog.showModal === 'function') {
            skipDialog.showModal();
        } else if (window.confirm(
            'Pular a música atual e iniciar a próxima da fila?'
        )) {
            sendSkipRequest();
        }
    });

    document.getElementById('cancel-skip').addEventListener('click', function () {
        skipDialog.close();
    });

    confirmSkipButton.addEventListener('click', function () {
        skipDialog.close();
        sendSkipRequest();
    });

    queueFilter.addEventListener('input', renderQueue);

    socket.on('connect', function () {
        setConnectionState('connected', 'Conectado');
        refreshState();
    });

    socket.on('disconnect', function () {
        setConnectionState('offline', 'Reconectando');
        submitButton.disabled = false;
        skipButton.disabled = false;
        confirmSkipButton.disabled = false;
        skipPending = false;
        showMessage('Conexão perdida. Tentando reconectar...', true);
    });

    socket.on('connect_error', function () {
        setConnectionState('offline', 'Sem conexão');
    });

    socket.on('song_added', function (data) {
        if (songInput.value.trim() === pendingSong) {
            songInput.value = '';
        }
        pendingSong = null;
        setConnectionState('connected', 'Conectado');
        submitButton.disabled = false;
        showMessage(data.message, false);
        refreshState();
    });

    socket.on('song_error', function (data) {
        pendingSong = null;
        submitButton.disabled = false;
        showMessage(data.message, true);
    });

    socket.on('service_error', function (data) {
        pendingSong = null;
        submitButton.disabled = false;
        skipButton.disabled = false;
        confirmSkipButton.disabled = false;
        skipPending = false;
        const serviceWasAvailable = connectionStatus.dataset.state !== 'offline';
        setConnectionState('offline', 'Serviço indisponível');
        if (skipDialog.open) {
            skipDialog.close();
        }
        if (serviceWasAvailable) {
            showMessage(data.message, true);
        }
    });

    socket.on('queue', function (data) {
        setConnectionState('connected', 'Conectado');
        songs = Array.isArray(data.queue)
            ? data.queue.filter(function (song) {
                return typeof song === 'string';
            })
            : [];
        renderQueue();
    });

    socket.on('current_song', function (data) {
        setConnectionState('connected', 'Conectado');
        const currentSong = document.getElementById('current-song-name');
        const name = data.current_song;
        const hasCurrentSong = Boolean(
            name && name !== 'Nenhuma música tocando'
        );
        currentSong.textContent = hasCurrentSong
            ? name
            : 'Nenhuma música tocando';
        skipButton.disabled = !hasCurrentSong || skipPending;
        skipButton.hidden = !hasCurrentSong;
    });

    socket.on('song_deleted', function (data) {
        showMessage(data.message, false);
        refreshState();
    });

    socket.on('song_moved', function (data) {
        showMessage(data.message, false);
        refreshState();
    });

    socket.on('song_skipped', function (data) {
        skipPending = false;
        confirmSkipButton.disabled = false;
        showMessage(data.message, false);
        refreshState();
    });

    refreshState();
    setInterval(refreshState, 5000);
});
