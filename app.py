import os
import glob as _glob

# Ensure winget-installed FFmpeg is on PATH for Whisper + FFmpeg render
_localappdata = os.environ.get('LOCALAPPDATA', '')
_ff_pattern   = os.path.join(_localappdata, r'Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin')
for _ff_bin in _glob.glob(_ff_pattern):
    if os.path.exists(os.path.join(_ff_bin, 'ffmpeg.exe')):
        os.environ['PATH'] = _ff_bin + ';' + os.environ.get('PATH', '')
        break

from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import json, threading, queue, uuid

app = Flask(__name__)

_queues: dict = {}

os.makedirs('output', exist_ok=True)
os.makedirs('data', exist_ok=True)

HISTORY_FILE = 'data/history.json'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/generate', methods=['POST'])
def generate():
    from pipeline import runner
    config = request.get_json(force=True) or {}
    job_id = uuid.uuid4().hex[:8]
    q: queue.Queue = queue.Queue()
    _queues[job_id] = q
    threading.Thread(target=runner.run, args=(config, q), daemon=True).start()
    return jsonify({'job_id': job_id})


@app.route('/api/stream/<job_id>')
def stream(job_id):
    def events():
        q = _queues.get(job_id)
        if not q:
            yield f'data: {json.dumps({"type":"error","message":"Job not found"})}\n\n'
            return
        try:
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield f'data: {json.dumps(msg)}\n\n'
                    if msg.get('type') in ('done', 'error'):
                        _queues.pop(job_id, None)
                        return
                except queue.Empty:
                    yield 'data: {"type":"heartbeat"}\n\n'
        except GeneratorExit:
            _queues.pop(job_id, None)

    return Response(
        stream_with_context(events()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@app.route('/api/history')
def get_history():
    if not os.path.exists(HISTORY_FILE):
        return jsonify([])
    with open(HISTORY_FILE) as f:
        return jsonify(json.load(f))


@app.route('/api/history', methods=['DELETE'])
def clear_history():
    with open(HISTORY_FILE, 'w') as f:
        json.dump([], f)
    return jsonify({'ok': True})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port, use_reloader=False, threaded=True)
