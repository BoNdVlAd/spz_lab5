from FileDescriptor import *


MAX_OPEN_FILES = 100
MAX_FILENAME_LENGTH = 255
BLOCK_SIZE = 512

class FileSystem:
    def __init__(self, device, num_descriptors):
        self.device = device
        self.root_dir = {}
        self.file_descriptors = [None] * num_descriptors
        self.open_files = [None] * MAX_OPEN_FILES
        self.seek_positions = [0] * MAX_OPEN_FILES
        self.current_dir = '/'

    def mkfs(self, num_descriptors):
        self.file_descriptors = [None] * num_descriptors
        self.root_dir = {}
        self._create_root_directory()

    def _create_root_directory(self):
        root_fd = self._allocate_file_descriptor('directory')
        self.file_descriptors[root_fd].block_map.append(self.device.allocate_block())
        self.root_dir['/'] = root_fd

    def _allocate_file_descriptor(self, file_type):
        for i in range(len(self.file_descriptors)):
            if self.file_descriptors[i] is None:
                self.file_descriptors[i] = FileDescriptor(file_type)
                return i
        raise RuntimeError("No free file descriptors available")

    def _resolve_path(self, pathname):
        if pathname.startswith('/'):
            return pathname
        return self.current_dir.rstrip('/') + '/' + pathname

    def _resolve_symlink(self, fd_index):
        fd = self.file_descriptors[fd_index]
        if fd.file_type == 'symlink':
            block_num = fd.block_map[0]
            target_path = self.device.read_block(block_num).decode().strip('\x00')
            return self._resolve_path(target_path)
        return None

    def stat(self, pathname):
        pathname = self._resolve_path(pathname)
        fd_index = self.root_dir.get(pathname)
        if fd_index is None:
            raise FileNotFoundError("File not found")
        fd = self.file_descriptors[fd_index]
        return fd

    def ls(self, pathname=None):
        pathname = self._resolve_path(pathname) if pathname else self.current_dir
        return {name: fd for name, fd in self.root_dir.items() if name.startswith(pathname)}

    def create(self, pathname):
        pathname = self._resolve_path(pathname)
        if len(pathname) > MAX_FILENAME_LENGTH:
            raise ValueError("Filename too long")
        if pathname in self.root_dir:
            raise ValueError("File already exists")

        fd_index = self._allocate_file_descriptor('regular')
        self.root_dir[pathname] = fd_index
        return fd_index

    def mkdir(self, pathname):
        pathname = self._resolve_path(pathname)
        if pathname in self.root_dir:
            raise ValueError("Directory already exists")

        fd_index = self._allocate_file_descriptor('directory')
        self.file_descriptors[fd_index].block_map.append(self.device.allocate_block())
        self.root_dir[pathname] = fd_index

    def rmdir(self, pathname):
        pathname = self._resolve_path(pathname)
        fd_index = self.root_dir.get(pathname)
        if fd_index is None:
            return print("Такої директорії не існує")
        fd = self.file_descriptors[fd_index]
        if fd.file_type != 'directory':
            raise ValueError("Not a directory")
        if any(name.startswith(pathname + '/') for name in self.root_dir.keys()):
            self.rm_rf(pathname)
            return


        block_num = fd.block_map.pop()
        self.device.free_block(block_num)
        self.file_descriptors[fd_index] = None
        del self.root_dir[pathname]

    def cd(self, pathname):
        pathname = self._resolve_path(pathname)
        if pathname not in self.root_dir:
            raise FileNotFoundError("Directory not found")
        fd_index = self.root_dir[pathname]
        if self.file_descriptors[fd_index].file_type != 'directory':
            raise ValueError("Not a directory")
        self.current_dir = pathname

    def symlink(self, target, pathname):
        pathname = self._resolve_path(pathname)
        if pathname in self.root_dir:
            raise ValueError("File already exists")
        if len(target) > BLOCK_SIZE:
            raise ValueError("Symlink target too long")

        fd_index = self._allocate_file_descriptor('symlink')
        self.file_descriptors[fd_index].block_map.append(self.device.allocate_block())
        self.device.write_block(self.file_descriptors[fd_index].block_map[0], target.encode())
        self.root_dir[pathname] = fd_index

    def open(self, pathname):
        pathname = self._resolve_path(pathname)
        fd_index = self.root_dir.get(pathname)
        if fd_index is None:
            raise FileNotFoundError("File not found")

        symlink_path = self._resolve_symlink(fd_index)
        if symlink_path:
            return self.open(symlink_path)

        for i in range(MAX_OPEN_FILES):
            if self.open_files[i] is None:
                self.open_files[i] = fd_index
                self.seek_positions[i] = 0
                return i
        raise RuntimeError("No free file descriptors available")

    def close(self, fd):
        if self.open_files[fd] is None:
            raise ValueError("File descriptor not open")
        self.open_files[fd] = None
        self.seek_positions[fd] = 0

    def seek(self, fd, offset):
        if self.open_files[fd] is None:
            raise ValueError("File descriptor not open")
        self.seek_positions[fd] = offset

    def read(self, fd, size):
        if self.open_files[fd] is None:
            raise ValueError("File descriptor not open")
        fd_index = self.open_files[fd]
        position = self.seek_positions[fd]
        file_descriptor = self.file_descriptors[fd_index]

        data = bytearray()
        remaining = size
        while remaining > 0 and position < file_descriptor.size:
            block_index = position // BLOCK_SIZE
            block_offset = position % BLOCK_SIZE
            block_num = file_descriptor.block_map[block_index]
            block_data = self.device.read_block(block_num)

            chunk = min(BLOCK_SIZE - block_offset, remaining)
            data.extend(block_data[block_offset:block_offset + chunk])
            position += chunk
            remaining -= chunk

        self.seek_positions[fd] = position
        return data

    def rm_rf(self, pathname):
        pathname = self._resolve_path(pathname)
        fd_index = self.root_dir.get(pathname)
        if fd_index is None:
            raise FileNotFoundError("Path not found")
        fd = self.file_descriptors[fd_index]
        if fd.file_type == 'directory':
            for name in list(self.root_dir.keys()):
                if name.startswith(pathname + '/'):
                    self.rm_rf(name)
            self.rmdir(pathname)
        else:
            self.unlink(pathname)

    def write(self, fd, data):
        if self.open_files[fd] is None:
            raise ValueError("File descriptor not open")
        fd_index = self.open_files[fd]
        position = self.seek_positions[fd]
        file_descriptor = self.file_descriptors[fd_index]

        remaining = len(data)
        written = 0
        while remaining > 0:
            block_index = position // BLOCK_SIZE
            block_offset = position % BLOCK_SIZE
            if block_index >= len(file_descriptor.block_map):
                block_num = self.device.allocate_block()
                file_descriptor.block_map.append(block_num)
            else:
                block_num = file_descriptor.block_map[block_index]

            block_data = self.device.read_block(block_num)
            chunk = min(BLOCK_SIZE - block_offset, remaining)
            block_data[block_offset:block_offset + chunk] = data[written:written + chunk]
            self.device.write_block(block_num, block_data)

            position += chunk
            written += chunk
            remaining -= chunk

        file_descriptor.size = max(file_descriptor.size, position)
        self.seek_positions[fd] = position

    def link(self, name1, name2):
        name1 = self._resolve_path(name1)
        name2 = self._resolve_path(name2)
        fd_index = self.root_dir.get(name1)
        if fd_index is None:
            raise FileNotFoundError("File not found")
        if name2 in self.root_dir:
            raise ValueError("File already exists")
        if self.file_descriptors[fd_index].file_type == 'directory':
            raise ValueError("Cannot link to a directory")
        self.root_dir[name2] = fd_index
        self.file_descriptors[fd_index].hard_links += 1

    def unlink(self, pathname):
        pathname = self._resolve_path(pathname)
        fd_index = self.root_dir.pop(pathname, None)
        if fd_index is None:
            raise FileNotFoundError("File not found")
        fd = self.file_descriptors[fd_index]
        if fd.file_type == 'directory':
            raise ValueError("Cannot unlink a directory")
        fd.hard_links -= 1
        if fd.hard_links == 0 and not any(fd_index in self.open_files for fd_index in self.open_files):
            for block_num in fd.block_map:
                self.device.free_block(block_num)
            self.file_descriptors[fd_index] = None

    def truncate(self, pathname, size):
        pathname = self._resolve_path(pathname)
        fd_index = self.root_dir.get(pathname)
        if fd_index is None:
            raise FileNotFoundError("File not found")
        file_descriptor = self.file_descriptors[fd_index]

        if size < file_descriptor.size:
            blocks_to_free = (file_descriptor.size + BLOCK_SIZE - 1) // BLOCK_SIZE - (
                        size + BLOCK_SIZE - 1) // BLOCK_SIZE
            for _ in range(blocks_to_free):
                block_num = file_descriptor.block_map.pop()
                self.device.free_block(block_num)
        elif size > file_descriptor.size:
            num_blocks_needed = (size + BLOCK_SIZE - 1) // BLOCK_SIZE - (
                        file_descriptor.size + BLOCK_SIZE - 1) // BLOCK_SIZE
            for _ in range(num_blocks_needed):
                block_num = self.device.allocate_block()
                file_descriptor.block_map.append(block_num)

        file_descriptor.size = size