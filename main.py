import os
import time
import re
import cloudinary
import cloudinary.uploader
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

# === CONFIGURATION ===
CLOUDINARY_NAME = os.environ.get("CLOUD_NAME", "di0flugpd")
CLOUDINARY_KEY = os.environ.get("CLOUD_KEY", "255441144864455")
CLOUDINARY_SECRET = os.environ.get("CLOUD_SECRET", "FnxTZfzP5oZG9_FP2ivu2mw4ySw")

cloudinary.config(cloud_name=CLOUDINARY_NAME, api_key=CLOUDINARY_KEY, api_secret=CLOUDINARY_SECRET, secure=True)

SUPABASE_URL = "https://zwtoztttsqamceuusvoi.supabase.co/"
SUPABASE_KEY = "sb_publishable_nxc75Aw211BgANYDwF09zQ_OFQXzGEO"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/data")
async def get_data():
    try:
        songs = supabase.table("songs").select("*").order("created_at", desc=True).execute()
        return {"songs": songs.data}
    except Exception as e:
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
        # Default cover if none provided
        cover_url = "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?q=80&w=1000"
        
        if cover and cover.filename:
            c_res = cloudinary.uploader.upload(await cover.read(), folder="beatify/covers")
            cover_url = c_res.get("secure_url")

        for t in tracks:
            if not t.filename: continue
            clean_title = re.sub(r'\.(mp3|wav|ogg|m4a|flac)$', '', t.filename, flags=re.IGNORECASE)
            
            # CRITICAL FIX: resource_type="auto" allows Cloudinary to detect Audio/MP3 correctly
            t_res = cloudinary.uploader.upload(await t.read(), resource_type="auto", folder=f"beatify/tracks/{user_email}")
            
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
        print(f"UPLOAD ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/delete_song/{id}")
async def delete_song(id: int, user_email: str):
    supabase.table("songs").delete().eq("id", id).eq("uploaded_by", user_email).execute()
    return {"status": "success"}

