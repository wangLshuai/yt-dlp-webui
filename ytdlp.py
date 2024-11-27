import yt_dlp
import concurrent.futures
import traceback
import os
import re
import functools


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
            if self.medias[filename]["auto"] == "no":
                raise KeyboardInterrupt("pasue")

            if progress.get("_total_bytes_str"):
                m["size"] = re.sub(
                    r"\u001b\[[0-9;]*m", "", progress.get("_total_bytes_str")
                )
            else:
                m["size"] = "N/A"

        if progress.get("status") == "error":
            m = progress
        elif progress.get("status") == "downloading":
            m["id"] = progress["info_dict"]["id"]
            m["downloaded_bytes"] = progress.get("downloaded_bytes")

            if progress.get("_speed_str"):
                m["speed"] = re.sub(r"\u001b\[[0-9;]*m", "", progress.get("_speed_str"))
            else:
                m["speed"] = "0"
            m["status"] = progress["status"]
            m["percent"] = re.sub(r"\u001b\[[0-9;]*m", "", progress["_percent_str"])
            if progress.get("_eta_str"):
                m["eta"] = re.sub(r"\u001b\[[0-9;]*m", "", progress["_eta_str"])
            else:
                m["eta"] = 0

        elif progress["status"] == "finished":
            m["status"] = "download_finished"
            m["speed"] = "convert"

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
            for fmt in formats:
                size = 0
                try:
                    size = int(fmt.get("filesize", "N/A"))
                except (TypeError, ValueError):
                    try:
                        size = int(fmt.get("filesize_approx", "N/A"))
                    except (TypeError, ValueError):
                        print("couldn't get size")
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
            }

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


def progress_hook(progress):
    print(progress)


def post_hook():
    print("complete")
