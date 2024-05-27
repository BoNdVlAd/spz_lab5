class Directory:
    def __init__(self, parent=None):
        self.entries = {}
        self.parent = parent

    def has_entry(self, name):
        return name in self.entries

    def get_entry(self, name):
        return self.entries.get(name)

    def add_entry(self, name, fd_index):
        self.entries[name] = fd_index

    def remove_entry(self, name):
        if name in self.entries:
            del self.entries[name]