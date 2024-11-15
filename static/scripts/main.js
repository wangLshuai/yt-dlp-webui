
let socket;
function updateProgress(progressJson) {
  const progressContainer = document.getElementById('progress-container');
  let progressItem =
    progressContainer.querySelector(`[name='${progressJson['filename']}']`)

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

  if (progressItem === null) {
    console.log(`not founded #${progressJson['filename']}`)

    progressItem = document.getElementById('progress-item-template')
      .content.querySelector('.progress-item').cloneNode(true);

    progressItem.setAttribute('name', `${progressJson['filename']}`);
    progressItem.setAttribute('status', progressJson['status']);
    if (progressJson['status'] === 'downloading') {
      const button = progressItem.querySelector('.progress-button');
      button.classList.add('running');
    }
    progressContainer.appendChild(progressItem);

    const fileNameLabel = progressItem.querySelector('.filename-label');
    fileNameLabel.textContent = progressJson['filename'];

  }


  const progress = progressItem.querySelector('.circle-progress');
  const r = progress.getAttribute('r');
  const percent = parseFloat(progressJson['percent']) / 100;
  const l = 2 * r * Math.PI;
  console.log(`percent*l: ${percent * l} l:${l}`);
  progress.style.strokeDasharray = `${percent * l},${l}`;
  const size = progressItem.querySelector('.size');
  size.textContent = progressJson['size'];
  const speed = progressItem.querySelector('.speed');
  speed.textContent = progressJson['speed'];
  const eta = progressItem.querySelector('.eta');
  eta.textContent = progressJson['eta'];


}

let urlform = document.getElementById('media-url-form')
  .addEventListener('submit', function (event) {
    event.preventDefault();
    const mediaUrl =
      document.getElementById('media-url-input').value;
    const quality = document.getElementById('quality').value;
    const format = document.getElementById('format').value;
    const auto = document.getElementById('auto').value;
    fetch('add', {
      method: 'POST',
      mode: 'cors',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        'url': mediaUrl,
        'quality': quality,
        'format': format,
        'auto': auto
      })
    })
      // .then(response => response.json())
      // .then(data => insertMediaList(data))
      .catch(error => console.error('Error', error));
  })

function setupWs() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const path = '/ws';

  const ws_url = `${protocol}//${host}${path}`;
  socket = new WebSocket(ws_url);

  // 当连接建立时触发
  socket.addEventListener('open', function (event) {
    // 发送一个JSON对象
    const message = { type: 'greeting', content: 'Hello, server!' };
    socket.send(JSON.stringify(message));
  });

  // 当从服务器接收到消息时触发
  socket.addEventListener('message', function (event) {
    // 解析接收到的JSON字符串
    const data = JSON.parse(event.data);
    if (data['status'] == 'error') {
      alert(`server info: ${data['info']}`)
    } else {
      console.log(data['filename'], data['percent'], data['speed'], data['eta']);
      updateProgress(data)
    }
  });

  // 当连接关闭时触发
  socket.addEventListener('close', function (event) {
    console.log('Connection closed');
    setTimeout(setupWs, 1000);
  });

  // 当发生错误时触发
  socket.addEventListener('error', function (event) {
    console.error('Error detected', event);
  });
}

function onProgressButtonClick(button) {
  console.log(button);
  const isRunning = button.classList.toggle('running');
  const playTriangle = button.querySelector('.play-triangle');
  const pauseBar = button.querySelector('.pause-bar')
  if (isRunning) {
    pauseBar.style.display = 'block';
    playTriangle.style.display = 'none';
  } else {
    pauseBar.style.display = 'none';
    playTriangle.style.display = 'block';
  }

}

function onCancelClick(cancel) {
  console.log(cancel);
}
setupWs();
