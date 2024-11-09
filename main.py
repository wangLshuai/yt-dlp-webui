import asyncio
import subprocess
import aiohttp
from aiohttp import web
import os
from functools import reduce
from ytdlp import Downloader
from queue import Queue, Empty
import threading
import time
import re


async def index(request):
    cwd = os.getcwd()
    filepath = os.path.join(cwd, "index.html")
    return web.FileResponse(path=filepath)


# 解析视频格式
async def add_item(request):
    media = await request.json()
    print(media)
    # url = data['url']

    # process = await asyncio.create_subprocess_shell(
    #     f'yt-dlp -F "{url}"',
    #     stdout=subprocess.PIPE,
    #     stderr=subprocess.PIPE
    # )

    # stdout, stderr = await process.communicate()
    # if process.returncode != 0:
    #     print(f"Error: {stderr.decode()}")
    #     raise web.HTTPInternalServerError(text=f"Error: {stderr.decode()}")

    # formats = stdout.decode().strip().split('----------------------------------------------------------------------------------------------\n')
    # print(formats)
    # video_list = formats[1].split('\n')
    # print(video_list)
    # response_data = {
    #     video_list
    # }
    downloader.add(media)
    return web.json_response(status=200)
    redirect_url = (
        app.router["formats"]
        .url_for()
        .with_query({"url": url, "formats": "\n".join(formats)})
    )
    raise web.HTTPFound(redirect_url)


async def websocket_progress(request):
    # 创建一个新的WebSocket响应
    ws = web.WebSocketResponse()
    global progress_ws_list
    await ws.prepare(request)
    progress_ws_list.append(ws)
    print("len:", len(progress_ws_list))
    # 打印连接信息
    print("WebSocket connection opened")

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = msg.json()
                print(f"Received message: {data}")

            elif msg.type == web.WSMsgType.ERROR:
                print(f"ws connection closed with exception {ws.exception()}")
    finally:
        print("WebSocket connection closed")
        progress_ws_list.remove(ws)
        await ws.close()

    return ws


def sync_progress_hook(progress):
    # print("\n\nkeys---------------------------------------------------")
    # print(progress.keys())
    # print("\nprogresss+++++++++++++++++++++++++++++++++++++++++++++")
    # print(progress)
    # print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n\n")
    # print("\n\n")
    # print(progress['info_dict'].keys())
    m = {}
    if progress.get("status") == "error":
        m = progress
    elif progress.get("status") == "downloading":
        m["id"] = progress["info_dict"]["id"]
        m["downloaded_bytes"] = progress.get("downloaded_bytes")
        m["filename"] = progress["filename"]
        m["title"] = progress["info_dict"]["title"]
        m["size"] = re.sub(
            r"\u001b\[[0-9;]*m", "", progress.get("_total_bytes_str")
        )

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

        print(
            f'\r {m["filename"]} size {m["size"]} {m["percent"]} {m["speed"]} {m["eta"]}         ',
            end="",
        )
    elif progress["status"] == "finished":
        m["status"] = "download_finished"
        m["title"] = progress["info_dict"]["title"]
        m["speed"] = "convert"

    global server_loop
    for ws in progress_ws_list:
        asyncio.run_coroutine_threadsafe(ws.send_json(m), server_loop)


def sync_post_hook(fullname):
    basename = os.path.basename(fullname)
    filename = os.path.splitext(basename)[0]
    m = {}
    m["title"] = filename
    m["status"] = "finished"
    print(filename, " convert finished")
    for ws in progress_ws_list:
        asyncio.run_coroutine_threadsafe(ws.send_json(m), server_loop)


async def my_background_task():
    while True:
        await asyncio.sleep(1)
        m = {
            "id": "9112128_part1",
            "downloaded_bytes": "2096128",
            "filename": "上古卷轴5天际 吟游诗人-龙裔来了 The Dragonborn Comes [9112128_part1].f2.m4a",
            "title": "上古卷轴5天际 吟游诗人-龙裔来了 The Dragonborn Comes",
            "status": "downloading",
            "_percent_str": " 36.3%",
            "eta": "1",
        }

        # for ws in progress_ws_list:
        #     print("send message")
        #     await ws.send_json(m)


async def on_startup(app):
    app["my_background_task"] = asyncio.create_task(my_background_task())


progress_ws_list = []
server_loop = None
downloader = Downloader(sync_progress_hook, sync_post_hook)
app = web.Application()
app.on_startup.append(on_startup)

app.router.add_static("/static", "static")
app.router.add_get("/", index)
app.router.add_post("/add", add_item)
app.router.add_get("/ws", websocket_progress)


async def start_server():
    global server_loop
    server_loop = asyncio.get_running_loop()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("Server started at http://0.0.0.0:8080")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(start_server())

        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for ws in progress_ws_list:
            if not ws.closed:
                loop.run_until_complete(ws.close())
        loop.run_until_complete(app.shutdown())
        loop.run_until_complete(app.cleanup())
        loop.stop()
        loop.close()
