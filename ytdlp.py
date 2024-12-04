import yt_dlp
import concurrent.futures
import traceback
import os
import re
import threading
import functools
from pathlib import Path
import copy


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


class DownloadPause(Exception):
    pass


class DownloadCancel(Exception):
    pass


class Downloader(object):
    def __init__(self, notify, max_workers=5):
        # self.listener_thread = threading.Thread(target=process_queue, args=(q, 5))
        # self.listener_thread.start()
        self.notify = notify
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.medias = {}
        self.mutex = threading.Lock()

    def update_notify(self):
        for filename in self.medias:
            message = {}
            message["filename"] = filename
            message["status"] = self.medias[filename]["status"]
            message["size"] = human_size(self.medias[filename]["size"])
            message["downloaded_bytes"] = self.medias[filename].get(
                "downloaded_bytes", 0
            )
            message["percent"] = self.medias[filename].get("percent", "N/A")
            self.notify(message)

    def progress_hook(self, progress):
        m = {}
        media = {}
        # print(progress)
        if progress.get("info_dict") is None:
            return

        if progress.get("info_dict").get("_filename") is None:
            return

        filename = progress["info_dict"]["_filename"]
        with self.mutex:
            media = copy.deepcopy(self.medias[filename])
            if media.get("status", "N/A") == "pause":
                raise DownloadPause("pasue")

            if media.get("status", "N/A") == "cancel":
                raise DownloadCancel("cancel")

        m["filename"] = filename
        if media["size"] > 0:
            m["size"] = human_size(media["size"])
        else:
            total_bytes_str = re.sub(
                r"\u001b\[[0-9;]*m", "", progress.get("_total_bytes_str", "N/A")
            )
            total_bytes_estimate_str = re.sub(
                r"\u001b\[[0-9;]*m",
                "",
                progress.get("_total_bytes_estimate_str", "N/A"),
            )
            if re.search(r"\d", total_bytes_str):
                m["size"] = total_bytes_str
            elif re.search(r"\d", total_bytes_estimate_str):
                m["size"] = total_bytes_estimate_str

        if progress.get("status") == "downloading":
            subfiles = media["subfiles"]
            ext = progress["info_dict"]["ext"]
            if subfiles.get(ext) is None:
                subfiles[ext] = {}
            subfiles[ext]["downloaded_bytes"] = progress.get("downloaded_bytes")
            total_downloaded_bytes = 0
            for key in subfiles:
                total_downloaded_bytes += subfiles[key].get("downloaded_bytes", 0)

            m["downloaded_bytes"] = human_size(total_downloaded_bytes)

            if progress.get("_speed_str"):
                m["speed"] = re.sub(r"\u001b\[[0-9;]*m", "", progress.get("_speed_str"))
            else:
                m["speed"] = "N/A"

            if media["size"] > 0:
                m["percent"] = f"{total_downloaded_bytes/media['size']*100:.2f}%"
            else:
                m["percent"] = re.sub(
                    r"\u001b\[[0-9;]*m", "", progress.get("_percent_str")
                )

            if progress.get("speed") and media["size"] > 0:
                m["eta"] = human_time(
                    (media["size"] - total_downloaded_bytes) / progress.get("speed")
                )
            else:
                m["eta"] = re.sub(
                    r"\u001b\[[0-9;]*m", "", progress.get("_eta_str", "N/A")
                )

            m["status"] = progress["status"]

        elif progress["status"] == "finished":
            m["status"] = "download_finished"
            m["speed"] = "convert"

        # print(m)
        with self.mutex:
            self.medias[filename]["percent"] = m.get("percent", "N/A")
            self.medias[filename]["downloaded_bytes"] = m.get("downloaded_bytes", "N/A")
            self.medias[filename]["status"] = m.get("status", "N/A")
            self.medias[filename]["subfiles"] = media.get("subfiles", {})

        self.notify(m)

    def post_hook(self, fullname):
        # basename = os.path.basename(fullname)
        filename = os.path.basename(fullname)
        m = {}
        m["filename"] = filename
        m["status"] = "finished"
        with self.mutex:
            if self.medias[filename].get("status", "N/A") == "cancel":
                raise DownloadCancel("cancel")
            self.medias[filename]["status"] = "finished"
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
            try:
                playlist_info = ydl.extract_info(media["url"], download=False)
            except Exception as e:
                print(e)
                media["status"] = "error"
                return

            if playlist_info.get("_type", "N/A") == "url":
                media["url"] = playlist_info["url"]
                self.extract_info(media)
                return
            filename = ydl.prepare_filename(playlist_info)
            formats = playlist_info.get("requested_formats")
            if formats is None and "url" not in playlist_info:
                media["status"] = "error"
                return
            total_size = 0
            subfiles = {}

            if formats:
                for fmt in formats:
                    size = 0
                    try:
                        size = int(fmt["filesize"])
                    except (TypeError, ValueError):
                        try:
                            size = int(fmt["filesize_approx"])
                        except (TypeError, ValueError):
                            print("couldn't get size")
                    subfiles[fmt["ext"]] = {"size": size}
                    total_size += size

            # filename = os.path.splitext(filename)[0]
            print("add filename: ", filename)
            media["filename"] = filename
            with self.mutex:
                self.medias[filename] = {
                    "title": playlist_info["title"],
                    "url": media["url"],
                    "size": total_size,
                    "quality": media["quality"],
                    "format": media["format"],
                    "status": media["status"],
                    "subfiles": subfiles,
                    "downloaded_bytes": "0Mb",
                    "percent": "0%",
                }

    def handle_exception(self, future, filename):
        message = {}
        message["filename"] = filename
        try:
            future.result()
        except DownloadPause:
            message["status"] = "pause"
            self.notify(message)
        except DownloadCancel:
            base_path = Path(".")
            files = base_path.glob(f"{filename}*")
            for f in files:
                os.remove(f)
            with self.mutex:
                self.medias.pop(filename)
            message["status"] = "cancel"
            self.notify(message)
        except Exception as e:
            print("Caught an exception in callback:")
            message["status"] = "error"
            message["info"] = traceback.format_exc()
            print(message["info"])
            self.notify(message)

    def pause(self, media):
        with self.mutex:
            media = self.medias.get(media["filename"])
            if media:
                media["status"] = "pause"

    def resume(self, media):
        filename = media["filename"]
        with self.mutex:
            media = self.medias.get(filename)
            if media:
                media["status"] = "downloading"
                print(f"start download: {media['url']}")
                future = self.executor.submit(self.download_process, media)
                handle_exception_with_args = functools.partial(
                    self.handle_exception, filename=filename
                )
                future.add_done_callback(handle_exception_with_args)
                print(f"submit: {media['url']}")

    def add(self, media):
        self.extract_info(media)
        if media["status"] == "downloading":
            print(f"start download: {media['url']}")
            future = self.executor.submit(self.download_process, media)
            handle_exception_with_args = functools.partial(
                self.handle_exception, filename=media["filename"]
            )
            future.add_done_callback(handle_exception_with_args)
            print(f"submit: {media['url']}")
        elif media["status"] == "pause":
            message = {}
            message["size"] = human_size(self.medias[media["filename"]]["size"])
            message["filename"] = media["filename"]
            message["percent"] = self.medias[media["filename"]]["percent"]
            message["downloaded_bytes"] = self.medias[media["filename"]][
                "downloaded_bytes"
            ]
            message["status"] = "pause"
            self.notify(message)
        elif media["status"] == "error":
            message = {}
            message["status"] = "error"
            message["info"] = "extract video info failed"
            self.notify(message)

    def cancel(self, media):
        filename = media["filename"]
        if self.medias.get(filename):
            with self.mutex:
                status = self.medias[filename].get("status", "N/A")
                if status == "finished" or status == "pause":
                    base_path = Path(".")
                    files = base_path.glob(f"{filename}*")
                    for f in files:
                        print(f)
                        os.remove(f)
                    self.medias.pop(filename)
                    message = {}
                    message["filename"] = filename
                    message["status"] = "cancel"
                    self.notify(message)
                else:
                    self.medias[filename]["status"] = "cancel"


if __name__ == "__main__":
    import time

    def notify(message):
        print(message)

    downaloader = Downloader(notify)
    downaloader.add(
        {
            "url": "https://v.qq.com/x/page/o3550b3cudq.html",
            "format": "mp3",
            "quality": "360p",
            "status": "downloading",
        }
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        exit(0)
