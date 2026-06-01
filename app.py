# app.py
from flask import Flask, render_template_string, request, jsonify
import threading
import time
import os

app = Flask(__name__)

# --- 1. SİSTEM KULLANICILARI ---
# Artık admin yeni kombi ekledikçe buraya dinamik olarak yeni teknisyenler de yazılacak
KULLANICILAR = {
    "admin": {
        "sifre": "1234",
        "rol": "YÖNETİCİ",
        "cihazlar": ["kombi_ist_01", "kombi_ank_02"]
    },
    "teknisyen_ist": {
        "sifre": "ist34",
        "rol": "TEKNİSYEN",
        "cihazlar": ["kombi_ist_01"]
    },
    "teknisyen_ank": {
        "sifre": "ank06",
        "rol": "TEKNİSYEN",
        "cihazlar": ["kombi_ank_02"]
    }
}

# --- 2. DİNAMİK KOMBİ HAVUZU ---
kombiler = {
    "kombi_ist_01": {
        "isim": "İstanbul Kadıköy Ünitesi",
        "temp": 42, "setpoint": 45, "flame": 0, "error": 0, "p01": 3500, "p02": 120
    },
    "kombi_ank_02": {
        "isim": "Ankara Çankaya Ünitesi",
        "temp": 38, "setpoint": 50, "flame": 0, "error": 0, "p01": 3100, "p02": 90
    }
}


# --- KOMBİ SİMÜLASYON MOTORU ---
def kombi_fizik_motoru():
    while True:
        for kombi_id, cihaz in list(kombiler.items()):
            if cihaz["error"] != 0:
                cihaz["flame"] = 0
                if cihaz["temp"] > 22:
                    cihaz["temp"] -= 1
            elif cihaz["temp"] < cihaz["setpoint"]:
                cihaz["flame"] = 1
                cihaz["temp"] += 1
            elif cihaz["temp"] >= cihaz["setpoint"]:
                cihaz["flame"] = 0
                if cihaz["temp"] > 20:
                    cihaz["temp"] -= 1
        time.sleep(2)


