import os
import re
import subprocess
import tempfile
from pathlib import Path
from collections import defaultdict
from flask import Flask, request, jsonify, send_file, Response

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

IMAGE_EXTENSIONS = {'.bmp', '.jpg', '.jpeg', '.png'}

HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SEQ VIEWER</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow+Condensed:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
  :root { --bg:#0d0e11;--panel:#13151a;--border:#2a2d35;--accent:#e8ff47;--accent2:#47c4ff;--danger:#ff5047;--text:#d4d8e0;--muted:#5a5f70;--mono:'Share Tech Mono',monospace;--sans:'Barlow Condensed',sans-serif; }
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  html,body{height:100%;background:var(--bg);color:var(--text);font-family:var(--sans);font-size:14px;overflow:hidden}
  #app{display:grid;grid-template-rows:46px 1fr 180px;height:100vh}
  #topbar{display:flex;align-items:center;gap:12px;padding:0 16px;border-bottom:1px solid var(--border);background:var(--panel)}
  .logo{font-family:var(--mono);font-size:16px;letter-spacing:4px;color:var(--accent);white-space:nowrap;text-shadow:0 0 20px rgba(232,255,71,0.4)}
  .sep{width:1px;height:24px;background:var(--border)}
  #dir-input{flex:1;background:var(--bg);border:1px solid var(--border);color:var(--text);font-family:var(--mono);font-size:12px;padding:6px 10px;outline:none;transition:border-color 0.2s}
  #dir-input:focus{border-color:var(--accent)}
  #dir-input::placeholder{color:var(--muted)}
  .btn{font-family:var(--sans);font-weight:700;font-size:12px;letter-spacing:1.5px;text-transform:uppercase;padding:6px 14px;border:1px solid var(--border);background:transparent;color:var(--text);cursor:pointer;transition:all 0.15s;white-space:nowrap}
  .btn:hover{border-color:var(--accent);color:var(--accent)}
  .btn.primary{border-color:var(--accent);color:var(--accent)}
  .btn.primary:hover{background:var(--accent);color:var(--bg)}
  .btn:disabled{opacity:0.3;cursor:not-allowed}
  #viewer{position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden;background:#080909}
  #canvas-container{position:relative;width:100%;height:100%;display:flex;align-items:center;justify-content:center}
  #main-img{max-width:100%;max-height:100%;object-fit:contain;display:none}
  #placeholder{display:flex;flex-direction:column;align-items:center;gap:16px;color:var(--muted)}
  .placeholder-icon{font-size:64px;opacity:0.3;font-family:var(--mono);letter-spacing:-4px}
  .placeholder-text{font-family:var(--mono);font-size:12px;letter-spacing:2px}
  #hud{position:absolute;top:10px;left:10px;font-family:var(--mono);font-size:11px;color:rgba(232,255,71,0.8);background:rgba(0,0,0,0.6);padding:6px 10px;pointer-events:none;line-height:1.8;display:none}
  #live-dot{position:absolute;top:10px;right:10px;display:none;align-items:center;gap:6px;font-family:var(--mono);font-size:10px;color:var(--accent2);background:rgba(0,0,0,0.6);padding:4px 8px}
  #live-dot.active{display:flex}
  .dot{width:6px;height:6px;border-radius:50%;background:var(--accent2);animation:pulse 1.5s ease-in-out infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.2}}
  #controls{background:var(--panel);border-top:1px solid var(--border);display:grid;grid-template-rows:1fr 1fr 1fr}
  .ctrl-row{display:flex;align-items:center;gap:10px;padding:0 16px;border-bottom:1px solid var(--border)}
  .ctrl-row:last-child{border-bottom:none}
  #slider-row{gap:12px}
  #frame-label{font-family:var(--mono);font-size:11px;color:var(--muted);min-width:80px}
  #frame-slider{flex:1;-webkit-appearance:none;height:3px;background:var(--border);outline:none;cursor:pointer}
  #frame-slider::-webkit-slider-thumb{-webkit-appearance:none;width:14px;height:14px;border-radius:0;background:var(--accent);cursor:pointer}
  #frame-slider::-moz-range-thumb{width:14px;height:14px;border-radius:0;background:var(--accent);border:none;cursor:pointer}
  #frame-num-display{font-family:var(--mono);font-size:12px;color:var(--accent);min-width:90px;text-align:right}
  #play-row{gap:8px}
  .ctrl-label{font-family:var(--mono);font-size:10px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;white-space:nowrap}
  .btn-icon{width:34px;height:30px;font-size:14px;padding:0;display:flex;align-items:center;justify-content:center;border:1px solid var(--border);background:transparent;color:var(--text);cursor:pointer;transition:all 0.15s;font-family:var(--mono)}
  .btn-icon:hover{border-color:var(--accent);color:var(--accent)}
  .btn-icon.active{border-color:var(--accent);background:var(--accent);color:var(--bg)}
  .btn-icon:disabled{opacity:0.3;cursor:not-allowed}
  #fps-input{width:50px;background:var(--bg);border:1px solid var(--border);color:var(--accent);font-family:var(--mono);font-size:12px;padding:4px 6px;text-align:center;outline:none}
  #fps-input:focus{border-color:var(--accent)}
  .divider-v{width:1px;height:20px;background:var(--border);margin:0 4px}
  #status-row{display:flex;align-items:center;gap:16px;padding:0 16px}
  #status-msg{font-family:var(--mono);font-size:11px;color:var(--muted);flex:1}
  #status-msg.error{color:var(--danger)}
  #status-msg.ok{color:var(--accent2)}
  #convert-panel{display:none;align-items:center;gap:10px}
  #convert-panel.visible{display:flex}
  #output-name-input,#convert-fps-input{background:var(--bg);border:1px solid var(--border);color:var(--text);font-family:var(--mono);font-size:11px;padding:4px 8px;outline:none}
  #output-name-input{width:140px}
  #convert-fps-input{width:50px;text-align:center;color:var(--accent)}
  #output-name-input:focus,#convert-fps-input:focus{border-color:var(--accent)}
  select.ctrl-select{background:var(--bg);border:1px solid var(--border);color:var(--text);font-family:var(--mono);font-size:11px;padding:4px 8px;outline:none;cursor:pointer}
  #notif{position:absolute;top:50px;right:16px;font-family:var(--mono);font-size:11px;padding:8px 14px;border-left:3px solid var(--accent2);background:rgba(13,14,17,0.95);color:var(--text);display:none;max-width:300px;z-index:100}
