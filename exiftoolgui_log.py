import queue
import threading

from datetime import datetime


class ExifToolGUILog:
    _instance: 'ExifToolGUILog' = None

    @classmethod
    @property
    def Instance(cls) -> 'ExifToolGUILog':
        if cls._instance == None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.source_file = 'exiftoolgui.log'

        self._queue = queue.Queue()
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self.write)

        self._thread.daemon = True
        self._thread.start()

    def __del__(self):
        self._queue.join()

    def append(self, cat: str, file: str, message: str) -> None:
        timestamp: str = f"{datetime.now().astimezone().strftime('%Y:%m:%d %H:%M:%S.%f%z')}"
        message_f: str = f"{timestamp} [{cat}]: \n  SourceFile: {file}\n  {message}"
        self._queue.put(message_f + '\n')
        # print("log")

    def write(self):
        with open(self.source_file, mode='a', encoding='utf-8') as file:
            while True:
                with self._lock:
                    message = self._queue.get()
                    message = str(message).strip()
                    file.write(message + "\n")
                    file.flush()
                    self._queue.task_done()
                    # print("write")


if __name__ == "__main__":

    log = ExifToolGUILog.Instance

    log.append('test_cat1', 'test_file1', 'test_message1')
    log.append('test_cat2', 'test_file2', 'test_message2')
