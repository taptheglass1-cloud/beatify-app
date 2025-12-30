import os
import time
import re
import cloudinary
import cloudinary.uploader
import cloudinary.api
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

# === CLOUDINARY CONFIG ===
# On Render, these should be set in the 'Environment' tab
cloudinary.config( 
  cloud_name = os.environ.get("CLOUD_NAME", "di0flugpd"), 
  api_key = os.environ.get("CLOUD_KEY", "255441144864455"), 
  api_secret = os.environ.get("CLOUD_SECRET", "FnxTZfzP5oZG9_FP2ivu2mw4ySw"),
  secure = True
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# === SUPABASE CONFIG ===
SUPABASE_URL = "https://zwtoztttsqamceuusvoi.supabase.co/"
SUPABASE_KEY = "sb_publishable_nxc75Aw211BgANYDwF09zQ_OFQXzGEO"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/api/data")
async def get_data():
    try:
        songs = supabase.table("songs").select("*").order("created_at", desc=True).execute()
        return {"songs": songs.data}
    except:
        return {"songs": []}

@app.post("/api/upload")
async def upload(
    album: str = Form(...), 
    user_email: str = Form(...), 
    artist_name: str = Form(...), 
    cover: UploadFile = File(None), 
    tracks: list[UploadFile] = File(...)
):
    try:
        ts = int(time.time())
        cover_url = "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?q=80&w=1000"
        
        if cover:
            c_res = cloudinary.uploader.upload(await cover.read(), folder="beatify/covers")
            cover_url = c_res.get("secure_url")

        for t in tracks:
            clean_title = re.sub(r'\\.(mp3|wav|ogg|m4a|flac)$', '', t.filename, flags=re.IGNORECASE)
            t_res = cloudinary.uploader.upload(
                await t.read(), 
                resource_type="video", 
                folder="beatify/tracks/" + user_email,
                public_id="track_" + str(ts) + "_" + t.filename.split('.')[0]
            )
            
            supabase.table("songs").insert({
                "artist": artist_name, 
                "album": album, 
                "title": clean_title, 
                "track_url": t_res.get("secure_url"), 
                "cover_url": cover_url, 
                "uploaded_by": user_email 
            }).execute()
            
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/delete_album/{album_name}")
async def delete_album(album_name: str, user_email: str):
    try:
        # Security: Only delete if the album AND uploader match
        result = supabase.table("songs").delete().eq("album", album_name).eq("uploaded_by", user_email).execute()
        return {"status": "success", "count": len(result.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Beatify | Cloud Studio</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <style>
        :root { --primary: #1DB954; --bg: #000000; --panel: #121212; --glass: rgba(255, 255, 255, 0.08); --border: rgba(255, 255, 255, 0.1); --text-dim: #b3b3b3; }
        * { box-sizing: border-box; transition: all 0.2s ease; }
        body { background: var(--bg); color: white; font-family: 'Plus Jakarta Sans', sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        .sidebar { width: 280px; background: black; padding: 24px; display: flex; flex-direction: column; gap: 8px; border-right: 1px solid var(--border); }
        .main { flex: 1; overflow-y: auto; background: linear-gradient(to bottom, #181818, #000000); padding: 40px; padding-bottom: 120px; }
        .nav-item { padding: 14px 20px; border-radius: 8px; display: flex; align-items: center; gap: 16px; color: var(--text-dim); cursor: pointer; font-weight: 700; }
        .nav-item:hover { background: var(--panel); color: white; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 24px; }
        .card { background: #181818; padding: 16px; border-radius: 12px; cursor: pointer; border: 1px solid transparent; }
        .card:hover { background: #282828; transform: translateY(-5px); }
        .card img { width: 100%; aspect-ratio: 1; border-radius: 8px; object-fit: cover; margin-bottom: 16px; box-shadow: 0 12px 30px rgba(0,0,0,0.5); }
        .player-bar { position: fixed; bottom: 0; left: 0; right: 0; height: 100px; background: black; border-top: 1px solid var(--border); display: flex; align-items: center; padding: 0 30px; z-index: 1000; }
        .p-info { width: 30%; display: flex; align-items: center; gap: 15px; }
        .p-controls { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 10px; }
        .p-vol { width: 30%; display: flex; justify-content: flex-end; align-items: center; gap: 12px; }
        input[type=range] { -webkit-appearance: none; background: transparent; cursor: pointer; }
        input[type=range]::-webkit-slider-runnable-track { background: var(--glass); height: 4px; border-radius: 2px; }
        input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; height: 12px; width: 12px; background: white; border-radius: 50%; margin-top: -4px; }
        .btn-play { background: white; color: black; width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; cursor: pointer; }
        .v-input { background: #2a2a2a; border: 1px solid var(--border); padding: 14px; border-radius: 6px; color: white; width: 100%; margin-bottom: 20px; }
        .upload-card { background: var(--panel); padding: 30px; border-radius: 16px; border: 1px solid var(--border); }
        #loader { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.9); backdrop-filter: blur(15px); z-index: 9999; flex-direction: column; align-items: center; justify-content: center; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div id="loader"><div style="width:60px;height:60px;border:5px solid var(--glass);border-top-color:var(--primary);border-radius:50%;animation:spin 1s linear infinite"></div><h2 id="l-text" style="margin-top:25px">Syncing Cloud...</h2></div>
    <div class="sidebar">
        <h2 style="padding: 0 15px; margin-bottom: 30px;"><i class="fa-brands fa-spotify" style="color:var(--primary)"></i> Beatify</h2>
        <div class="nav-item" onclick="show('home')"><i class="fa-solid fa-house"></i> Home</div>
        <div id="auth-zone"></div>
    </div>
    <div class="main" id="content"></div>
    <div class="player-bar" id="player" style="display:none">
        <div class="p-info" id="p-info"></div>
        <div class="p-controls">
            <div class="btn-play" onclick="togglePlay()"><i class="fa-solid fa-play" id="play-btn"></i></div>
            <div style="width:100%; max-width:600px; display:flex; align-items:center; gap:12px">
                <small id="cur-time">0:00</small>
                <input type="range" id="prog-range" value="0" style="flex:1" oninput="seek(this.value)">
                <small id="dur-time">0:00</small>
            </div>
        </div>
        <div class="p-vol">
            <i class="fa-solid fa-volume-high"></i>
            <input type="range" min="0" max="1" step="0.01" value="0.8" style="width:100px" oninput="setVol(this.value)">
        </div>
        <audio id="audio" ontimeupdate="updateProg()" onloadedmetadata="initDur()"></audio>
    </div>

<script>
    const _sb = supabase.createClient('https://zwtoztttsqamceuusvoi.supabase.co', 'sb_publishable_nxc75Aw211BgANYDwF09zQ_OFQXzGEO');
    let db = { songs: [] }, user = null;

    async function init() {
        const { data } = await _sb.auth.getSession();
        user = data.session?.user || null;
        await loadData();
    }

    async function loadData() {
        const r = await fetch('/api/data');
        const res = await r.json();
        db.songs = res.songs;
        renderAuth(); show('home');
    }

    function renderAuth() {
        const zone = document.getElementById('auth-zone');
        if(user) zone.innerHTML = '<div class="nav-item" onclick="show(\\'upload\\')"><i class="fa-solid fa-plus"></i> Studio</div><div class="nav-item" onclick="logout()"><i class="fa-solid fa-sign-out"></i> Logout</div>';
        else zone.innerHTML = '<div class="nav-item" onclick="show(\\'login\\')"><i class="fa-solid fa-user"></i> Login</div>';
    }

    function show(view) {
        const c = document.getElementById('content');
        if(view === 'home') {
            const albums = {};
            db.songs.forEach(s => {
                if(!albums[s.album]) albums[s.album] = { title: s.album, artist: s.artist, cover: s.cover_url, tracks: [] };
                albums[s.album].tracks.push(s);
            });
            let h = '<h1>Discovery</h1><div class="grid">';
            Object.values(albums).forEach(a => {
                h += '<div class="card" onclick="openAlbum(\\''+a.title+'\\')"><img src="'+a.cover+'"><b>'+a.title+'</b><small>'+a.artist+'</small></div>';
            });
            c.innerHTML = h + '</div>';
        } else if(view === 'upload') {
            const myAlbums = {};
            db.songs.filter(s => s.uploaded_by === user.email).forEach(s => {
                if(!myAlbums[s.album]) myAlbums[s.album] = { title: s.album, count: 0 };
                myAlbums[s.album].count++;
            });
            let h = '<div style="display:grid; grid-template-columns: 1fr 1fr; gap:30px">';
            h += '<div class="upload-card"><h2>Upload</h2><input class="v-input" id="u-alb" placeholder="Album Name"><p>Cover</p><input type="file" id="u-cov"><p>Audio</p><input type="file" id="u-tracks" multiple><button class="btn-play" style="width:100%; border-radius:8px" onclick="doUp()">Publish</button></div>';
            h += '<div class="upload-card"><h2>Your Albums</h2>';
            Object.values(myAlbums).forEach(a => {
                h += '<div style="display:flex; justify-content:space-between; margin-bottom:10px; background:var(--glass); padding:10px; border-radius:8px"><span>'+a.title+' ('+a.count+')</span><i class="fa-solid fa-trash" style="color:red; cursor:pointer" onclick="confirmDelete(\\''+a.title+'\\')"></i></div>';
            });
            c.innerHTML = h + '</div></div>';
        } else if(view === 'login') {
            c.innerHTML = '<div class="upload-card" style="max-width:400px"><h2>Login</h2><input class="v-input" id="l-em" placeholder="Email"><input class="v-input" type="password" id="l-ps" placeholder="Password"><button class="btn-play" style="width:100%; border-radius:8px" onclick="doAuth()">Continue</button></div>';
        }
    }

    function openAlbum(title) {
        const tracks = db.songs.filter(s => s.album === title);
        let h = '<div style="display:flex; gap:40px; margin-bottom:40px"><img src="'+tracks[0].cover_url+'" width="250" style="border-radius:12px"><div><h1 style="font-size:64px; margin:0">'+title+'</h1><b>'+tracks[0].artist+'</b></div></div>';
        tracks.forEach((t, i) => {
            h += '<div style="display:flex; align-items:center; padding:12px; border-radius:8px; cursor:pointer" onclick="play(\\''+t.track_url+'\\',\\''+t.title+'\\',\\''+t.artist+'\\',\\''+t.cover_url+'\\')"><span style="width:40px">'+(i+1)+'</span><div style="flex:1"><b>'+t.title+'</b></div><i class="fa-solid fa-play"></i></div>';
        });
        document.getElementById('content').innerHTML = h;
    }

    function play(url, title, artist, cover) {
        document.getElementById('player').style.display = 'flex';
        const a = document.getElementById('audio'); a.src = url; a.play();
        document.getElementById('play-btn').className = "fa-solid fa-pause";
        document.getElementById('p-info').innerHTML = '<img src="'+cover+'" width="56" height="56" style="border-radius:4px"><div><b>'+title+'</b><br><small>'+artist+'</small></div>';
    }

    function togglePlay() {
        const a = document.getElementById('audio');
        const b = document.getElementById('play-btn');
        if(a.paused) { a.play(); b.className="fa-solid fa-pause"; }
        else { a.pause(); b.className="fa-solid fa-play"; }
    }

    async function confirmDelete(name) {
        if(confirm("Delete this album?")) {
            const r = await fetch('/api/delete_album/'+encodeURIComponent(name)+'?user_email='+user.email, { method:'DELETE' });
            if(r.ok) location.reload();
        }
    }

    function setVol(v) { document.getElementById('audio').volume = v; }
    function updateProg() {
        const a = document.getElementById('audio');
        if(a.duration) { 
            document.getElementById('prog-range').value = (a.currentTime / a.duration) * 100;
            document.getElementById('cur-time').innerText = fmt(a.currentTime);
        }
    }
    function initDur() { document.getElementById('dur-time').innerText = fmt(document.getElementById('audio').duration); }
    function fmt(s) { const m = Math.floor(s/60); const sec = Math.floor(s%60); return m+":"+(sec<10?"0":"")+sec; }
    function seek(v) { const a = document.getElementById('audio'); a.currentTime = (v / 100) * a.duration; }

    async function doUp() {
        document.getElementById('loader').style.display = 'flex';
        const fd = new FormData();
        fd.append('album', document.getElementById('u-alb').value);
        fd.append('user_email', user.email);
        fd.append('artist_name', user.email.split('@')[0]);
        fd.append('cover', document.getElementById('u-cov').files[0]);
        for(let f of document.getElementById('u-tracks').files) fd.append('tracks', f);
        await fetch('/api/upload', {method:'POST', body:fd});
        location.reload();
    }

    async function doAuth() {
        const em = document.getElementById('l-em').value, ps = document.getElementById('l-ps').value;
        const { error } = await _sb.auth.signInWithPassword({ email: em, password: ps });
        if(error) await _sb.auth.signUp({ email: em, password: ps });
        location.reload();
    }

    async function logout() { await _sb.auth.signOut(); location.reload(); }
    init();
</script>
</body>
</html>
"""
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(app, host="0.0.0.0", port=port)