</style>
</head>
<body>
<div id="app">
  <div id="topbar">
    <span class="logo">SEQ</span>
    <div class="sep"></div>
    <input id="dir-input" type="text" placeholder="画像ディレクトリのパスを入力 (例: C:\images\seq)">
    <button class="btn primary" id="btn-load">LOAD</button>
    <div class="sep"></div>
    <button class="btn" id="btn-convert-toggle">VIDEO</button>
  </div>
  <div id="viewer">
    <div id="canvas-container">
      <img id="main-img" alt="frame">
      <div id="placeholder">
        <div class="placeholder-icon">▤▤▤</div>
        <div class="placeholder-text">LOAD A DIRECTORY TO BEGIN</div>
      </div>
    </div>
    <div id="hud"></div>
    <div id="live-dot"><div class="dot"></div>LIVE</div>
    <div id="notif"></div>
  </div>
  <div id="controls">
    <div class="ctrl-row" id="slider-row">
      <span class="ctrl-label">FRAME</span>
      <span id="frame-label">— / —</span>
      <input type="range" id="frame-slider" min="0" max="0" value="0" disabled>
      <span id="frame-num-display">—</span>
    </div>
    <div class="ctrl-row" id="play-row">
      <span class="ctrl-label">PLAY</span>
      <button class="btn-icon" id="btn-first" title="先頭へ" disabled>⏮</button>
      <button class="btn-icon" id="btn-prev" title="前のコマ" disabled>◀</button>
      <button class="btn-icon" id="btn-play" title="再生/停止" disabled>▶</button>
      <button class="btn-icon" id="btn-next" title="次のコマ" disabled>▶|</button>
      <button class="btn-icon" id="btn-last" title="最後へ" disabled>⏭</button>
      <div class="divider-v"></div>
      <span class="ctrl-label">FPS</span>
      <input type="number" id="fps-input" value="12" min="1" max="120">
      <div class="divider-v"></div>
      <span class="ctrl-label">LOOP</span>
      <button class="btn-icon" id="btn-loop">∞</button>
      <div class="divider-v"></div>
      <div id="convert-panel">
        <span class="ctrl-label">OUT</span>
        <input type="text" id="output-name-input" placeholder="output_filename">
        <select class="ctrl-select" id="fmt-select">
          <option value="mp4">MP4</option>
          <option value="gif">GIF</option>
          <option value="webm">WEBM</option>
        </select>
        <span class="ctrl-label">FPS</span>
        <input type="number" id="convert-fps-input" value="24" min="1" max="60">
        <button class="btn primary" id="btn-do-convert" disabled>CONVERT</button>
      </div>
    </div>
    <div class="ctrl-row" id="status-row">
      <span id="status-msg">Ready.</span>
    </div>
  </div>
