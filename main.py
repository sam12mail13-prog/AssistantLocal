#!/usr/bin/env python3
"""
🧠 Assistant Local — Lanceur
Détection auto • Recherche • Saisie libre • Discussion
"""
import os
import sys
import time
import json
import threading
import subprocess
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

PORT = 8080
OLLAMA_BASE = "http://127.0.0.1:11434"

HOME = os.path.expanduser("~")
OLLAMA_DIR = os.path.join(HOME, ".ollama")
OLLAMA_BIN = os.path.join(OLLAMA_DIR, "ollama")
os.makedirs(OLLAMA_DIR, exist_ok=True)
os.environ["OLLAMA_MODELS"] = os.path.join(OLLAMA_DIR, "models")
os.environ["PATH"] = f"{OLLAMA_DIR}:{os.environ.get('PATH', '')}"

# ─── DÉTECTION ───
class Appareil:
    def __init__(self):
        self.arch = self._get_arch()
        self.cpu_nom = self._get_cpu()
        self.ram_gb = self._get_ram()

    def _get_arch(self):
        try:
            m = os.uname().machine
            if "aarch64" in m or "arm64" in m: return "arm64"
            return m
        except: return "arm64"

    def _get_cpu(self):
        try:
            with open("/proc/cpuinfo") as f:
                c = f.read().lower()
                if "dimensity" in c:
                    if "8100" in c: return "Dimensity 8100-Ultra (Xiaomi 12T)"
                    return "Dimensity"
        except: pass
        return "Processeur inconnu"

    def _get_ram(self):
        try:
            with open("/proc/meminfo") as f:
                for l in f:
                    if l.startswith("MemTotal"):
                        return round(int(l.split()[1]) / 1024 / 1024, 1)
        except: return 7.2

    def resumer(self):
        return f"{self.cpu_nom} | {self.ram_gb} Go RAM | {self.arch}"

APPAREIL = Appareil()

# ─── BIBLIOTHÈQUE ───
BIBLIOTHEQUE = [
    {"id": "qwen2.5:0.5b", "nom": "Qwen 2.5 — Ultra-Léger", "desc": "💨 Le plus rapide", "ram_min": 0.8, "tags": ["rapide"]},
    {"id": "llama3.2:1b", "nom": "Llama 3.2 — Rapide", "desc": "⚡ Réponse instantanée", "ram_min": 1.2, "tags": ["rapide"]},
    {"id": "qwen3:1.7b", "nom": "Qwen 3 — Équilibre", "desc": "🎯 Recommandé", "ram_min": 1.8, "tags": ["recommandé"]},
    {"id": "llama3.2:3b", "nom": "Llama 3.2 — Détaillé", "desc": "💪 Raisonnement solide", "ram_min": 2.8, "tags": ["puissant"]},
    {"id": "gemma3:4b", "nom": "Gemma 3 — Maximum", "desc": "🔥 Très précis", "ram_min": 3.5, "tags": ["maximum"]},
    {"id": "llama3.1:8b", "nom": "Llama 3.1 — Référence", "desc": "👑 Le plus puissant", "ram_min": 6.5, "tags": ["maximum"]},
]

# ─── GESTION OLLAMA ───
def verifier_ollama():
    return os.path.exists(OLLAMA_BIN)

