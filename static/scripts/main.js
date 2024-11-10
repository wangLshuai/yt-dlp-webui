
let socket;
function updateProgress(progressJson) {
  var progressContainer = document.getElementById('progress-container');
  var progressItem =
    progressContainer.querySelector(`[name="${progressJson['filename']}"]`)

  if (progressJson['status'] === 'finished') {
    console.log(`${progressJson['filename']} finished`);
    if (progressItem !== null)
      progressItem.remove();

    mediaListContainer = document.getElementById("finish-container");

    const newCheckbox = document.createElement('input');
    newCheckbox.type = 'checkbox';

    const newLabel = document.createElement('label');
    newLabel.className = 'media-label';
    newLabel.appendChild(newCheckbox);
    newLabel.appendChild(document.createTextNode(progressJson['filename']));
    mediaListContainer.appendChild(newLabel);
    return;

  }

  if (progressItem === null) {
    console.log(`not founded #${progressJson['filename']}`)

    progressItem = document.createElement('div');
    progressItem.setAttribute('name', `${progressJson['filename']}`);
    progressItem.setAttribute('class', 'progress-item');
    progressContainer.appendChild(progressItem);

    var label = document.createElement('label');
    label.setAttribute('class', 'filename-label');
    label.textContent = progressJson['filename'];
    progressItem.appendChild(label);


    var progressBar = document.createElement('dev');
    progressBar.setAttribute('class', 'progress-bar');
    progressItem.append(progressBar);

    var progress = document.createElement('dev');
    progress.setAttribute('class', 'progress');
    progressBar.appendChild(progress);

    var size = document.createElement('label');
    size.setAttribute('class', 'size');
    progressItem.appendChild(size);

    var speed = document.createElement('label');
    speed.setAttribute('class', 'speed');
    progressItem.appendChild(speed);

    var eta = document.createElement('label');
    eta.setAttribute('class', 'eta');
    progressItem.appendChild(eta);
  }


  var progress = progressItem.querySelector('.progress');
  progress.style.width = progressJson['percent'];
  var size = progressItem.querySelector('.size');
  size.textContent = progressJson['size'];
  var speed = progressItem.querySelector('.speed');
  speed.textContent = progressJson['speed'];
  var eta = progressItem.querySelector('.eta');
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

setupWs();