</div>
<script>
const state={directory:'',files:[],currentIndex:0,playing:false,looping:true,fps:12,timer:null,refreshTimer:null,mtimes:{}};
const $=id=>document.getElementById(id);
const dirInput=$('dir-input'),btnLoad=$('btn-load'),mainImg=$('main-img'),placeholder=$('placeholder');
const hud=$('hud'),liveDot=$('live-dot'),notif=$('notif');
const frameSlider=$('frame-slider'),frameLabel=$('frame-label'),frameNumDisplay=$('frame-num-display');
const btnFirst=$('btn-first'),btnPrev=$('btn-prev'),btnPlay=$('btn-play'),btnNext=$('btn-next'),btnLast=$('btn-last'),btnLoop=$('btn-loop');
const fpsInput=$('fps-input'),statusMsg=$('status-msg');
const btnConvertToggle=$('btn-convert-toggle'),convertPanel=$('convert-panel');
const outputNameInput=$('output-name-input'),fmtSelect=$('fmt-select'),convertFpsInput=$('convert-fps-input'),btnDoConvert=$('btn-do-convert');

function setStatus(msg,type=''){statusMsg.textContent=msg;statusMsg.className=type}
let notifTimer;
function showNotif(msg){notif.textContent=msg;notif.style.display='block';clearTimeout(notifTimer);notifTimer=setTimeout(()=>{notif.style.display='none'},3000)}

function showFrame(index){
  if(!state.files.length)return;
  index=Math.max(0,Math.min(index,state.files.length-1));
  state.currentIndex=index;
  const f=state.files[index];
  mainImg.src='/api/image?path='+encodeURIComponent(f.path)+'&t='+Date.now();
  mainImg.style.display='block';placeholder.style.display='none';
  frameSlider.value=index;
  frameLabel.textContent=(index+1)+' / '+state.files.length;
  frameNumDisplay.textContent='#'+f.num;
  hud.style.display='block';
  hud.innerHTML='FILE  '+f.filename+'<br>IDX   '+(index+1)+' / '+state.files.length+'<br>NUM   '+f.num;
}

function updateControls(){
  const has=state.files.length>0;
  [frameSlider,btnFirst,btnPrev,btnPlay,btnNext,btnLast,btnDoConvert].forEach(el=>el.disabled=!has);
  if(has)frameSlider.max=state.files.length-1;
}

