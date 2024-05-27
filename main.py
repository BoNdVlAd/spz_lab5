from BlockDevice import *
from FileSystem import *

BLOCK_SIZE = 512
MAX_FILE_DESCRIPTORS = 100
MAX_FILENAME_LENGTH = 255
MAX_OPEN_FILES = 100


def main():

    device = BlockDevice(10 * 1024 * 1024)
    print("Ініціалізація файлової системи")
    fs = FileSystem(device, MAX_FILE_DESCRIPTORS)
    fs.mkfs(MAX_FILE_DESCRIPTORS)

    print('-------------------------------------------------------------------------------------------------')

    print("Створення файлу example_file.txt, запис тексту, читання з файлу, закриття файлу:")
    fs.create("example_file.txt")
    fd = fs.open("example_file.txt")
    fs.write(fd, b"Hello, World!")
    fs.seek(fd, 0)
    print(fs.read(fd, 13).decode())
    fs.close(fd)

    print('---------------------------------------------------------------------------------------------------')

    print("Створення директорії dir1 та створення у ній файлу file_dir1.txt")
    fs.mkdir("dir1")
    fs.create("dir1/file_dir1.txt")
    print("Файли в поточній директорії:", fs.ls())


    print('---------------------------------------------------------------------------------------------------')

    print("Відкриття та запис даних у файл file_dir1.txt у директорії dir1")

    fd = fs.open("dir1/file_dir1.txt")
    fs.write(fd, b"I`m Vlad")
    fs.close(fd)

    print('---------------------------------------------------------------------------------------------------')

    print('Перехід в директорію dir1')
    fs.cd("dir1")
    print("Поточна директорія:", fs.current_dir)
    print("Файли в поточній директорії:", fs.ls())

    print('---------------------------------------------------------------------------------------------------')

    print("Вихід у кореневу директорію")
    fs.cd("/")
    print("Поточна директорія:", fs.current_dir)

    print('---------------------------------------------------------------------------------------------------')

    print("Створення символічного посилання на файл(dir1/file_dir1.txt) у директорії dir1")

    fs.symlink("dir1/file_dir1.txt", "symlink_to_file")
    fd = fs.open("symlink_to_file")
    print('читання посилання', fs.read(fd, 8).decode())
    fs.close(fd)

    print('---------------------------------------------------------------------------------------------------')

    print("Видалення символічного посилання на файл file_dir1.txt")
    print("Файли в поточній директорії:", fs.ls())
    fs.unlink("symlink_to_file")
    print('Видалення посилання...')
    print("Файли в поточній директорії:", fs.ls())
    print("Читання файлу file_dir1.txt після видалення символічного посилання на нього:")
    fd = fs.open("dir1/file_dir1.txt")
    print('читання file_dir1.txt: ', fs.read(fd, 8).decode())
    fs.close(fd)

    print('---------------------------------------------------------------------------------------------------')

    print("Видалення директорії dir1")
    fs.rmdir("dir1")
    print("Файли в кореневому каталозі після видалення dir1:", fs.ls())

    print('---------------------------------------------------------------------------------------------------')

    print("Спроба ще раз видалити директорію dir1: ")
    fs.rmdir("dir1")

if __name__ == "__main__":
    main()