
let socket;

function createProgress() {

}
function updateProgress(progressJson) {
  const progressContainer = document.getElementById('progress-container');
  let progressItem =
    progressContainer.querySelector(`[filename='${progressJson['filename']}']`)

  if (progressItem === null) {
    console.log(`not founded #${progressJson['filename']}`)

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

  if (progressJson['size'] != null) {
    const size = progressItem.querySelector('.size');
    size.textContent = progressJson['size'];
  }

  if (progressJson['status'] === 'finished') {
    console.log(`${progressJson['filename']} finished`);

    progressItem.setAttribute('status', 'finished');

    const button = progressItem.querySelector('.progress-button');
    button.remove();

    const speed = progressItem.querySelector('.speed');
    speed.remove();

    const eta = progressItem.querySelector('.eta');
    eta.remove();
    return;
  }


  const progress = progressItem.querySelector('.circle-progress');
  const r = progress.getAttribute('r');
  const percent_str = progressJson['percent'];
  if (percent_str != null) {
    const percent = parseFloat(percent_str) / 100;
    const l = 2 * r * Math.PI;
    console.log(`percent*l: ${percent * l} l:${l}`);
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
  urlInput.value = '';
  const quality = document.getElementById('quality').value;
  const format = document.getElementById('format').value;
  const auto = document.getElementById('auto').value;
  const media = { 'url': mediaUrl, 'quality': quality, 'format': format, 'auto': auto }
  const message = { 'action': 'add', 'media': media };
  socket.send(JSON.stringify(message));
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
      console.log(message);
      updateProgress(message)
    }
  });


  socket.addEventListener('close', function (event) {
    console.log('Connection closed');
    setTimeout(setupWs, 1000);
  });

  socket.addEventListener('error', function (event) {
    console.error('Error detected', event);
  });
}

function onProgressButtonClick(button) {
  console.log(button);
  const progressItem = button.parentElement;
  const isRunning = button.classList.toggle('running');
  console.log(isRunning);
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
    console.log('pause,display block');
    pauseBar.style.display = 'none';
    playTriangle.style.display = 'block';
    const message = { 'action': 'pause', 'media': media };
    socket.send(JSON.stringify(message));
  }

}

function onCancelClick(cancel) {
  console.log(cancel);
}
setupWs();
