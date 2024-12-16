FROM alpine

# install aiohttp depended,gcc,muls-dev python3-dev in arm32 platform
RUN apk add --no-cache ffmpeg python3 py3-pip gcc python3-dev musl-dev && \
    python3 -m venv /venv && \
    mkdir -p /var/media

ENV PATH="/venv/bin:$PATH"
RUN pip install --upgrade pip && pip install yt-dlp aiohttp cloudscraper -i https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app/
COPY ./ .
CMD ["python", "./main.py", "--output", "/var/media"]