import asyncio
from aiohttp import web
import os
from functools import reduce
from ytdlp import Downloader
import logging
import argparse


async def index(request):
    cwd = os.getcwd()
    filepath = os.path.join(cwd, "index.html")
    return web.FileResponse(path=filepath)


def process_action(message):
    logger.info(message)
    if message["action"] == "add":
        downloader.add(message["media"])
    if message["action"] == "pause":
        downloader.pause(message["media"])
    if message["action"] == "resume":
        downloader.resume(message["media"])
    if message["action"] == "cancel":
        downloader.cancel(message["media"])


async def websocket_progress(request):
    ws = web.WebSocketResponse()
    global progress_ws_list
    await ws.prepare(request)
    progress_ws_list.append(ws)
    logger.info("WebSocket connection opened")
    logger.info(f"WebSocket connect num: {len(progress_ws_list)}")
    downloader.update_notify()
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                message = msg.json()
                process_action(message)

            elif msg.type == web.WSMsgType.ERROR:
                logger.info(f"ws connection closed with exception {ws.exception()}")
    finally:
        logger.info("WebSocket connection closed")
        progress_ws_list.remove(ws)
        await ws.close()

    return ws


def sync_notify(message):

    global server_loop
    for ws in progress_ws_list:
        asyncio.run_coroutine_threadsafe(ws.send_json(message), server_loop)


async def my_background_task():
    while True:
        await asyncio.sleep(1)
        m = {
            "id": "9112128_part1",
            "downloaded_bytes": "2096128",
            "filename": "上古卷轴5天际 吟游诗人-龙裔来了 The Dragonborn Comes [9112128_part1].f2.m4a",
            "filename": "上古卷轴5天际 吟游诗人-龙裔来了 The Dragonborn Comes",
            "status": "downloading",
            "speed": "1Mb/s",
            "size": "300Mb",
            "percent": " 36.3%",
            "eta": "1",
        }

        for ws in progress_ws_list:
            logger.info("send message")
            await ws.send_json(m)


async def on_startup(app):
    app["my_background_task"] = asyncio.create_task(my_background_task())


progress_ws_list = []
server_loop = None
downloader = None
app = web.Application()
# app.on_startup.append(on_startup)

app.router.add_static("/static", "static")
app.router.add_get("/", index)
app.router.add_get("/ws", websocket_progress)


async def start_server(port):
    global server_loop
    server_loop = asyncio.get_running_loop()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Server started at http://0.0.0.0:{port}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="--output: the output directory (default: ./)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="./download/",
        help="the output directory (default: ./download/)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default="5480",
        help="the http listen port (default: 5480)",
    )

    args = parser.parse_args()

    output_directory = args.output
    if output_directory[-1] != "/":
        output_directory += "/"

    print(f"Output directory set to: {output_directory}")

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
        print(f"Created directory: {output_directory}")

    downloader = Downloader(sync_notify, output_directory)

    logger = logging.getLogger("yt-dlp-webui-logger")
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(start_server(args.port))

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