# --- WEB ARAYÜZÜ (HTML) ---
WEB_ARAYUZU = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E.C.A. Kombi Global Filo Yönetimi</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
</head>
<body class="bg-gray-950 text-gray-100 p-4 min-h-screen flex flex-col items-center select-none">
    <div class="w-full max-w-md bg-gray-900 rounded-2xl shadow-2xl border border-gray-800 p-5 space-y-4 mt-4">

        <div class="flex justify-between items-center border-b border-gray-800 pb-3 gap-2">
            <div>
                <h1 class="text-lg font-bold text-blue-500">E.C.A. FLEET</h1>
                <p class="text-[10px] text-gray-400">Yetki: <span id="auth-level" class="text-emerald-400 font-bold">MİSAFİR</span></p>
            </div>
            <div id="login-area" class="flex gap-1 items-center">
                <input type="text" id="username" placeholder="Kullanıcı" class="bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5 text-xs w-16 text-center">
                <input type="password" id="pass" placeholder="Şifre" class="bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5 text-xs w-16 text-center">
                <button onclick="girisYap()" class="bg-blue-600 text-[11px] px-2 py-0.5 rounded font-bold">Giriş</button>
            </div>
            <button id="logout-btn" onclick="cikisYap()" class="hidden bg-red-900 text-xs px-3 py-1 rounded-lg font-bold">Çıkış</button>
        </div>

        <div id="admin-add-section" class="hidden bg-gray-950 p-3 rounded-xl border border-amber-900/50 space-y-2">
            <span class="text-xs font-bold text-amber-500 block">➕ Yeni Kombi & Sorumlu Teknisyen Ekle</span>
            <div class="space-y-1.5">
                <div class="flex gap-1">
                    <input type="text" id="new-kombi-id" placeholder="Kombi ID (örn: bursa_03)" class="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs flex-1">
                    <input type="text" id="new-kombi-name" placeholder="Kombi Adı (örn: Bursa Bayi)" class="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs flex-1">
                </div>
                <div class="flex gap-1">
                    <input type="text" id="new-tech-user" placeholder="Teknisyen K. Adı" class="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs flex-1 text-amber-400">
                    <input type="password" id="new-tech-pass" placeholder="Teknisyen Şifre" class="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs flex-1 text-amber-400">
                </div>
                <button onclick="yeniKombiEkle()" class="w-full bg-amber-600 hover:bg-amber-500 text-xs py-1.5 rounded font-bold transition">Sisteme Entegre Et</button>
            </div>
        </div>

        <div class="bg-gray-950 p-3 rounded-xl border border-gray-800 space-y-1">
            <label class="text-xs text-gray-400 block font-bold">İzlenen Kombi Ünitesi:</label>
            <select id="kombi-select" onchange="kombiDegisti()" class="w-full bg-gray-800 border border-gray-700 rounded-lg p-2 text-sm text-blue-400 font-bold outline-none">
                </select>
        </div>

        <div class="bg-gray-950 rounded-xl p-5 text-center border border-gray-800 relative">
            <div id="live-temp" class="text-6xl font-black text-emerald-400">-- °C</div>
            <div id="kombi-isim" class="text-xs text-gray-400 mt-1">Lütfen Giriş Yapın</div>
            <div id="live-flame" class="text-xs mt-2 font-bold text-gray-500">Durum: Bekleniyor...</div>
        </div>

        <div id="alert-bar" class="w-full text-center py-2 rounded-lg font-bold text-xs bg-gray-800 text-gray-400">
            Sistem Bağlantısı Bekleniyor
        </div>

        <div class="bg-gray-950 p-4 rounded-xl border border-gray-800 space-y-3">
            <div class="flex justify-between text-xs font-bold">
                <span>Sıcaklık Ayarı (Setpoint):</span>
                <span id="set-val" class="text-blue-400">45°C</span>
            </div>
            <input type="range" id="set-slider" min="30" max="65" value="45" class="w-full accent-blue-500">
            <button onclick="komutGonder('setpoint', document.getElementById('set-slider').value)" class="w-full bg-blue-600 hover:bg-blue-500 py-2 rounded-lg text-sm font-bold transition">Komut Gönder</button>
        </div>

        <div id="tech-section" class="hidden border-t border-gray-800 pt-4 space-y-3">
            <h3 class="text-sm font-bold text-amber-500">🛠 nighttime Özel Servis Parametreleri</h3>
            <div class="space-y-2 text-xs">
                <div class="bg-gray-950 p-3 rounded-lg border border-gray-800 flex justify-between items-center">
                    <span>P01: Max Fan (RPM):</span>
                    <div class="flex gap-1">
                        <input type="number" id="p01-in" class="w-16 bg-gray-800 border border-gray-700 text-center rounded text-amber-400">
                        <button onclick="komutGonder('p01', document.getElementById('p01-in').value)" class="bg-amber-600 px-2 py-0.5 rounded font-bold">Yaz</button>
                    </div>
                </div>
                <div class="bg-gray-950 p-3 rounded-lg border border-gray-800 flex justify-between items-center">
                    <span>P02: Pompa Gecikme (Sn):</span>
                    <div class="flex gap-1">
                        <input type="number" id="p02-in" class="w-16 bg-gray-800 border border-gray-700 text-center rounded text-amber-400">
                        <button onclick="komutGonder('p02', document.getElementById('p02-in').value)" class="bg-amber-600 px-2 py-0.5 rounded font-bold">Yaz</button>
                    </div>
                </div>
                <div class="bg-gray-950 p-3 rounded-lg border border-gray-800 space-y-2">
                    <span class="text-red-400 font-bold block">Simülasyon Test Araçları:</span>
                    <div class="grid grid-cols-2 gap-2">
                        <button onclick="komutGonder('error', 1)" class="bg-red-900/50 hover:bg-red-900 py-1.5 rounded text-[10px] font-bold text-red-200">E01 Arızası</button>
                        <button onclick="komutGonder('error', 4)" class="bg-red-900/50 hover:bg-red-900 py-1.5 rounded text-[10px] font-bold text-red-200">E04 Arızası</button>
                    </div>
                    <button onclick="komutGonder('error', 0)" class="w-full bg-emerald-800 hover:bg-emerald-700 py-1.5 rounded text-[10px] font-bold text-emerald-100">Arızayı Resetle</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let mevcutKullanici = "";
        let mevcutSifre = "";
        let aktifCihazId = "";

        setInterval(async () => {
            if(!aktifCihazId) return;
            try {
                let res = await fetch(`/api/durum/${aktifCihazId}`);
                if(res.status !== 200) return;
                let data = await res.json();

                document.getElementById("live-temp").innerText = data.temp + " °C";
                document.getElementById("live-flame").innerText = data.flame === 1 ? "Durum: 🔥 Kombi Yanıyor" : "Durum: 💤 Standby";
                document.getElementById("kombi-isim").innerText = data.isim;

                let alertBar = document.getElementById("alert-bar");
                if (data.error !== 0) {
                    alertBar.innerText = "⚠️ ARIZA: E" + data.error;
                    alertBar.className = "w-full text-center py-2 rounded-lg font-bold text-xs bg-red-900 text-red-100";
                } else {
                    let yetkiText = document.getElementById("auth-level").innerText;
                    alertBar.innerText = yetkiText !== "MİSAFİR" ? `🛠️ ${yetkiText} Modu Aktif` : "Sistem Normal";
                    alertBar.className = yetkiText !== "MİSAFİR" ? "w-full text-center py-2 rounded-lg font-bold text-xs bg-amber-950 text-amber-300" : "w-full text-center py-2 rounded-lg font-bold text-xs bg-emerald-950 text-emerald-300";
                }
                if (!document.getElementById("tech-section").classList.contains("hidden")) {
                    document.getElementById("p01-in").placeholder = data.p01;
                    document.getElementById("p02-in").placeholder = data.p02;
                }
            } catch (err) { console.error(err); }
        }, 1500);

        function kombiDegisti() {
            aktifCihazId = document.getElementById("kombi-select").value;
        }

        async function girisYap() {
            let u = document.getElementById("username").value;
            let p = document.getElementById("pass").value;

            let response = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: u, sifre: p})
            });
            let data = await response.json();

            if(data.status === "ok") {
                mevcutKullanici = u;
                mevcutSifre = p;

                document.getElementById("auth-level").innerText = data.rol;
                document.getElementById("login-area").classList.add("hidden");
                document.getElementById("logout-btn").classList.remove("hidden");

                if(data.rol === "TEKNİSYEN" || data.rol === "YÖNETİCİ") {
                    document.getElementById("tech-section").classList.remove("hidden");
                }
                if(data.rol === "YÖNETİCİ") {
                    document.getElementById("admin-add-section").classList.remove("hidden");
                }

                kombiListesiniYenile(data.cihazlar);
            } else {
                alert("Hatalı Kullanıcı Adı veya Şifre!");
            }
        }

        function kombiListesiniYenile(cihazlar, secilecekId = null) {
            let select = document.getElementById("kombi-select");
            select.innerHTML = "";
            cihazlar.forEach(c => {
                let opt = document.createElement('option');
                opt.value = c.id;
                opt.innerText = c.isim;
                select.appendChild(opt);
            });
            aktifCihazId = secilecekId ? secilecekId : cihazlar[0].id;
            select.value = aktifCihazId;
        }

        async function yeniKombiEkle() {
            let kid = document.getElementById("new-kombi-id").value.trim();
            let kname = document.getElementById("new-kombi-name").value.trim();
            let tuser = document.getElementById("new-tech-user").value.trim();
            let tpass = document.getElementById("new-tech-pass").value.trim();

            if(!kid || !kname || !tuser || !tpass) { 
                alert("Lütfen tüm alanları (Kombi ve Teknisyen bilgileri) doldurun!"); 
                return; 
            }

            let response = await fetch('/api/kombi-ekle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: mevcutKullanici,
                    sifre: mevcutSifre,
                    id: kid,
                    isim: kname,
                    tech_user: tuser,
                    tech_pass: tpass
                })
            });
            let data = await response.json();
            if(data.status === "ok") {
                alert("Kombi oluşturuldu ve yeni teknisyen hesabı başarıyla tanımlandı!");
                document.getElementById("new-kombi-id").value = "";
                document.getElementById("new-kombi-name").value = "";
                document.getElementById("new-tech-user").value = "";
                document.getElementById("new-tech-pass").value = "";
                kombiListesiniYenile(data.cihazlar, kid);
            } else {
                alert(data.message);
            }
        }

        function cikisYap() {
            mevcutKullanici = ""; mevcutSifre = ""; aktifCihazId = "";
            document.getElementById("username").value = "";
            document.getElementById("pass").value = "";
            document.getElementById("auth-level").innerText = "MİSAFİR";
            document.getElementById("login-area").classList.remove("hidden");
            document.getElementById("logout-btn").classList.add("hidden");
            document.getElementById("tech-section").classList.add("hidden");
            document.getElementById("admin-add-section").classList.add("hidden");
            document.getElementById("kombi-select").innerHTML = "";
            document.getElementById("live-temp").innerText = "-- °C";
            document.getElementById("kombi-isim").innerText = "Lütfen Giriş Yapın";
            document.getElementById("alert-bar").className = "w-full text-center py-2 rounded-lg font-bold text-xs bg-gray-800 text-gray-400";
            document.getElementById("alert-bar").innerText = "Sistem Bağlantısı Bekleniyor";
        }

        async function komutGonder(parametre, deger) {
            if(!aktifCihazId || deger === "") return;

            let response = await fetch('/api/komut', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: mevcutKullanici,
                    sifre: mevcutSifre,
                    cihaz_id: aktifCihazId,
                    parametre: parametre,
                    deger: parseInt(deger)
                })
            });
            let resData = await response.json();
            if(resData.status === "error") alert(resData.message);
        }

        const slider = document.getElementById("set-slider");
        slider.oninput = function() { document.getElementById("set-val").innerText = this.value + "°C"; }
    </script>
