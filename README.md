docker build -t yt-dlp-webui .

docker run -d --restart=always -p 5480:5480 -v /media/dir:/var/media yt-dlp-webui