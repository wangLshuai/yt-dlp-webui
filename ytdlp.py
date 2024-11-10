import yt_dlp
import threading
import concurrent.futures
import traceback


class Downloader(object):
    def __init__(self, progress_hook, post_hook, max_workers=5):
        # self.listener_thread = threading.Thread(target=process_queue, args=(q, 5))
        # self.listener_thread.start()
        self.progress_hook = progress_hook
        self.post_hook = post_hook
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.futures = []

    def download_process(self, media):
        params = {
            "quiet": True,
            "format": "wv[height>=240]+bestaudio/bv*+ba/best",
            "no_warnings": True,
            "noprogress": True,
            # 'simulate':True,
            "outtmpl": "%(title)s.%(ext)s",
            "progress_hooks": [self.progress_hook],
            "post_hooks": [self.post_hook],
        }

        params["format"] = (
            f'wv[height>={media["quality"]}]+bestaudio/w[height>={media["quality"]}]/bv+ba/best'
        )
        print("format", params["format"])
        # ops = {
        #     'extract_flat':True
        # }

        # ydl = yt_dlp.YoutubeDL(ops)
        # playlist_info = ydl.extract_info(media['url'], download=False)
        # print(playlist_info)

        # params['playlist_items'] = '1'
        yt_dlp.YoutubeDL(params).download(media["url"])

    def handle_exception(self, future):
        try:
            # 尝试获取结果，如果任务正常完成，这里不会抛出异常
            result = future.result()
        except Exception as e:
            print("Caught an exception in callback:")
            message = {}
            message["status"] = "error"
            message["info"] = traceback.format_exc()
            print(message)
            self.progress_hook(message)

    def add(self, media):
        print(f"start download: {media['url']}")
        future = self.executor.submit(self.download_process, media)
        self.futures.append(future)
        future.add_done_callback(self.handle_exception)
        print(f"commit: {media['url']}")


def progress_hook(progress):
    print(progress)


def post_hook():
    print("complete")


if __name__ == "__main__":

    downloader = Downloader(progress_hook=progress_hook, post_hook=post_hook)

    # 创建一个线程来向队列中添加 URL
    urls = [
        "https://www.bilibili.com/video/BV1yx411C7YU",
        "https://www.bilibili.com/video/BV1bV4y1h7f6",
        # 添加更多视频 URL
    ]

    downloader.add(urls[0])
    downloader.add(urls[1])

    concurrent.futures.wait(downloader.futures)

    print("所有下载任务已完成")

# download('https://www.bilibili.com/video/BV1yx411C7YU')