</body>
</html>
"""


@app.route('/')
def ana_sayfa():
    return render_template_string(WEB_ARAYUZU)


# --- API: KULLANICI GİRİŞ KONTROLÜ ---
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    u = data.get("username")
    p = data.get("sifre")

    if u in KULLANICILAR and KULLANICILAR[u]["sifre"] == p:
        user_info = KULLANICILAR[u]
        if user_info["rol"] == "YÖNETİCİ":
            # Admin her zaman güncel havuzdaki tüm kombileri çeker
            izinli_cihazlar = [{"id": cid, "isim": kombiler[cid]["isim"]} for cid in kombiler]
        else:
            izinli_cihazlar = [{"id": cid, "isim": kombiler[cid]["isim"]} for cid in user_info["cihazlar"] if
                               cid in kombiler]

        return jsonify({
            "status": "ok",
            "rol": user_info["rol"],
            "cihazlar": izinli_cihazlar
        })
    return jsonify({"status": "error", "message": "Giriş başarısız"}), 401


# --- API: DİNAMİK KOMBİ VE KULLANICI OLUŞTURMA (Admin Yetkili) ---
@app.route('/api/kombi-ekle', methods=['POST'])
def api_kombi_ekle():
    data = request.get_json() or {}
    u = data.get("username")
    p = data.get("sifre")
    new_id = data.get("id")
    new_isim = data.get("isim")
    tech_user = data.get("tech_user")
    tech_pass = data.get("tech_pass")

    # Yetki Doğrulama
    if u not in KULLANICILAR or KULLANICILAR[u]["sifre"] != p or KULLANICILAR[u]["rol"] != "YÖNETİCİ":
        return jsonify({"status": "error", "message": "Bu işlem için Yönetici yetkisi gerekiyor!"}), 403

    if new_id in kombiler:
        return jsonify({"status": "error", "message": "Bu Kombi ID zaten mevcut!"}), 400

    if tech_user in KULLANICILAR:
        return jsonify({"status": "error", "message": "Bu Teknisyen kullanıcı adı zaten alınmış!"}), 400

    # 1. Yeni Kombiyi Tanımla
    kombiler[new_id] = {
        "isim": new_isim,
        "temp": 32, "setpoint": 42, "flame": 0, "error": 0, "p01": 3200, "p02": 110
    }

    # 2. Yeni Teknisyen Kullanıcısını Havuza Ekle ve Cihazı Atap et
    KULLANICILAR[tech_user] = {
        "sifre": tech_pass,
        "rol": "TEKNİSYEN",
        "cihazlar": [new_id]
    }

    # Yöneticinin kendi listesini de güncelle
    if new_id not in KULLANICILAR[u]["cihazlar"]:
        KULLANICILAR[u]["cihazlar"].append(new_id)

    # Admin paneli yenilesin diye tüm cihazları dönüyoruz
    tum_cihazlar = [{"id": cid, "isim": kombiler[cid]["isim"]} for cid in kombiler]
    return jsonify({"status": "ok", "cihazlar": tum_cihazlar})


# --- API: ANLIK DURUM BİLGİSİ ---
@app.route('/api/durum/<cihaz_id>', methods=['GET'])
def durum_ver(cihaz_id):
    if cihaz_id in kombiler:
        return jsonify(kombiler[cihaz_id])
    return jsonify({"error": "Cihaz bulunamadı"}), 404


# --- API: GÜVENLİ KOMUT ALMA ---
@app.route('/api/komut', methods=['POST'])
def komut_al():
    req_data = request.get_json() or {}
    u = req_data.get("username")
    p = req_data.get("sifre")
    cihaz_id = req_data.get("cihaz_id")
    parametre = req_data.get("parametre")
    deger = req_data.get("deger")

    if not cihaz_id or cihaz_id not in kombiler:
        return jsonify({"status": "error", "message": "Geçersiz Cihaz"}), 400

    if u not in KULLANICILAR or KULLANICILAR[u]["sifre"] != p:
        return jsonify({"status": "error", "message": "Yetkisiz Erişim!"}), 403

    if KULLANICILAR[u]["rol"] != "YÖNETİCİ" and cihaz_id not in KULLANICILAR[u]["cihazlar"]:
        return jsonify({"status": "error", "message": "Bu cihaza erişim yetkiniz yok!"}), 403

    cihaz = kombiler[cihaz_id]

    try:
        deger = int(deger)
        if parametre == "setpoint":
            cihaz["setpoint"] = deger
            return jsonify({"status": "ok"})

        elif parametre in ["p01", "p02", "error"]:
            if parametre == "p01":
                cihaz["p01"] = deger
            elif parametre == "p02":
                cihaz["p02"] = deger
            elif parametre == "error":
                cihaz["error"] = deger
                if deger != 0:
                    cihaz["temp"] = 22
                else:
                    cihaz["temp"] = 35
                    cihaz["setpoint"] = 45
                    cihaz["flame"] = 0
            return jsonify({"status": "ok"})

    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Hatalı değer formatı"}), 400

    return jsonify({"status": "error", "message": "Bilinmeyen istek"}), 400


if __name__ == '__main__':
    threading.Thread(target=kombi_fizik_motoru, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