@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Beatify | Studio</title>
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
        .nav-item:hover, .nav-item.active { background: var(--panel); color: white; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 24px; }
        .card { background: #181818; padding: 16px; border-radius: 12px; cursor: pointer; border: 1px solid transparent; }
        .card:hover { background: #282828; transform: translateY(-5px); border-color: var(--border); }
        .card img { width: 100%; aspect-ratio: 1; border-radius: 8px; object-fit: cover; margin-bottom: 16px; }
        .player-bar { position: fixed; bottom: 0; left: 0; right: 0; height: 100px; background: black; border-top: 1px solid var(--border); display: flex; align-items: center; padding: 0 30px; z-index: 1000; }
        .p-info { width: 30%; display: flex; align-items: center; gap: 15px; }
        .p-controls { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 10px; }
        .p-vol { width: 30%; display: flex; justify-content: flex-end; align-items: center; gap: 12px; }
        input[type=range] { -webkit-appearance: none; background: transparent; cursor: pointer; }
        input[type=range]::-webkit-slider-runnable-track { background: var(--glass); height: 4px; border-radius: 2px; }
        input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; height: 12px; width: 12px; background: white; border-radius: 50%; margin-top: -4px; }
        .btn-play { background: white; color: black; width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; cursor: pointer; }
        .v-input { background: #2a2a2a; border: 1px solid var(--border); padding: 14px; border-radius: 6px; color: white; width: 100%; margin-bottom: 15px; }
        .upload-card { background: var(--panel); padding: 30px; border-radius: 16px; border: 1px solid var(--border); }
        .chip { padding: 6px 15px; border-radius: 20px; background: var(--glass); font-size: 12px; cursor: pointer; }
        .chip.active { background: var(--primary); color: black; }
        #loader { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.9); z-index: 9999; flex-direction: column; align-items: center; justify-content: center; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div id="loader"><div style="width:50px;height:50px;border:4px solid var(--glass);border-top-color:var(--primary);border-radius:50%;animation:spin 1s linear infinite"></div><h3 id="l-text">Uploading...</h3></div>
    <div class="sidebar">
        <h2 style="padding:0 15px; color:var(--primary)"><i class="fa-brands fa-spotify"></i> Beatify</h2>
        <div class="nav-item" id="n-home" onclick="show('home')"><i class="fa-solid fa-house"></i> Home</div>
        <div class="nav-item" id="n-up" onclick="show('upload')"><i class="fa-solid fa-plus"></i> Studio</div>
        <div style="margin-top:auto; padding:15px; border-top:1px solid var(--border)" id="profile-zone"></div>
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
        <div class="p-vol"><i class="fa-solid fa-volume-high"></i><input type="range" min="0" max="1" step="0.01" value="0.8" style="width:100px" oninput="setVol(this.value)"></div>
        <audio id="audio" ontimeupdate="updateProg()" onloadedmetadata="initDur()"></audio>
    </div>

<script>
    const _sb = supabase.createClient('https://zwtoztttsqamceuusvoi.supabase.co', 'sb_publishable_nxc75Aw211BgANYDwF09zQ_OFQXzGEO');
    let db = { songs: [] }, user = null, isSingle = false, isSignUp = false;

    async function init() {
        const { data } = await _sb.auth.getSession();
        user = data.session?.user || null;
        renderProfile();
        await loadData();
        if(!user) show('login'); else show('home');
    }

    async function loadData() {
        const r = await fetch('/api/data');
        const res = await r.json();
        db.songs = res.songs || [];
    }

    function renderProfile() {
        const p = document.getElementById('profile-zone');
        if(user) {
            const username = user.email.split('@')[0];
            p.innerHTML = `<div style="font-size:14px; font-weight:800; color:white; margin-bottom:5px">@${username}</div><button class="chip" style="width:100%" onclick="logout()">Logout</button>`;
        } else {
            p.innerHTML = `<button class="chip active" style="width:100%" onclick="show('login')">Get Started</button>`;
        }
    }

    function show(view) {
        const c = document.getElementById('content');
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        if(view === 'home') {
            document.getElementById('n-home').classList.add('active');
            const albums = {};
            db.songs.forEach(s => {
                const key = s.album === "Single" ? `s-${s.id}` : s.album;
                if(!albums[key]) albums[key] = { title: s.album, artist: s.artist, cover: s.cover_url, songs: [] };
                albums[key].songs.push(s);
            });
            let h = '<h1>Discovery</h1><div class="grid">';
            Object.values(albums).forEach(a => {
                const isSgl = a.title === 'Single';
                const clickParam = isSgl ? a.songs[0].id : `'${a.title.replace(/'/g, "\\\\'")}'`;
                h += `<div class="card" onclick="openMedia(${clickParam}, ${isSgl})">
                        <img src="${a.cover}">
                        <b>${isSgl ? a.songs[0].title : a.title}</b><br>
                        <small>${a.artist} • ${a.title}</small>
                      </div>`;
            });
            c.innerHTML = h || '<p>No music found.</p>';
        } else if(view === 'upload') {
            if(!user) return show('login');
            document.getElementById('n-up').classList.add('active');
            let h = `<div style="display:grid; grid-template-columns:1fr 1.2fr; gap:30px">
                <div class="upload-card">
                    <h2>Studio</h2>
                    <div style="display:flex; gap:10px; margin-bottom:20px">
                        <div class="chip ${!isSingle?'active':''}" onclick="setMode(false)">Album</div>
                        <div class="chip ${isSingle?'active':''}" onclick="setMode(true)">Single</div>
                    </div>
                    <input class="v-input" id="u-alb" placeholder="${isSingle?'Track Title':'Album Name'}">
                    <p>Artwork</p><input type="file" id="u-cov" accept="image/*">
                    <p>Audio</p><input type="file" id="u-tracks" ${isSingle?'':'multiple'} accept="audio/*">
                    <button class="btn-play" style="width:100%; border-radius:8px; margin-top:20px" onclick="doUp()">Publish</button>
                </div>
                <div class="upload-card"><h2>Library</h2>`;
            db.songs.filter(s => s.uploaded_by === user.email).forEach(s => {
                h += `<div style="display:flex; justify-content:space-between; padding:12px; background:var(--glass); border-radius:8px; margin-bottom:8px">
                    <div><b>${s.title}</b><br><small>${s.album}</small></div>
                    <i class="fa-solid fa-trash" style="color:red; cursor:pointer" onclick="delSong(${s.id})"></i>
                </div>`;
            });
            c.innerHTML = h + '</div></div>';
        } else if(view === 'login') {
            c.innerHTML = `<div class="upload-card" style="max-width:400px; margin:50px auto"><h2>${isSignUp?'Join':'Sign In'}</h2><input class="v-input" id="l-user" placeholder="Username"><input class="v-input" id="l-ps" type="password" placeholder="Password"><button class="btn-play" style="width:100%; border-radius:8px" onclick="doAuth()">Continue</button><p onclick="toggleSign()" style="cursor:pointer; text-align:center; margin-top:20px"><small>${isSignUp?'Login':'Sign Up'}</small></p></div>`;
        }
    }

    async function doUp() {
        const tracks = document.getElementById('u-tracks').files;
        if(!tracks.length) return alert("Select music!");
        document.getElementById('loader').style.display = 'flex';
        const fd = new FormData();
        fd.append('album', isSingle ? 'Single' : document.getElementById('u-alb').value);
        fd.append('artist_name', user.email.split('@')[0]);
        fd.append('user_email', user.email);
        fd.append('cover', document.getElementById('u-cov').files[0]);
        for(let f of tracks) fd.append('tracks', f);
        
        try {
            const r = await fetch('/api/upload', {method:'POST', body:fd});
            if(!r.ok) throw new Error(await r.text());
            location.reload();
        } catch(e) {
            alert("Upload failed: " + e.message);
            document.getElementById('loader').style.display = 'none';
        }
    }

    function toggleSign() { isSignUp = !isSignUp; show('login'); }
    function setMode(v) { isSingle = v; show('upload'); }
    async function delSong(id) { if(confirm('Delete?')) { await fetch(`/api/delete_song/${id}?user_email=${user.email}`, {method:'DELETE'}); location.reload(); }}
    function openMedia(p, s) { 
        const tracks = s ? db.songs.filter(x => x.id == p) : db.songs.filter(x => x.album === p);
        let h = `<div style="display:flex; gap:30px; margin-bottom:30px"><img src="${tracks[0].cover_url}" width="200" style="border-radius:12px"><div><h1>${s ? tracks[0].title : tracks[0].album}</h1><b>${tracks[0].artist}</b></div></div>`;
        tracks.forEach((t, i) => {
            h += `<div class="nav-item" onclick="play('${t.track_url}','${t.title.replace(/'/g,"\\\\'")}','${t.artist.replace(/'/g,"\\\\'")}','${t.cover_url}')"><span>${i+1}</span><div style="flex:1"><b>${t.title}</b></div><i class="fa-solid fa-play"></i></div>`;
        });
        document.getElementById('content').innerHTML = h;
    }
    function play(u, t, a, c) { 
        document.getElementById('player').style.display = 'flex';
        const audio = document.getElementById('audio'); audio.src = u; audio.play();
        document.getElementById('play-btn').className = "fa-solid fa-pause";
        document.getElementById('p-info').innerHTML = `<img src="${c}" width="50" height="50" style="border-radius:4px"><div><b>${t}</b><br><small>${a}</small></div>`;
    }
    function togglePlay() { const a=document.getElementById('audio'); if(a.paused){a.play(); document.getElementById('play-btn').className="fa-solid fa-pause";} else {a.pause(); document.getElementById('play-btn').className="fa-solid fa-play";}}
    function setVol(v) { document.getElementById('audio').volume = v; }
    function updateProg() { const a=document.getElementById('audio'); if(a.duration) document.getElementById('prog-range').value = (a.currentTime/a.duration)*100; document.getElementById('cur-time').innerText=fmt(a.currentTime);}
    function initDur() { document.getElementById('dur-time').innerText=fmt(document.getElementById('audio').duration);}
    function fmt(s) { const m=Math.floor(s/60); const sec=Math.floor(s%60); return m+":"+(sec<10?"0":"")+sec;}
    function seek(v) { const a=document.getElementById('audio'); a.currentTime=(v/100)*a.duration;}
    async function doAuth() {
        const u = document.getElementById('l-user').value, p = document.getElementById('l-ps').value;
        const e = `${u}@beatify.com`;
        let res = isSignUp ? await _sb.auth.signUp({email:e, password:p}) : await _sb.auth.signInWithPassword({email:e, password:p});
        if(res.error) alert(res.error.message); else location.reload();
    }
    async function logout() { await _sb.auth.signOut(); location.reload(); }
    init();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
