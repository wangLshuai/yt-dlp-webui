
let socket;

function createProgress() {

}
function updateProgress(progressJson) {
  const progressContainer = document.getElementById('progress-container');
  let progressItem =
    progressContainer.querySelector(`[filename='${progressJson['filename']}']`)

  if (progressItem === null) {
    progressItem = document.getElementById('progress-item-template')
      .content.querySelector('.progress-item').cloneNode(true);

    progressItem.setAttribute('filename', `${progressJson['filename']}`);
    progressItem.setAttribute('status', progressJson['status']);
    if (progressJson['status'] === 'downloading') {
      const button = progressItem.querySelector('.progress-button');
      button.classList.add('running');
      const pauseBar = progressItem.querySelector('.pause-bar');
      const playTriangle = progressItem.querySelector('.play-triangle');
      pauseBar.style.display = 'block';
      playTriangle.style.display = 'none';
    }
    progressContainer.insertBefore(progressItem, progressContainer.firstChild);

    const fileNameLabel = progressItem.querySelector('.filename-label');
    fileNameLabel.textContent = progressJson['filename'];

  }

  if (progressJson['status'] === 'cancel') {
    progressItem.remove();
    return;
  }


  if (progressJson['size'] != null) {
    const size = progressItem.querySelector('.size');
    size.textContent = progressJson['size'];
  }

  if (progressJson['downloaded_bytes'] != null) {
    const downloaded_bytes = progressItem.querySelector('.downloaded_bytes');
    downloaded_bytes.textContent = progressJson['downloaded_bytes'];
  }

  if (progressJson['status'] === 'finished') {
    console.log(`${progressJson['filename']} finished`);

    progressItem.setAttribute('status', 'finished');

    const button = progressItem.querySelector('.progress-button');
    if (button != null)
      button.remove();

    const downloaded_bytes = progressItem.querySelector('.downloaded_bytes');
    if (downloaded_bytes != null)
      downloaded_bytes.remove();

    const speed = progressItem.querySelector('.speed');
    if (speed != null)
      speed.remove();

    const eta = progressItem.querySelector('.eta');
    if (eta != null)
      eta.remove();
    return;
  }


  const progress = progressItem.querySelector('.circle-progress');
  const r = progress.getAttribute('r');
  const percent_str = progressJson['percent'];
  if (percent_str != null) {
    const percent = parseFloat(percent_str) / 100;
    const l = 2 * r * Math.PI;
    progress.style.strokeDasharray = `${percent * l},${l}`;
  }

  const speed = progressItem.querySelector('.speed');
  speed.textContent = progressJson['speed'];
  const eta = progressItem.querySelector('.eta');
  eta.textContent = progressJson['eta'];


}

function handleSubmit(event) {
  event.preventDefault();
  const urlInput =
    document.getElementById('media-url-input');
  const mediaUrl = urlInput.value;
  const quality = document.getElementById('quality').value;
  const format = document.getElementById('format').value;
  const auto = document.getElementById('auto').value;
  let media;
  if (auto === 'yes') {
    media = { 'url': mediaUrl, 'quality': quality, 'format': format, 'status': 'downloading' }
  } else {
    media = { 'url': mediaUrl, 'quality': quality, 'format': format, 'status': 'pause' }
  }
  const message = { 'action': 'add', 'media': media };
  socket.send(JSON.stringify(message));
  urlInput.value = '';
}

function setupWs() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const path = '/ws';

  const ws_url = `${protocol}//${host}${path}`;
  socket = new WebSocket(ws_url);

  socket.addEventListener('message', function (event) {
    const message = JSON.parse(event.data);
    if (message['status'] == 'error') {
      alert(`server info: ${message['info']}`)
    } else {
      updateProgress(message)
    }
  });

  function closeEventHandler() {
    console.log('Connection closed,retry');
    setTimeout(setupWs, 2000);
  }

  function errorEventHandler(event) {
    console.log('Error detected', event);
    socket.removeEventListener('close', closeEventHandler);
    socket.removeEventListener("error", errorEventHandler);

    closeEventHandler();
  }

  socket.addEventListener('close', closeEventHandler);

  socket.addEventListener('error', errorEventHandler);
}

function onProgressButtonClick(button) {
  const progressItem = button.parentElement;
  const isRunning = button.classList.toggle('running');
  const playTriangle = button.querySelector('.play-triangle');
  const pauseBar = button.querySelector('.pause-bar');

  const filename = progressItem.getAttribute('filename');

  const media = { 'filename': filename };
  if (isRunning) {
    pauseBar.style.display = 'block';
    playTriangle.style.display = 'none';
    const message = { 'action': 'resume', 'media': media };
    socket.send(JSON.stringify(message));
  } else {
    pauseBar.style.display = 'none';
    playTriangle.style.display = 'block';
    const message = { 'action': 'pause', 'media': media };
    socket.send(JSON.stringify(message));
  }

}

function onCancelClick(cancel) {
  const progressItem = cancel.parentElement.parentElement.parentElement;
  const filename = progressItem.getAttribute('filename');
  userResponse = confirm(`你确定删除 《${filename}》下载载任务吗？`);
  if (userResponse == true) {
    const media = { 'filename': filename };
    const message = { 'action': 'cancel', 'media': media };
    socket.send(JSON.stringify(message));
  }
}
setupWs();
