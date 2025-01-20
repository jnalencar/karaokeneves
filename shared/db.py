class DB:
    def __init__(self):
        self.queue = []
        self.current_song = None

    def add_song(self, song):
        self.queue.append(song)

    def get_next_song(self):
        if self.queue:
            return self.queue[0]
        return None

    def pop_next_song(self):
        if self.queue:
            self.current_song = self.queue[0]
            return self.queue.pop(0)
        return None
    
    def get_all_songs(self):
        return self.queue
    
    def get_current_song(self):
        return self.current_song