class DB:
    def __init__(self):
        self.queue = []

    def add_song(self, song):
        self.queue.append(song)

    def get_next_song(self):
        if self.queue:
            return self.queue[0]
        return None

    def pop_next_song(self):
        if self.queue:
            return self.queue.pop(0)
        return None
    
    def get_all_songs(self):
        return self.queue