async function loadDirectory(){
  const dir=dirInput.value.trim();
  if(!dir){setStatus('ディレクトリを入力してください','error');return}
  setStatus('スキャン中...');stopPlayback();
  try{
    const res=await fetch('/api/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({directory:dir})});
    const data=await res.json();
    if(data.error){setStatus(data.error,'error');return}
    state.directory=dir;state.files=data.files;state.currentIndex=0;
    state.mtimes=Object.fromEntries(data.files.map(f=>[f.filename,f.mtime]));
    frameSlider.max=data.files.length-1;frameSlider.value=0;
    updateControls();showFrame(0);
    setStatus('Loaded: '+data.files.length+' frames — prefix "'+data.prefix+'"','ok');
    startLiveRefresh();
    outputNameInput.value=(data.prefix||'output').replace(/[\W_]+$/,'')||'output';
  }catch(e){setStatus('通信エラー: '+e.message,'error')}
}

function startPlayback(){
  if(state.playing)return;
  state.playing=true;btnPlay.classList.add('active');btnPlay.textContent='⏸';
  function tick(){
    if(!state.playing)return;
    let next=state.currentIndex+1;
    if(next>=state.files.length){if(state.looping)next=0;else{stopPlayback();return}}
    showFrame(next);state.timer=setTimeout(tick,1000/state.fps);
  }
  state.timer=setTimeout(tick,1000/state.fps);
}
function stopPlayback(){
  state.playing=false;btnPlay.classList.remove('active');btnPlay.textContent='▶';
  if(state.timer){clearTimeout(state.timer);state.timer=null}
}
function togglePlayback(){if(state.playing)stopPlayback();else startPlayback()}

function startLiveRefresh(){
  if(state.refreshTimer)clearInterval(state.refreshTimer);
  liveDot.classList.add('active');
  state.refreshTimer=setInterval(async()=>{
    if(!state.directory)return;
    try{
      const res=await fetch('/api/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({directory:state.directory,mtimes:state.mtimes})});
      const data=await res.json();
      if(data.error||!data.changed)return;
      const wasPlaying=state.playing,prevIndex=state.currentIndex,prevTotal=state.files.length;
      state.files=data.files;state.mtimes=Object.fromEntries(data.files.map(f=>[f.filename,f.mtime]));
      frameSlider.max=data.files.length-1;updateControls();
      if(data.files.length!==prevTotal){showNotif('ファイル更新: '+data.files.length+' フレーム');setStatus(data.files.length+' frames (updated)','ok')}
      if(!wasPlaying)showFrame(Math.min(prevIndex,data.files.length-1));
    }catch(e){}
  },2000);
}

btnLoad.addEventListener('click',loadDirectory);
dirInput.addEventListener('keydown',e=>{if(e.key==='Enter')loadDirectory()});
frameSlider.addEventListener('input',()=>{stopPlayback();showFrame(parseInt(frameSlider.value))});
btnFirst.addEventListener('click',()=>{stopPlayback();showFrame(0)});
btnLast.addEventListener('click',()=>{stopPlayback();showFrame(state.files.length-1)});
btnPrev.addEventListener('click',()=>{stopPlayback();showFrame(Math.max(0,state.currentIndex-1))});
btnNext.addEventListener('click',()=>{stopPlayback();showFrame(Math.min(state.files.length-1,state.currentIndex+1))});
btnPlay.addEventListener('click',togglePlayback);
btnLoop.addEventListener('click',()=>{state.looping=!state.looping;btnLoop.classList.toggle('active',state.looping)});
btnLoop.classList.add('active');
fpsInput.addEventListener('change',()=>{const v=parseInt(fpsInput.value);if(v>=1&&v<=120){state.fps=v;if(state.playing){stopPlayback();startPlayback()}}});
window.addEventListener('keydown',e=>{
  if([dirInput,outputNameInput,fpsInput,convertFpsInput].includes(e.target))return;
  if(e.key==='ArrowLeft'||e.key===','){stopPlayback();showFrame(Math.max(0,state.currentIndex-1))}
  else if(e.key==='ArrowRight'||e.key==='.'){stopPlayback();showFrame(Math.min(state.files.length-1,state.currentIndex+1))}
  else if(e.key===' '){e.preventDefault();togglePlayback()}
  else if(e.key==='Home'){stopPlayback();showFrame(0)}
  else if(e.key==='End'){stopPlayback();showFrame(state.files.length-1)}
});
btnConvertToggle.addEventListener('click',()=>{
  convertPanel.classList.toggle('visible');
  btnConvertToggle.classList.toggle('primary',convertPanel.classList.contains('visible'));
});
btnDoConvert.addEventListener('click',async()=>{
  const outputName=outputNameInput.value.trim()||'output',fmt=fmtSelect.value,fps=parseInt(convertFpsInput.value)||24;
  setStatus('変換中... ('+fmt.toUpperCase()+', '+fps+'fps)');btnDoConvert.disabled=true;
  try{
    const res=await fetch('/api/convert_video',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({directory:state.directory,fps,format:fmt,output_name:outputName})});
    const data=await res.json();
    if(data.error)setStatus('変換エラー: '+data.error,'error');
    else{setStatus('変換完了: '+data.output_path,'ok');showNotif('✓ 出力: '+outputName+'.'+fmt)}
  }catch(e){setStatus('通信エラー: '+e.message,'error')}
  btnDoConvert.disabled=false;
});
</script>
</body>
</html>"""


def scan_directory(directory):
    if not os.path.isdir(directory):
        return {'error': 'ディレクトリが見つかりません: ' + directory}
    files = []
    for f in os.listdir(directory):
        ext = Path(f).suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            m = re.search(r'(\d+)$', Path(f).stem)
            if m:
                full = os.path.join(directory, f)
                files.append({'filename': f, 'path': full, 'num': int(m.group(1)), 'mtime': os.path.getmtime(full)})
    if not files:
        return {'error': '連番画像が見つかりません (bmp/jpg/png)'}
    def prefix(e): return re.sub(r'[\W_]*\d+$', '', Path(e['filename']).stem)
    groups = defaultdict(list)
    for f in files: groups[prefix(f)].append(f)
    grp = max(groups.values(), key=len)
    grp.sort(key=lambda x: x['num'])
    return {'prefix': prefix(grp[0]),
            'files': [{'filename': f['filename'], 'path': f['path'], 'num': f['num'], 'mtime': f['mtime']} for f in grp],
            'total': len(grp)}


@app.route('/')
def index():
    return HTML, 200, {'Content-Type': 'text/html; charset=utf-8'}

@app.route('/api/scan', methods=['POST'])
def scan():
    d = request.json.get('directory', '').strip()
    if not d: return jsonify({'error': 'ディレクトリを指定してください'})
    return jsonify(scan_directory(d))

@app.route('/api/refresh', methods=['POST'])
def refresh():
    d = request.json.get('directory', '').strip()
    known = request.json.get('mtimes', {})
    if not d: return jsonify({'error': 'No directory'})
    result = scan_directory(d)
    if 'error' in result: return jsonify(result)
    result['changed'] = ({f['filename']: f['mtime'] for f in result['files']} != known)
    return jsonify(result)

@app.route('/api/image')
def get_image():
    path = request.args.get('path', '')
    if not path or not os.path.isfile(path): return Response('Not found', status=404)
    mime = {'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.bmp':'image/bmp'}
    return send_file(path, mimetype=mime.get(Path(path).suffix.lower(), 'image/jpeg'))

@app.route('/api/convert_video', methods=['POST'])
def convert_video():
    data = request.json
    directory = data.get('directory', '').strip()
    fps = int(data.get('fps', 24))
    fmt = data.get('format', 'mp4')
    output_name = data.get('output_name', 'output').strip() or 'output'
    result = scan_directory(directory)
    if 'error' in result: return jsonify({'error': result['error']})
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except:
        return jsonify({'error': 'ffmpeg が見つかりません'})
    files = result['files']
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp:
        for f in files:
            tmp.write("file '{}'\nduration {}\n".format(f['path'], 1.0/fps))
        tmp.write("file '{}'\n".format(files[-1]['path']))
        list_file = tmp.name
    output_path = os.path.join(directory, '{}.{}'.format(output_name, fmt))
    try:
        cmds = {
            'mp4': ['ffmpeg','-y','-f','concat','-safe','0','-i',list_file,'-vf','scale=trunc(iw/2)*2:trunc(ih/2)*2','-c:v','libx264','-pix_fmt','yuv420p','-r',str(fps),output_path],
            'gif': ['ffmpeg','-y','-f','concat','-safe','0','-i',list_file,'-vf','fps={},scale=320:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse'.format(fps),output_path],
            'webm': ['ffmpeg','-y','-f','concat','-safe','0','-i',list_file,'-c:v','libvpx-vp9','-r',str(fps),output_path],
        }
        if fmt not in cmds: os.unlink(list_file); return jsonify({'error': '非対応フォーマット'})
        proc = subprocess.run(cmds[fmt], capture_output=True, text=True, timeout=300)
        os.unlink(list_file)
        if proc.returncode != 0: return jsonify({'error': 'ffmpeg error: ' + proc.stderr[-300:]})
        return jsonify({'success': True, 'output_path': output_path})
    except subprocess.TimeoutExpired:
        if os.path.exists(list_file): os.unlink(list_file)
        return jsonify({'error': 'タイムアウト'})
    except Exception as e:
        if os.path.exists(list_file): os.unlink(list_file)
        return jsonify({'error': str(e)})


if __name__ == '__main__':
    print("=" * 50)
    print("  Sequential Image Viewer")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(debug=False, host='0.0.0.0', port=5000)
