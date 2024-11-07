
function updateProgress(progressJson) {
  var progressContainer = document.getElementById('progress-container');
  var progressItem =
      progressContainer.querySelector(`[name="${progressJson['title']}"]`)
  if (progressItem === null) {
    console.log(`not founded #${progressJson['title']}`)

    progressItem = document.createElement('div');
    progressItem.setAttribute('name', `${progressJson['title']}`);
    progressItem.setAttribute('class', 'progress-item');
    progressContainer.appendChild(progressItem);

    var label = document.createElement('label');
    label.setAttribute('class', 'title-label');
    label.textContent = progressJson['title'];
    progressItem.appendChild(label);


    var progressBar = document.createElement('dev');
    progressBar.setAttribute('class', 'progress-bar');
    progressItem.append(progressBar);

    var progress = document.createElement('dev');
    progress.setAttribute('class', 'progress');
    progressBar.appendChild(progress);

    var speed = document.createElement('label');
    speed.setAttribute('class', 'speed');
    progressItem.appendChild(speed);

    var eta = document.createElement('label');
    eta.setAttribute('class', 'eta');
    progressItem.appendChild(eta);
  }


  var progress = progressItem.querySelector('.progress');
  progress.style.width = progressJson['_percent_str'];
  var speed = progressItem.querySelector('.speed');
  speed.textContent = progressJson['_speed_str'];
  var eta = progressItem.querySelector('.eta');
  eta.textContent = progressJson['eta'];

  if (progressJson['status'] === 'convert_finished') {
    console.log('convert finished');
    progressItem.remove();
  }
}

function insertMediaList(medias) {
  console.log(medias);
  let mediaListContainer = document.getElementById('media-list-container');

  for (let media of medias) {
    const newCheckbox = document.createElement('input');
    newCheckbox.type = 'checkbox';
    newCheckbox.name = 'media'
    newCheckbox.value = media;

    const newLabel = document.createElement('label');
    newLabel.className = 'media-label';
    // newLabel.textContent = video;
    newLabel.appendChild(newCheckbox);
    newLabel.appendChild(document.createTextNode(media));
    mediaListContainer.appendChild(newLabel);
  }


  mediaListForm = document.getElementById('media-list-form');
  const newDownButton = document.createElement('button');
  newDownButton.textContent = 'Download';
  newDownButton.id = 'download-button';
  mediaListForm.appendChild(newDownButton);
}

// 模拟进度更新
// setTimeout(() => updateProgress('progress1', 25), 1000); // 1秒后更新到25%
// setTimeout(() => updateProgress('progress2', 50), 2000); // 2秒后更新到50%
// setTimeout(() => updateProgress('progress3', 75), 3000); // 3秒后更新到75%

// // 进一步更新
// setTimeout(() => updateProgress('progress1', 50), 4000); // 4秒后更新到50%
// setTimeout(() => updateProgress('progress2', 75), 5000); // 5秒后更新到75%
// setTimeout(() => updateProgress('progress3', 100), 6000); // 6秒后更新到100%

let urlform = document.getElementById('media-url-form')
                  .addEventListener('submit', function(event) {
                    event.preventDefault();
                    const mediaUrl =
                        document.getElementById('media-url-input').value;
                    const quality = document.getElementById('quality').value;
                    const format = document.getElementById('format').value;
                    const auto = document.getElementById('auto').value;
                    fetch('add', {
                      method: 'POST',
                      mode: 'cors',
                      headers: {'Content-Type': 'application/json'},
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


const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const host = window.location.host;
const path = '/ws';

const ws_url = `${protocol}//${host}${path}`;
const socket = new WebSocket(ws_url);

// 当连接建立时触发
socket.addEventListener('open', function(event) {
  // 发送一个JSON对象
  const message = {type: 'greeting', content: 'Hello, server!'};
  socket.send(JSON.stringify(message));
});

// 当从服务器接收到消息时触发
socket.addEventListener('message', function(event) {
  // 解析接收到的JSON字符串
  const data = JSON.parse(event.data);
  console.log(data['title'], data['_percent_str'], data['eta']);
  updateProgress(data)
});

// 当连接关闭时触发
socket.addEventListener('close', function(event) {
  console.log('Connection closed');
});

// 当发生错误时触发
socket.addEventListener('error', function(event) {
  console.error('Error detected', event);
});