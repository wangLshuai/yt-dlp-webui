import yt_dlp
import concurrent.futures
import traceback
import os
import re
import functools


def human_size(size):
    unit = ["B", "K", "M", "G"]
    while size > 1024:
        size /= 1024
        unit.pop(0)

    return f"{size:.2f}{unit[0]}"


def human_time(seconds):
    h_str = ""
    m_str = ""

    if seconds > 3600:
        h_str = f"{int(seconds/3600):02d}:"
        m_str = "00:"
        seconds %= 3600
    if seconds > 60:
        m_str = f"{int(seconds/60):02d}:"
        seconds %= 60
    return h_str + m_str + f"{int(seconds):02d}"


class Downloader(object):
    def __init__(self, notify, max_workers=5):
        # self.listener_thread = threading.Thread(target=process_queue, args=(q, 5))
        # self.listener_thread.start()
        self.notify = notify
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.medias = {}

    def progress_hook(self, progress):
        m = {}
        if progress.get("info_dict") and progress.get("info_dict").get("_filename"):
            filename = os.path.splitext(
                os.path.basename(progress["info_dict"]["_filename"])
            )[0]
            m["filename"] = filename
            m["size"] = human_size(self.medias[filename]["size"])
            if self.medias[filename]["auto"] == "no":
                raise KeyboardInterrupt("pasue")

            # if progress.get("_total_bytes_str"):
            #     m["size"] = re.sub(
            #         r"\u001b\[[0-9;]*m", "", progress.get("_total_bytes_str")
            #     )
            # else:
            #     m["size"] = "N/A"

            if progress.get("status") == "downloading":
                m["id"] = progress["info_dict"]["id"]
                subfiles = self.medias[filename]["subfiles"]
                ext = progress["info_dict"]["ext"]
                subfiles[ext]["downloaded_bytes"] = progress.get("downloaded_bytes")
                total_downloaded_bytes = 0
                for key in subfiles:
                    total_downloaded_bytes += subfiles[key].get("downloaded_bytes", 0)
                m["downloaded_bytes"] = total_downloaded_bytes

                if progress.get("_speed_str"):
                    m["speed"] = re.sub(
                        r"\u001b\[[0-9;]*m", "", progress.get("_speed_str")
                    )
                else:
                    m["speed"] = "N/A"
                m["status"] = progress["status"]
                m["percent"] = (
                    f"{total_downloaded_bytes/self.medias[filename]["size"]*100:.2f}%"
                )
                if progress.get("speed"):

                    m["eta"] = human_time(
                        (self.medias[filename]["size"] - total_downloaded_bytes) / progress.get("speed")
                    )
                else:
                    m["eta"] = "N/A"

            # elif progress["status"] == "finished":
            #     m["status"] = "download_finished"
            #     m["speed"] = "convert"

        # print(m)
        self.notify(m)

    def post_hook(self, fullname):
        basename = os.path.basename(fullname)
        filename = os.path.splitext(basename)[0]
        m = {}
        m["filename"] = filename
        m["status"] = "finished"
        size = os.path.getsize(fullname)
        for uint in ["B", "K", "M", "G"]:
            if size < 1024:
                break
            size /= 1024
        m["size"] = f"{size:.2f}{uint}"
        print(f"{filename}------------ convert finished")
        self.notify(m)

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

        # params['playlist_items'] = '1'
        yt_dlp.YoutubeDL(params).download(media["url"])

    def extract_info(self, media):
        params = {
            "extract_flat": True,
            "outtmpl": "%(title)s.%(ext)s",
            "format": f'wv[height>={media["quality"]}]+bestaudio/w[height>={media["quality"]}]/bv+ba/best',
        }
        with yt_dlp.YoutubeDL(params) as ydl:
            playlist_info = ydl.extract_info(media["url"], download=False)
            filename = ydl.prepare_filename(playlist_info)

            formats = playlist_info.get("requested_formats", [])

            total_size = 0
            subfiles = {}
            for fmt in formats:
                size = 0
                try:
                    size = int(fmt.get("filesize", "N/A"))
                except (TypeError, ValueError):
                    try:
                        size = int(fmt.get("filesize_approx", "N/A"))
                    except (TypeError, ValueError):
                        print("couldn't get size")
                subfiles[fmt["ext"]] = {"size": size}
                total_size += size

            filename = os.path.splitext(filename)[0]
            print("add filename: ", filename)
            media["filename"] = filename
            self.medias[filename] = {
                "title": playlist_info["title"],
                "url": media["url"],
                "size": total_size,
                "quality": media["quality"],
                "format": media["format"],
                "auto": media["auto"],
                "subfiles": subfiles,
            }
            print(self.medias[filename])

    def handle_exception(self, future, filename):
        message = {}
        message["filename"] = filename
        try:
            future.result()
        except KeyboardInterrupt:
            message["status"] = "pause"
            self.notify(message)
        except Exception as e:
            print("Caught an exception in callback:")
            message["status"] = "error"
            message["info"] = traceback.format_exc()
            print(message["info"])
            self.notify(message)

    def pause(self, media):
        media = self.medias.get(media["filename"])
        if media:
            media["auto"] = "no"

    def resume(self, media):
        filename = media["filename"]
        media = self.medias.get(filename)
        if media:
            media["auto"] = "yes"
            print(f"start download: {media['url']}")
            future = self.executor.submit(self.download_process, media)
            handle_exception_with_args = functools.partial(
                self.handle_exception, filename=filename
            )
            future.add_done_callback(handle_exception_with_args)
            print(f"commit: {media['url']}")

    def add(self, media):
        self.extract_info(media)
        if media["auto"] == "yes":
            print(f"start download: {media['url']}")
            future = self.executor.submit(self.download_process, media)
            handle_exception_with_args = functools.partial(
                self.handle_exception, filename=media["filename"]
            )
            future.add_done_callback(handle_exception_with_args)
            print(f"commit: {media['url']}")
        else:
            message = {}
            message["size"] = self.medias[media["filename"]]["size"]
            message["filename"] = media["filename"]
            message["percent"] = self.medias[media["filename"]]["size"]
            message["status"] = "pause"
            self.notify(media)


if __name__ == "__main__":
    import time

    def notify(message):
        print(message)

    downaloader = Downloader(notify)
    downaloader.add(
        {
            "url": "https://www.bilibili.com/video/BV1yx411C7YU",
            "format": "mp3",
            "quality": "360p",
            "auto": "yes",
        }
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        exit(0)
