import json
import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>B站字幕提取</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:-apple-system,sans-serif;background:linear-gradient(135deg,#00a1d6,#00609c);min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}
    .container{background:#fff;border-radius:16px;padding:40px;max-width:600px;width:100%;box-shadow:0 20px 60px rgba(0,0,0,0.3)}
    h1{text-align:center;color:#00a1d6;margin-bottom:30px}
    .input-group{display:flex;gap:10px;margin-bottom:20px}
    input{flex:1;padding:12px;border:2px solid #ddd;border-radius:8px;font-size:16px}
    input:focus{border-color:#00a1d6;outline:none}
    button{padding:12px 24px;background:#00a1d6;color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer}
    button:hover{background:#0088c6}
    .result{margin-top:20px;padding:20px;background:#f5f5f5;border-radius:8px;display:none}
    .result h3{color:#333;margin-bottom:10px;font-size:16px}
    .result pre{white-space:pre-wrap;word-break:break-all;font-size:14px;line-height:1.6;max-height:400px;overflow-y:auto;background:#fff;padding:15px;border-radius:8px}
    .error{color:#e74c3c;text-align:center;margin-top:20px;display:none}
    .loading{text-align:center;display:none;margin-top:20px;color:#666}
  </style>
</head>
<body>
  <div class="container">
    <h1>B站字幕提取</h1>
    <div class="input-group">
      <input type="text" id="bvid" placeholder="输入BV号，如 BV1DQ7k6JE4P">
      <button onclick="fetchSubtitle()">提取</button>
    </div>
    <div class="loading" id="loading">正在提取...</div>
    <div class="error" id="error"></div>
    <div class="result" id="result">
      <h3 id="title"></h3>
      <pre id="subtitle"></pre>
    </div>
  </div>
  <script>
    async function fetchSubtitle() {
      var bvid = document.getElementById('bvid').value.trim();
      if (!bvid) { alert('请输入BV号'); return; }
      document.getElementById('loading').style.display = 'block';
      document.getElementById('error').style.display = 'none';
      document.getElementById('result').style.display = 'none';
      try {
        var res = await fetch('/api/video?bvid=' + encodeURIComponent(bvid));
        var data = await res.json();
        if (data.error) { throw new Error(data.error); }
        document.getElementById('title').textContent = data.data.title + ' - ' + data.data.author;
        document.getElementById('subtitle').textContent = data.data.subtitle;
        document.getElementById('result').style.display = 'block';
      } catch (e) {
        document.getElementById('error').textContent = '错误: ' + e.message;
        document.getElementById('error').style.display = 'block';
      }
      document.getElementById('loading').style.display = 'none';
    }
    document.getElementById('bvid').addEventListener('keypress', function(e) {
      if (e.key === 'Enter') fetchSubtitle();
    });
  </script>
</body>
</html>
'''


def get_bilibili_subtitle(bvid):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.bilibili.com/'
    }
    
    video_url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
    video_res = requests.get(video_url, headers=headers)
    video_data = video_res.json()
    
    if video_data['code'] != 0:
        return {'error': '视频不存在或BV号错误'}
    
    cid = video_data['data']['cid']
    aid = video_data['data']['aid']
    title = video_data['data']['title']
    author = video_data['data']['owner']['name']
    
    dm_url = f'https://api.bilibili.com/x/v2/dm/view?aid={aid}&type=1&oid={cid}'
    dm_res = requests.get(dm_url, headers=headers)
    dm_data = dm_res.json()
    
    subtitles = dm_data.get('data', {}).get('subtitle', {}).get('subtitles', [])
    
    if not subtitles:
        return {
            'success': True,
            'data': {
                'title': title,
                'author': author,
                'subtitle': '该视频没有字幕',
                'hasSubtitle': False
            }
        }
    
    subtitle = subtitles[0]
    for s in subtitles:
        if s['lan'] == 'ai-zh':
            subtitle = s
            break
    
    sub_url = subtitle['subtitle_url']
    if sub_url.startswith('//'):
        sub_url = 'https:' + sub_url
    if sub_url.startswith('http://'):
        sub_url = sub_url.replace('http://', 'https://')
    
    content_res = requests.get(sub_url)
    content_data = content_res.json()
    
    subtitle_text = '\n'.join([line['content'] for line in content_data['body']])
    
    return {
        'success': True,
        'data': {
            'title': title,
            'author': author,
            'subtitle': subtitle_text,
            'hasSubtitle': True
        }
    }


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/video')
def api_video():
    bvid = request.args.get('bvid', '')
    if not bvid:
        return jsonify({'error': '请提供 bvid 参数'})
    
    result = get_bilibili_subtitle(bvid)
    return jsonify(result)


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
