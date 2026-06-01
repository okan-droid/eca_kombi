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
    <title>E.C.A. Kombi Fleet - Yönetici Komuta Merkezi</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-gray-950 text-gray-100 p-4 min-h-screen flex flex-col items-center select-none">

    <div class="w-full max-w-5xl bg-gray-900 rounded-2xl shadow-2xl border border-gray-800 p-6 space-y-6 mt-4">

        <div class="flex justify-between items-center border-b border-gray-800 pb-4 gap-4">
            <div>
                <h1 class="text-xl font-black tracking-tight text-blue-500 flex items-center gap-2">
                    <i class="fa-solid trips-daily"></i> E.C.A. FLEET COMMANDER
                </h1>
                <p class="text-xs text-gray-400">Yetki Seviyesi: <span id="auth-level" class="text-emerald-400 font-bold">MİSAFİR</span></p>
            </div>

            <div id="login-area" class="flex gap-2 items-center">
                <input type="text" id="username" placeholder="Kullanıcı" class="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-xs w-24 text-center outline-none focus:border-blue-500">
                <input type="password" id="pass" placeholder="Şifre" class="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-xs w-24 text-center outline-none focus:border-blue-500">
                <button onclick="girisYap()" class="bg-blue-600 hover:bg-blue-500 text-xs px-3 py-1 rounded-lg font-bold transition">Giriş</button>
            </div>

            <button id="logout-btn" onclick="cikisYap()" class="hidden bg-red-900/80 hover:bg-red-800 text-xs px-4 py-1.5 rounded-lg font-bold transition">
                <i class="fa-solid fa-sign-out-alt"></i> Güvenli Çıkış
            </button>
        </div>

        <div id="admin-add-section" class="hidden bg-gray-950 p-4 rounded-xl border border-amber-900/40 space-y-3">
            <span class="text-xs font-bold text-amber-500 flex items-center gap-1.5">
                <i class="fa-solid fa-plus-circle"></i> Yeni Kombi İstasyonu & Teknisyen Tanımla
            </span>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-2">
                <input type="text" id="new-kombi-id" placeholder="Kombi ID (örn: bursa_03)" class="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-amber-500">
                <input type="text" id="new-kombi-name" placeholder="Kombi Adı (örn: Bursa Bayi)" class="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-amber-500">
                <input type="text" id="new-tech-user" placeholder="Teknisyen Kullanıcı Adı" class="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-amber-500 text-amber-400">
                <input type="password" id="new-tech-pass" placeholder="Teknisyen Şifre" class="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-amber-500 text-amber-400">
            </div>
            <button onclick="yeniKombiEkle()" class="w-full bg-amber-600 hover:bg-amber-500 text-xs py-2 rounded-lg font-bold transition shadow-lg shadow-amber-900/20">Sisteme ve Filoya Entegre Et</button>
        </div>

        <div class="space-y-2">
            <h2 class="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
                <i class="fa-solid fa-satellite-dish"></i> Aktif Filo İzleme Ekranı
            </h2>
            <div id="fleet-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <div class="col-span-full text-center py-8 text-sm text-gray-500 bg-gray-950 rounded-xl border border-gray-800 border-dashed">
                    Filonun anlık durumunu görmek için lütfen yetkili girişi yapın.
                </div>
            </div>
        </div>

        <div id="control-section" class="hidden border-t border-gray-800 pt-5 space-y-4">
            <div class="bg-gray-950 p-4 rounded-xl border border-blue-900/30 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h3 id="selected-kombi-title" class="text-base font-bold text-blue-400">Seçili Kombi</h3>
                    <p class="text-[11px] text-gray-400">Cihaz ID: <span id="selected-kombi-id" class="font-mono text-gray-300">--</span></p>
                </div>
                <div class="flex items-center gap-3 bg-gray-900 px-4 py-2 rounded-lg border border-gray-800 w-full md:w-auto justify-between">
                    <span class="text-xs font-bold">Hedef Sıcaklık: <span id="set-val" class="text-blue-400 ml-1">45°C</span></span>
                    <input type="range" id="set-slider" min="30" max="65" value="45" class="accent-blue-500 h-1.5 w-24">
                    <button onclick="komutGonder('setpoint', document.getElementById('set-slider').value)" class="bg-blue-600 hover:bg-blue-500 text-xs px-3 py-1 rounded font-bold transition">Gönder</button>
                </div>
            </div>

            <div id="tech-tools" class="hidden bg-gray-950 p-4 rounded-xl border border-gray-800 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                <div class="flex justify-between items-center bg-gray-900 p-3 rounded-lg border border-gray-800">
                    <span>P01: Max Fan (RPM):</span>
                    <div class="flex gap-1">
                        <input type="number" id="p01-in" class="w-16 bg-gray-800 border border-gray-700 text-center rounded text-amber-400 py-0.5">
                        <button onclick="komutGonder('p01', document.getElementById('p01-in').value)" class="bg-amber-600 px-2 py-0.5 rounded font-bold">Yaz</button>
                    </div>
                </div>
                <div class="flex justify-between items-center bg-gray-900 p-3 rounded-lg border border-gray-800">
                    <span>P02: Pompa Gecikme (Sn):</span>
                    <div class="flex gap-1">
                        <input type="number" id="p02-in" class="w-16 bg-gray-800 border border-gray-700 text-center rounded text-amber-400 py-0.5">
                        <button onclick="komutGonder('p02', document.getElementById('p02-in').value)" class="bg-amber-600 px-2 py-0.5 rounded font-bold">Yaz</button>
                    </div>
                </div>
                <div class="flex gap-1 items-center justify-between bg-gray-900 p-2 rounded-lg border border-gray-800">
                    <button onclick="komutGonder('error', 1)" class="bg-red-950/40 hover:bg-red-900/80 border border-red-900 py-1.5 px-2 rounded text-[10px] font-bold text-red-300 transition flex-1">E01 Tetikle</button>
                    <button onclick="komutGonder('error', 4)" class="bg-red-950/40 hover:bg-red-900/80 border border-red-900 py-1.5 px-2 rounded text-[10px] font-bold text-red-300 transition flex-1">E04 Tetikle</button>
                    <button onclick="komutGonder('error', 0)" class="bg-emerald-950/40 hover:bg-emerald-900/80 border border-emerald-900 py-1.5 px-2 rounded text-[10px] font-bold text-emerald-300 transition flex-1">Resetle</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let mevcutKullanici = "";
        let mevcutSifre = "";
        let aktifCihazId = "";
        let izinliCihazlarListesi = [];

        // CANLI VERİ GÜNCELLEME MOTORU (TÜM KARTLARI YENİLER)
        setInterval(async () => {
            if(izinliCihazlarListesi.length === 0) return;

            let gridContainer = document.getElementById("fleet-grid");
            let htmlIcerik = "";

            for(let cihaz of izinliCihazlarListesi) {
                try {
                    let res = await fetch(`/api/durum/${cihaz.id}`);
                    if(res.status !== 200) continue;
                    let data = await res.json();

                    let kartRengi = "border-gray-800 bg-gray-950";
                    let durumMetni = "💤 Standby";
                    let durumRengi = "text-gray-400";
                    let alevIcon = "";

                    if (data.error !== 0) {
                        kartRengi = "border-red-900/80 bg-red-950/20";
                        durumMetni = `⚠️ ARIZA: E${data.error}`;
                        durumRengi = "text-red-400 font-black animate-pulse";
                    } else if (data.flame === 1) {
                        kartRengi = "border-emerald-900/50 bg-emerald-950/10";
                        durumMetni = "🔥 Kombi Yanıyor";
                        durumRengi = "text-emerald-400 font-bold";
                        alevIcon = "text-orange-500";
                    }

                    let seciliBorder = (aktifCihazId === cihaz.id) ? "ring-2 ring-blue-500 shadow-blue-900/30" : "";

                    htmlIcerik += `
                        <div onclick="cihazSec('${cihaz.id}', '${data.isim}')" class="p-4 rounded-xl border transition cursor-pointer transform hover:scale-[1.02] ${kartRengi} ${seciliBorder}">
                            <div class="flex justify-between items-start">
                                <span class="text-xs font-bold text-gray-300 block truncate max-w-[150px]">${data.isim}</span>
                                <i class="fa-solid fa-fire ${alevIcon} text-xs"></i>
                            </div>
                            <span class="text-[10px] font-mono text-gray-500 block">${cihaz.id}</span>
                            <div class="mt-4 flex justify-between items-baseline">
                                <span class="text-3xl font-black tracking-tight ${data.error !== 0 ? 'text-red-400':'text-gray-100'}">${data.temp}°C</span>
                                <span class="text-[10px] font-bold bg-gray-900 px-2 py-0.5 rounded border border-gray-800 text-blue-400">Hedef: ${data.setpoint}°C</span>
                            </div>
                            <div class="mt-2 pt-2 border-t border-gray-900 flex justify-between text-[10px]">
                                <span class="${durumRengi}">${durumMetni}</span>
                                <span class="text-gray-500">P01: ${data.p01}</span>
                            </div>
                        </div>
                    `;
                } catch (err) { console.error(err); }
            }
            gridContainer.innerHTML = htmlIcerik;
        }, 1500);

        function cihazSec(id, isim) {
            aktifCihazId = id;
            document.getElementById("control-section").classList.remove("hidden");
            document.getElementById("selected-kombi-title").innerText = isim;
            document.getElementById("selected-kombi-id").innerText = id;
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
                mevcutKullanici = u; mevcutSifre = p;
                izinliCihazlarListesi = data.cihazlar;

                document.getElementById("auth-level").innerText = data.rol;
                document.getElementById("login-area").classList.add("hidden");
                document.getElementById("logout-btn").classList.remove("hidden");

                if(data.rol === "TEKNİSYEN" || data.rol === "YÖNETİCİ") {
                    document.getElementById("tech-tools").classList.remove("hidden");
                }
                if(data.rol === "YÖNETİCİ") {
                    document.getElementById("admin-add-section").classList.remove("hidden");
                }
                if(data.cihazlar.length > 0) {
                    cihazSec(data.cihazlar[0].id, data.cihazlar[0].isim);
                }
            } else {
                alert("Hatalı Giriş Bilgileri!");
            }
        }

        async function yeniKombiEkle() {
            let kid = document.getElementById("new-kombi-id").value.trim();
            let kname = document.getElementById("new-kombi-name").value.trim();
            let tuser = document.getElementById("new-tech-user").value.trim();
            let tpass = document.getElementById("new-tech-pass").value.trim();

            if(!kid || !kname || !tuser || !tpass) { alert("Lütfen tüm alanları doldurun!"); return; }

            let response = await fetch('/api/kombi-ekle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: mevcutKullanici, sifre: mevcutSifre,
                    id: kid, isim: kname, tech_user: tuser, tech_pass: tpass
                })
            });
            let data = await response.json();
            if(data.status === "ok") {
                alert("Yeni İstasyon ve Teknisyen Başarıyla Filoya Eklendi!");
                izinliCihazlarListesi = data.cihazlar;
                document.getElementById("new-kombi-id").value = "";
                document.getElementById("new-kombi-name").value = "";
                document.getElementById("new-tech-user").value = "";
                document.getElementById("new-tech-pass").value = "";
                cihazSec(kid, kname);
            } else { alert(data.message); }
        }

        function cikisYap() {
            mevcutKullanici = ""; mevcutSifre = ""; aktifCihazId = ""; izinliCihazlarListesi = [];
            document.getElementById("username").value = ""; document.getElementById("pass").value = "";
            document.getElementById("auth-level").innerText = "MİSAFİR";
            document.getElementById("login-area").classList.remove("hidden");
            document.getElementById("logout-btn").classList.add("hidden");
            document.getElementById("control-section").classList.add("hidden");
            document.getElementById("admin-add-section").classList.add("hidden");
            document.getElementById("tech-tools").classList.add("hidden");
            document.getElementById("fleet-grid").innerHTML = `
                <div class="col-span-full text-center py-8 text-sm text-gray-500 bg-gray-950 rounded-xl border border-gray-800 border-dashed">
                    Filonun anlık durumunu görmek için lütfen yetkili girişi yapın.
                </div>`;
        }

        async function komutGonder(parametre, deger) {
            if(!aktifCihazId || deger === "") return;
            let response = await fetch('/api/komut', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: mevcutKullanici, sifre: mevcutSifre,
                    cihaz_id: aktifCihazId, parametre: parametre, deger: parseInt(deger)
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
