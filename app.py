# app.py
from flask import Flask, render_template_string, request, jsonify
import threading
import time
import os

app = Flask(__name__)

# --- GÜVENLİK AYARI ---
TEKNISYEN_SIFRESI = os.environ.get("TEKNISYEN_SIFRESI", "1234")

# --- SANAL KOMBİ DURUMU ---
kombi_durumu = {
    "temp": 42,
    "setpoint": 45,
    "flame": 0,
    "error": 0,
    "p01": 3500,
    "p02": 120,
    "mode": 0
}


# --- KOMBİ SİMÜLASYON MOTORU ---
def kombi_fizik_motoru():
    while True:
        if kombi_durumu["error"] != 0:
            kombi_durumu["flame"] = 0
            if kombi_durumu["temp"] > 22:
                kombi_durumu["temp"] -= 1
        elif kombi_durumu["temp"] < kombi_durumu["setpoint"]:
            kombi_durumu["flame"] = 1
            kombi_durumu["temp"] += 1
        elif kombi_durumu["temp"] >= kombi_durumu["setpoint"]:
            kombi_durumu["flame"] = 0
            if kombi_durumu["temp"] > 20:
                kombi_durumu["temp"] -= 1

        time.sleep(2)


# --- WEB ARAYÜZÜ (HTML) ---
WEB_ARAYUZU = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E.C.A. Kombi Global Simülatör</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
</head>
<body class="bg-gray-950 text-gray-100 p-4 min-h-screen flex flex-col items-center select-none">
    <div class="w-full max-w-md bg-gray-900 rounded-2xl shadow-2xl border border-gray-800 p-5 space-y-5 mt-4">
        <div class="flex justify-between items-center border-b border-gray-800 pb-3">
            <div>
                <h1 class="text-xl font-bold text-blue-500">E.C.A. GLOBAL</h1>
                <p class="text-xs text-gray-400">Yetki: <span id="auth-level" class="text-emerald-400 font-bold">KULLANICI</span></p>
            </div>
            <div id="login-area" class="flex gap-1">
                <input type="password" id="pass" placeholder="Şifre" class="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-xs w-20 text-center">
                <button onclick="girisYap()" class="bg-blue-600 text-xs px-2 py-1 rounded-lg font-bold">Giriş</button>
            </div>
            <button id="logout-btn" onclick="cikisYap()" class="hidden bg-red-900 text-xs px-3 py-1 rounded-lg font-bold">Çıkış</button>
        </div>

        <div class="bg-gray-950 rounded-xl p-5 text-center border border-gray-800 relative">
            <div id="live-temp" class="text-6xl font-black text-emerald-400">-- °C</div>
            <div class="text-xs text-gray-400 mt-1">Uzak Kazan Sıcaklığı</div>
            <div id="live-flame" class="text-xs mt-2 font-bold text-gray-500">Durum: Bekleniyor...</div>
        </div>

        <div id="alert-bar" class="w-full text-center py-2 rounded-lg font-bold text-xs bg-emerald-950 text-emerald-300">
            Bulut Bağlantısı Aktif
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
            <h3 class="text-sm font-bold text-amber-500">🛠️ Teknisyen Servis Parametreleri</h3>
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
        let yetki = "KULLANICI";
        let tokenSifre = ""; 

        setInterval(async () => {
            try {
                let res = await fetch('/api/durum');
                let data = await res.json();
                document.getElementById("live-temp").innerText = data.temp + " °C";
                document.getElementById("live-flame").innerText = data.flame === 1 ? "Durum: 🔥 Kombi Yanıyor" : "Durum: 💤 Standby";

                let alertBar = document.getElementById("alert-bar");
                if (data.error !== 0) {
                    alertBar.innerText = "⚠️ ARIZA: E" + data.error;
                    alertBar.className = "w-full text-center py-2 rounded-lg font-bold text-xs bg-red-900 text-red-100";
                } else {
                    alertBar.innerText = yetki === "TEKNİSYEN" ? "🛠️ Servis Modu Aktif" : "Sistem Normal";
                    alertBar.className = yetki === "TEKNİSYEN" ? "w-full text-center py-2 rounded-lg font-bold text-xs bg-amber-950 text-amber-300" : "w-full text-center py-2 rounded-lg font-bold text-xs bg-emerald-950 text-emerald-300";
                }
                if (yetki === "TEKNİSYEN") {
                    document.getElementById("p01-in").placeholder = data.p01;
                    document.getElementById("p02-in").placeholder = data.p02;
                }
            } catch (err) {
                console.error("Veri okuma hatası", err);
            }
        }, 1500);

        async function komutGonder(parametre, deger) {
            if(deger === undefined || deger === "") return;

            // İstek gövdesini dinamik hazırlıyoruz
            let payload = {
                parametre: parametre,
                deger: parseInt(deger)
            };

            // Eğer setpoint DEĞİLSE (yani teknisyen parametresiyse) şifreyi ekle
            if (parametre !== "setpoint") {
                payload.sifre = tokenSifre;
            }

            let response = await fetch('/api/komut', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            let resData = await response.json();
            if(resData.status === "error") {
                alert("Hata: " + resData.message);
                if(response.status === 403) {
                    cikisYap();
                }
            } else if(parametre === "error" && parseInt(deger) === 0) {
                alert("Arıza başarıyla resetlendi! Kombi normal çalışma moduna dönüyor.");
            }
        }

        function girisYap() {
            let inputPass = document.getElementById("pass").value;
            if(inputPass !== "") {
                yetki = "TEKNİSYEN";
                tokenSifre = inputPass;
                document.getElementById("auth-level").innerText = "TEKNİSYEN";
                document.getElementById("login-area").classList.add("hidden");
                document.getElementById("logout-btn").classList.remove("hidden");
                document.getElementById("tech-section").classList.remove("hidden");
            } else { alert("Lütfen şifre girin!"); }
        }

        function cikisYap() {
            yetki = "KULLANICI";
            tokenSifre = "";
            document.getElementById("pass").value = "";
            document.getElementById("auth-level").innerText = "KULLANICI";
            document.getElementById("login-area").classList.remove("hidden");
            document.getElementById("logout-btn").classList.add("hidden");
            document.getElementById("tech-section").classList.add("hidden");
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


@app.route('/api/durum', methods=['GET'])
def durum_ver():
    return jsonify(kombi_durumu)


@app.route('/api/komut', methods=['POST'])
def komut_al():
    req_data = request.get_json() or {}
    parametre = req_data.get("parametre")
    deger = req_data.get("deger")

    # 1. Genel Kullanıcı İşlemleri (Şifre parametresi aranmaz)
    if parametre == "setpoint":
        try:
            kombi_durumu["setpoint"] = int(deger)
            return jsonify({"status": "ok"})
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Geçersiz setpoint değeri"}), 400

    # 2. Teknisyen İşlemleri (Şifre zorunludur)
    elif parametre in ["p01", "p02", "error"]:
        sifre = req_data.get("sifre", "")
        if str(sifre) != str(TEKNISYEN_SIFRESI):
            return jsonify({"status": "error", "message": "Yetkisiz İşlem! Geçersiz şifre."}), 403

        try:
            deger = int(deger)
            if parametre == "p01":
                kombi_durumu["p01"] = deger
            elif parametre == "p02":
                kombi_durumu["p02"] = deger
            elif parametre == "error":
                kombi_durumu["error"] = deger
                if deger != 0:
                    kombi_durumu["temp"] = 22
                else:
                    kombi_durumu["temp"] = 35
                    kombi_durumu["setpoint"] = 45
                    kombi_durumu["flame"] = 0
            return jsonify({"status": "ok"})
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Geçersiz parametre değeri"}), 400

    return jsonify({"status": "error", "message": "Bilinmeyen istek"}), 400


if __name__ == '__main__':
    threading.Thread(target=kombi_fizik_motoru, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
