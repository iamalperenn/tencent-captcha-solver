import logging
import os
import re
import json
import random
import base64
import tempfile
import urllib.parse
import cv2
import threading
import time
from curl_cffi import requests
from ultralytics import YOLO
from colorama import Fore, Style, init
from flask import Flask, jsonify
from flask_cors import CORS

MODEL_PATH = "./model/best.pt"

init(autoreset=True)
logger = logging.getLogger("tcaptcha")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('{asctime} | {levelname:<8s} | {message}', style='{'))
logger.addHandler(handler)

def log_info(msg): logger.info(Fore.GREEN + msg)
def log_warn(msg): logger.warning(Fore.YELLOW + msg)
def log_err(msg): logger.error(Fore.RED + msg)
def log_debug(msg): logger.debug(Fore.CYAN + msg)

app = Flask(__name__)
CORS(app)
session = requests.Session()
model = YOLO(MODEL_PATH)
model_lock = threading.Lock()

headers = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Host": "t-captcha.gjacky.com",
    "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-S9210 Build/PQ3B.190801.10101846; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/95.0.4638.74 Mobile Safari/537.36",
    "X-Requested-With": "com.tencent.ig"
}

def get_captcha_params():
    cb = f"_aq_{random.randint(100000,999999)}"
    ua = base64.b64encode(headers["User-Agent"].encode()).decode()
    return {
        "aid":2033864629,"protocol":"https","accver":1,"showtype":"popup","ua":ua,"noheader":0,
        "fb":0,"aged":0,"enableAged":0,"enableDarkMode":0,"sid":"16509146463833173100",
        "grayscale":1,"dyeid":0,"clientype":1,"cap_cd":"","uid":"91cb51ce636b271c402dcaf739ddc9eb",
        "lang":"tr","entry_url":"file:///android_asset/iMSDKWebVerify.html","elder_captcha":0,
        "js":"/tcaptcha-frame.b230d84b.js","login_appid":"","wb":1,"version":"1.1.0",
        "subsid":1,"callback":cb,"sess":""
    }

def parse_response(text):
    m = re.match(r'_aq_(\d+)\((.*)\)', text)
    return (m.group(1), json.loads(m.group(2))) if m else (None, None)

def download_image(url, path):
    full = f"https://t-captcha.gjacky.com{url}" if url.startswith("/") else url
    r = session.get(full, headers=headers, timeout=20)
    r.raise_for_status()
    with open(path, 'wb') as f:
        f.write(r.content)

def detect_objects(path, conf=0.3):
    img = cv2.imread(path)
    if img is None:
        return []
    with model_lock:
        res = model.predict(img, conf=conf, verbose=False)
    det = []
    for box in res[0].boxes:
        x1,y1,x2,y2 = box.xyxy[0].cpu().numpy()
        cls = int(box.cls[0].cpu().numpy())
        cx,cy = int((x1+x2)/2), int((y1+y2)/2)
        det.append({'name': model.names[cls], 'x': cx, 'y': cy})
    det.sort(key=lambda d: d['x'])
    return det

def generate_collect_data():
    return "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"

def verify_captcha(data, coords):
    ans = [{"elem_id":i+1,"type":"DynAnswerType_POS","data":f"{c['x']},{c['y']}"} for i,c in enumerate(coords)]
    payload = {
        "collect":generate_collect_data(),
        "tlg":"1772",
        "eks":"JzR9rnp/8FZsUBz0oTdnHkbv8uit7+J4hLE3Riqr0TVqR5h/vkdAhIWfKnltqZlyFSEspbbmj2bpR/v3ti3ToYDMgsuc2WEAiI74nSA3T5QP0X7swyU1sFBZDc8iM6qjV2HZ52CZhCoXHVSZT0wqK4uFBUq/AgCeWepBdIyyBEeDAtM0avtlcNfACb6WEAQ19KP61tL4ugdR14QwVwQhGRYGCFqt6LeRXD/0JcGwGwjvCBv825Ebgg==",
        "sess":data.get('sess',''),
        "ans":json.dumps(ans)
    }
    h = {
        "user-agent":headers["User-Agent"],
        "content-type":"application/x-www-form-urlencoded; charset=UTF-8",
        "origin":"https://global.captcha.gtimg.com",
        "x-requested-with":"com.tencent.ig",
        "referer":"https://global.captcha.gtimg.com/"
    }
    r = session.post("https://t-captcha.gjacky.com/cap_union_new_verify", data=payload, headers=h, timeout=20)
    r.raise_for_status()
    try:
        result = r.json()
    except Exception as e:
        log_err(f"verify parse error: {e}")
        return None
    if result.get("errorCode") == "0" and result.get("ticket"):
        log_info(Fore.CYAN + f"Captcha Solved | Token: {result['ticket']}")
    else:
        log_warn("Captcha solver failed")
        logger.debug(json.dumps(result, ensure_ascii=False, indent=2))
    return result

def solve_once(data):
    d = data.get('data',{}).get('dyn_show_info',{})
    s = d.get('sprite_url','')
    b = d.get('bg_elem_cfg',{}).get('img_url','')
    if not (s and b):
        log_warn("sprite or bg not found")
        return {"qcaptcha": None, "success": False}
    tmp = tempfile.mkdtemp()
    sprite = os.path.join(tmp, "sprite.png")
    bg = os.path.join(tmp, "bg.png")
    try:
        t1 = threading.Thread(target=download_image, args=(s, sprite))
        t2 = threading.Thread(target=download_image, args=(b, bg))
        t1.start(); t2.start()
        t1.join(); t2.join()
        sprites = detect_objects(sprite)
        bgs = detect_objects(bg)
        coords = []
        for sdet in sprites:
            match = next((bdet for bdet in bgs if bdet['name'] == sdet['name']), None)
            if match:
                coords.append({'name': sdet['name'], 'x': match['x'], 'y': match['y']})
        if not coords:
            log_warn("No coordinates found")
            return {"qcaptcha": None, "success": False}
        result = verify_captcha(data, coords)
        if result:
            success = result.get("errorCode") == "0" and result.get("ticket") is not None
            return {"qcaptcha": result, "success": success}
        else:
            return {"qcaptcha": None, "success": False}
    except Exception as e:
        log_err(f"solve_once error: {e}")
        return {"qcaptcha": None, "success": False}
    finally:
        for f in (sprite, bg):
            try:
                if os.path.exists(f): os.remove(f)
            except: pass
        try:
            os.rmdir(tmp)
        except: pass

@app.route('/solve', methods=['GET'])
def solve_captcha():
    try:
        log_info("Solving captcha...")
        params = get_captcha_params()
        url = f"https://t-captcha.gjacky.com/cap_union_prehandle?{urllib.parse.urlencode(params)}"
        r = session.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        _, data = parse_response(r.text)
        if not data:
            log_warn("Parse error in prehandle")
            return jsonify({"qcaptcha": None, "success": False})
        result = solve_once(data)
        return jsonify(result)
    except requests.RequestException as e:
        log_err(f"Network error: {e}")
        return jsonify({"qcaptcha": None, "success": False})
    except Exception as e:
        log_err(f"Error: {e}")
        return jsonify({"qcaptcha": None, "success": False})

if __name__ == "__main__":
    log_info("Starting CAPTCHA Solver API...")
    app.run(host='0.0.0.0', port=5000, debug=False)