def installer_ollama():
    print(f"📥 Téléchargement d'Ollama...")
    try:
        url = "https://github.com/ollama/ollama/releases/latest/download/ollama-linux-arm64"
        r = requests.get(url, timeout=300, stream=True)
        r.raise_for_status()
        with open(OLLAMA_BIN, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        os.chmod(OLLAMA_BIN, 0o755)
        print("✅ Ollama installé !")
        return True
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return False

def demarrer_ollama():
    subprocess.run(["pkill", "-f", "ollama"], capture_output=True)
    time.sleep(1)
    try: subprocess.run(["termux-wake-lock"], capture_output=True)
    except: pass
    subprocess.Popen([OLLAMA_BIN, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(1)
        try:
            if requests.get(f"{OLLAMA_BASE}/api/tags", timeout=1).status_code == 200:
                return True
        except: pass
    return True

def modeles_installes():
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        if r.status_code == 200:
            return [m["name"] for m in r.json().get("models", [])]
    except: pass
    return []

def telecharger(nom):
    print(f"⬇️ Téléchargement de {nom}...")
    proc = subprocess.Popen([OLLAMA_BIN, "pull", nom], text=True)
    proc.wait()
    return proc.returncode == 0

mode_actuel = None
historique = []

def discuter(message):
    if not mode_actuel:
        return "⚠️ Sélectionne d'abord un modèle", 0
    debut = time.time()
    messages = [{"role": "system", "content": f"Assistant local — {APPAREIL.resumer()}. Réponds en français."}]
    for m in historique[-10:]: messages.append(m)
    messages.append({"role": "user", "content": message})
    try:
        r = requests.post(
            f"{OLLAMA_BASE}/v1/chat/completions",
            json={"model": mode_actuel, "messages": messages, "temperature": 0.7},
            timeout=300
        )
        rep = r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        rep = f"⚠️ Erreur : {str(e)}"
    return rep, round(time.time() - debut, 2)

# ─── INTERFACE WEB ───
HTML = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Assistant Local</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:system-ui,sans-serif}}
:root{{--bg:#0f1115;--cb:#1a1d23;--brd:#2d3038;--txt:#e4e6eb;--pri:#4f46e5;--ok:#10b981}}
body{{background:var(--bg);color:var(--txt);min-height:100vh}}
.entete{{background:linear-gradient(135deg,#1e293b,#0f172a);padding:1.2rem;border-bottom:1px solid var(--brd)}}
h1{{font-size:1.2rem;margin-bottom:.6rem}}
.info{{font-size:.8rem;color:#9ba1b0;margin-bottom:1rem;padding:.7rem;background:rgba(0,0,0,.25);border-radius:.7rem}}
.rech{{padding:1rem}}
#rech{{width:100%;background:var(--cb);border:1px solid var(--brd);border-radius:.7rem;padding:.9rem;color:var(--txt);font-size:1rem}}
.libre{{padding:0 1rem 1rem}}
.libre-ligne{{display:flex;gap:.6rem;margin-top:.5rem}}
#libre{{flex:1;background:var(--cb);border:1px solid var(--brd);border-radius:.7rem;padding:.9rem;color:var(--txt)}}
.btn-ok{{background:var(--ok);color:#fff;border:none;border-radius:.7rem;padding:.9rem 1rem;cursor:pointer}}
.liste{{padding:1rem}}
.modele{{background:var(--cb);border:1px solid var(--brd);border-radius:.8rem;padding:.9rem;margin-bottom:.7rem;cursor:pointer}}
.modele:hover{{border-color:var(--pri)}}
.modele.reco{{border-left:3px solid var(--ok)}}
.modele.installe{{border-color:var(--ok)}}
.msg{{max-width:92%;margin:.8rem 0;padding:.9rem 1.1rem;border-radius:1rem;white-space:pre-wrap}}
.msg.toi{{background:var(--pri);margin-left:auto}}
.msg.ia{{background:var(--ok);color:#000;margin-right:auto}}
.saisie{{position:fixed;bottom:0;left:0;right:0;padding:1rem;background:rgba(15,17,21,.95);border-top:1px solid var(--brd)}}
.saisie-ligne{{display:flex;gap:.6rem}}
#msg{{flex:1;background:var(--cb);border:none;border-radius:.7rem;padding:.9rem;color:var(--txt);resize:none;height:50px}}
.btn{{background:var(--pri);color:#fff;border:none;border-radius:.7rem;padding:.9rem 1.2rem;cursor:pointer}}
.page{{display:none;padding-bottom:100px}}
.page.active{{display:block}}
.retour{{background:transparent;border:none;color:var(--pri);padding:1rem;cursor:pointer;font-size:.9rem}}
.chargement{{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:var(--cb);border-radius:1rem;padding:2rem;display:none;z-index:100}}
.spin{{width:40px;height:40px;border:3px solid var(--brd);border-top-color:var(--pri);border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 1rem}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
</style>
</head>
<body>
<div id="page-selection" class="page active">
    <div class="entete">
        <h1>🧠 Assistant Local</h1>
        <div class="info">📱 {APPAREIL.cpu_nom}<br>💾 {APPAREIL.ram_gb} Go RAM détectée</div>
    </div>
    <div class="rech">
        <input type="text" id="rech" placeholder="Rechercher un modèle..." oninput="afficher()">
    </div>
    <div class="libre">
        <p style="font-size:.8rem;color:#9ba1b0">✏️ Ou entre un nom personnalisé :</p>
        <div class="libre-ligne">
            <input type="text" id="libre" placeholder="ex: deepseek-r1:7b">
            <button class="btn-ok" onclick="ajouter()">Ajouter</button>
        </div>
    </div>
    <div class="liste" id="liste"></div>
</div>
<div id="page-chat" class="page">
    <button class="retour" onclick="retour()">← Choisir un autre modèle</button>
    <div id="messages"></div>
    <div class="saisie">
        <div class="saisie-ligne">
            <textarea id="msg" placeholder="Ta demande..." onkeydown="touche(event)"></textarea>
            <button class="btn" onclick="envoyer()">Envoyer</button>
        </div>
    </div>
</div>
<div class="chargement" id="chargement">
    <div class="spin"></div>
    <p id="texte-chargement">Vérification...</p>
</div>
<script>
let installes = [];
async function charger() {{
    const r = await fetch('/liste');
    installes = await r.json();
    afficher();
}}
function afficher(texte='') {{
    const cont = document.getElementById('liste');
    cont.innerHTML = '';
    let liste = {json.dumps(BIBLIOTHEQUE)};
    if (texte) {{
        const t = texte.toLowerCase();
        liste = liste.filter(m => m.nom.toLowerCase().includes(t) || m.id.toLowerCase().includes(t));
    }}
    liste.forEach(m => {{
        const ok = {APPAREIL.ram_gb} >= m.ram_min;
        const inst = installes.includes(m.id);
        const reco = ok && m.ram_min >= 1.5 && m.ram_min <= 2.0;
        const div = document.createElement('div');
        div.className = `modele ${{reco?'reco':''}} ${{inst?'installe':''}}`;
        div.innerHTML = `<div style="font-weight:500">${{reco?'✅ ':''}}${{m.nom}}${{inst?' ✓ Installé':''}}</div><div style="font-size:.8rem;color:#9ba1b0;margin:.3rem 0">${{m.desc}}</div><div style="font-size:.75rem;color:#6b7280">RAM min: ${{m.ram_min}} Go</div>`;
        if (ok) div.onclick = () => selectionner(m.id, inst);
        cont.appendChild(div);
    }});
}}
async function ajouter() {{
    const nom = document.getElementById('libre').value.trim();
    if (!nom) return alert('Entre un nom');
    chargement(`Ajout de ${{nom}}...`);
    const r = await fetch('/ajouter', {{method:'POST',body:'nom='+encodeURIComponent(nom)}});
    masquer();
    if (r.ok) {{ alert(`✅ ${{nom}} ajouté !`); charger(); }}
    else alert('Erreur — vérifie le nom');
}}
async function selectionner(id, deja) {{
    if (!deja) chargement(`Téléchargement de ${{id}}...`);
    const r = await fetch('/selectionner', {{method:'POST',body:'id='+encodeURIComponent(id)}});
    masquer();
    if (r.ok) {{
        document.getElementById('page-selection').classList.remove('active');
        document.getElementById('page-chat').classList.add('active');
        document.getElementById('messages').innerHTML = `<div class="msg ia">✅ <strong>${{id}}</strong> actif ! Pose ta question.</div>`;
    }}
}}
function retour() {{
    document.getElementById('page-chat').classList.remove('active');
    document.getElementById('page-selection').classList.add('active');
    charger();
}}
async function envoyer() {{
    const texte = document.getElementById('msg').value.trim();
    if (!texte) return;
    ajouterMsg(texte, 'toi');
    document.getElementById('msg').value = '';
    const r = await fetch('/parler', {{method:'POST',body:'texte='+encodeURIComponent(texte)}});
    const data = await r.json();
    ajouterMsg(data.reponse, 'ia', data.duree);
}}
function ajouterMsg(contenu, qui, duree=null) {{
    const div = document.createElement('div');
    div.className = `msg ${{qui}}`;
    div.textContent = contenu;
    if (duree) {{
        const m = document.createElement('div');
        m.style = 'font-size:.7rem;opacity:.6;margin-top:.5rem';
        m.textContent = `⏱️ ${{duree}}s`;
        div.appendChild(m);
    }}
    document.getElementById('messages').appendChild(div);
}}
function touche(e) {{ if (e.key==='Enter'&&!e.shiftKey) {{e.preventDefault();envoyer();}} }}
function chargement(t) {{ document.getElementById('texte-chargement').innerText=t;document.getElementById('chargement').style.display='block'; }}
function masquer() {{ document.getElementById('chargement').style.display='none'; }}
charger();
</script>
</body>
</html>"""

# ─── SERVEUR ───
class Serveur(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        if self.path == "/liste":
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(modeles_installes()).encode())
        else:
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())

    def do_POST(self):
        global mode_actuel, historique, BIBLIOTHEQUE
        n = int(self.headers["Content-Length"])
        data = parse_qs(self.rfile.read(n).decode())
        if self.path == "/ajouter":
            nom = data["nom"][0].strip()
            BIBLIOTHEQUE.append({"id": nom, "nom": nom, "desc": "Ajouté manuellement", "ram_min": 2.0, "tags": ["perso"]})
            telecharger(nom)
            self.send_response(200)
        elif self.path == "/selectionner":
            mode_actuel = data["id"][0]
            historique = []
            if mode_actuel not in modeles_installes(): telecharger(mode_actuel)
            self.send_response(200)
        elif self.path == "/parler":
            msg = data["texte"][0]
            rep, duree = discuter(msg)
            historique.append({"role":"user","content":msg})
            historique.append({"role":"assistant","content":rep})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"reponse":rep,"duree":duree}).encode())
        self.end_headers()
    def log_message(self, *args): pass

def lancer_serveur():
    HTTPServer(("127.0.0.1", PORT), Serveur).serve_forever()

# ─── DÉMARRAGE ───
if __name__ == "__main__":
    print("="*50)
    print("🧠 LANCEUR ASSISTANT LOCAL")
    print("="*50)
    print(f"📱 {APPAREIL.resumer()}")
    threading.Thread(target=lancer_serveur, daemon=True).start()
    if not verifier_ollama():
        if not installer_ollama(): sys.exit(1)
    demarrer_ollama()
    print(f"✅ Prêt ! Ouvre : http://127.0.0.1:{PORT}")
    while True: time.sleep(3600)
