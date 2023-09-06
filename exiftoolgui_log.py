import asyncio
import aiofiles

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
        self.queue = asyncio.Queue()

        # self.consumer_task = None

        # self.loop = asyncio.get_event_loop()
        # self.loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(self.loop)
        # self.consumer_task = self.loop.create_task(self.write_log())

        pass

    def log(self, cat: str, file: str, message: str) -> None:
        timestamp: str = f"{datetime.now().astimezone().strftime('%Y:%m:%d %H:%M:%S.%f%z')}"
        message_f: str = f"{timestamp} [{cat}]: \n  SourceFile: {file}\n  {message}"
        self.queue.put_nowait(message_f + '\n')
        print("log")

    async def write(self):
        async with aiofiles.open(self.source_file, mode='a', encoding='utf-8') as file:
            while True:
                message = await self.queue.get()
                await file.write(message + "\n")
                await file.flush()
                self.queue.task_done()
                print("write")

    async def close(self):
        await self.queue.join()
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass

    # def start(self):
    #     # self.consumer_task = asyncio.create_task(self.write_log())
    #     # await self.consumer_task
    #     self.loop.run_until_complete(self.write_log())

    # def stop(self):
    #     asyncio.run(self.close())


if __name__ == "__main__":

    async def generate():
        while True:
            await asyncio.sleep(1)
            log.log('test_cat1', 'test_file1', 'test_message1')
            log.log('test_cat2', 'test_file2', 'test_message2')

    async def main():
        # task_generate = asyncio.create_task(generate())
        # log.consumer_task = asyncio.create_task(log.write())
        await asyncio.gather(generate(), log.write())

    log = ExifToolGUILog.Instance

    asyncio.run(main())

    # asyncio.run(log.start())
    # log.loop.run_until_complete(log.write_log())
    # log.stop()
