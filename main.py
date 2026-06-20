import json
import urllib3
import os 
from datetime import datetime

http = urllib3.PoolManager()

def lambda_handler(event, context):    
    # Recuperiamo il token una volta sola qui
    tg_token = os.environ.get('TELEGRAM_TOKEN')

    # Se c'è un 'body', la chiamata arriva da Telegram (API Gateway)
    if 'body' in event:
        return handle_message(event, tg_token)
    
    # Altrimenti è la sveglia di EventBridge
    return send_update(tg_token)

def handle_message(event, tg_token):
    try:
        body = json.loads(event['body'])
        
        # --- 1. FILTRI DI SICUREZZA ---
        sender_id = "Sconosciuto"
        if 'message' in body:
            sender_id = str(body['message']['chat']['id'])
        elif 'callback_query' in body:
            sender_id = str(body['callback_query']['message']['chat']['id'])
            
        my_id = os.environ.get('TELEGRAM_CHAT_ID')

        # WHITELIST: Se non sei tu, blocca e rispondi 200 (per fermare Telegram)
        if sender_id != my_id:
            print(f"⛔ Accesso negato all'ID: {sender_id}")
            return {'statusCode': 200, 'body': 'User unauthorized'}

        # ANTI-LOOP: Ignora i messaggi dei bot
        is_bot = False
        if 'message' in body:
            is_bot = body['message'].get('from', {}).get('is_bot', False)
        if is_bot:
            return {'statusCode': 200, 'body': 'Ignored bot message'}

        # --- 2. GESTIONE MESSAGGI ---
        if 'message' in body:
            chat_id = body['message']['chat']['id']
            text = body['message'].get('text', '')
            
            if text == "/start":
                return send_telegram_message(tg_token, chat_id, "Benvenuto! Scegli un'azione:")
            
            # Risposta di cortesia per altri messaggi
            return send_telegram_message(tg_token, chat_id, "Comando non riconosciuto.")

        # --- 3. GESTIONE BOTTONI ---
        elif 'callback_query' in body:
            callback_id = body['callback_query']['id']
            # chat_id = body['callback_query']['message']['chat']['id'] # Non serve se usiamo send_update
            data = body['callback_query']['data']
            
            # Conferma immediata a Telegram (spegne la rotellina)
            answer_callback(tg_token, callback_id, "Elaborazione...")

            if data == "CMD_UPD":
                return send_update(tg_token)
            
            if data == "CMD_INFO_PSA":
                message = get_weather(True)
                return send_telegram_message(tg_token, my_id, message)
            if data == "CMD_INFO_LCA":
                message = get_weather(None)
                return send_telegram_message(tg_token, my_id, message)
            if data == "CMD_INFO_TRADE":
                message = get_trade()
                return send_telegram_message(tg_token, my_id, message)
            
            return {'statusCode': 200, 'body': "Button handled"}           

    except Exception as e:
        print(f"Errore critico handle_message: {e}")
        # Ritorniamo 200 anche in caso di errore per evitare che Telegram riprovi all'infinito
        return {'statusCode': 200, 'body': str(e)}

def send_telegram_message(token, chat_id, text):
    """Funzione che spedisce il messaggio a Telegram con tastiera"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "ℹ️ Info su Pisa", "callback_data": "CMD_INFO_PSA"},
                {"text": "ℹ️ Info su Lucca", "callback_data": "CMD_INFO_LCA"},
            ],
            [
                {"text": "📈​ Info su Trade", "callback_data": "CMD_INFO_TRADE"},
                {"text": "➕ Aggiornami adesso", "callback_data": "CMD_UPD"}
            ]
        ]
    }

    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": keyboard,
        "parse_mode": "Markdown"
    }
    
    try:
        resp = http.request('POST', url, body=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        print(f"Telegram status: {resp.status}")
        return {'statusCode': 200, 'body': 'Message sent'}
    except Exception as e:
        print(f"Errore invio Telegram: {e}")
        return {'statusCode': 200, 'body': 'Error sending message'}

def send_update(tg_token, pisa=False):
    tg_chat_id = os.environ.get('TELEGRAM_CHAT_ID')

    message = "bella fra!\n\n"
    message += get_weather(pisa)
    message += "\n\n"
    message += get_trade()

    if tg_token and tg_chat_id:
        # Qui usiamo una versione semplice di invio o quella con tastiera
        # Nota: send_telegram_message richiede (token, chat_id, text)
        send_telegram_message(tg_token, tg_chat_id, message)

    return {'statusCode': 200, 'body': json.dumps(message)}
    
def answer_callback(token, callback_id, text=None):
    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
        
    try:
        http.request('POST', url, body=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    except Exception as e:
        print(f"Errore answerCallback: {e}")

def get_weather(pisa):
    apiWeather_key = os.environ.get('OPENWEATHER_KEY')

    if pisa:
        city = "Pisa"
        lat = "43.43"
        lon = "10.24"
    else:
        city = "Lucca"
        lat = "43.50"
        lon = "10.30"
    url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&lang=it&appid={apiWeather_key}&units=metric"

    try:
        response = http.request('GET', url)
        data = json.loads(response.data.decode('utf-8'))
        
        temp = data['current']['temp']
        desc = data['current']['weather'][0]['description']

        icons = {
            "01d": " ☀️ ",
            "02d": " 🌤️ ",
            "03d": "⛅",
            "04d": " 🌥️ ",
            "09d": " 🌧️ ",
            "10d": " 🌦️ ",
            "11d": " 🌩️  ​",
            "13d": " 🌨️ ",
            "50d": " 🌫️ ",
            "01n": " ☀️ ",
            "02n": " 🌤️ ",
            "03n": "⛅",
            "04n": " 🌥️ ",
            "09n": " 🌧️ ",
            "10n": " 🌦️ ",
            "11n": " 🌩️​ ​",
            "13n": " 🌨️ ",
            "50n": " 🌫️ ",
        }

        if pisa or pisa is None:
            hours = data['hourly'][:10]
            result = []
            for h in hours:
                ts = h['dt']
                result.append({
                    "icon": icons[h['weather'][0]['icon']],
                    "time": datetime.fromtimestamp(ts).strftime('%H:%M %d-%m'),
                    "temp": h['temp'],
                    "desc": h['weather'][0]['description']
                })
                print(icons[h['weather'][0]['icon']],h['weather'][0]['icon'])

        message = f"🌡️ Info su meteo:​\nAdesso a {city} ci sono {temp}°C con {desc}."
        if pisa or pisa is None:
            message += "\n\n🌂​ Previsioni della giornata:"
            message += create_ascii_table_weather(result)

        return message 
    except Exception as e:
        print(f"Errore Meteo: {e}")
        # Importante: loggare l'errore ma ritornare 200 a Telegram se invocato via webhook
        return {'statusCode': 200, 'body': str(e)}
    
def get_trade():
    apiFinn_key = os.environ.get('FINNHUB_KEY')

    results = []
    symbols = ["SPY","IWM","GLD"]
    for s in symbols:
        results.append(get_stock_price(s,apiFinn_key))
    
    results.append(None)

    symbols = ["BINANCE:BTCEUR","BINANCE:SOLEUR","BINANCE:ETHEUR","BINANCE:XRPEUR","BINANCE:ADAEUR"]
    for s in symbols:
        results.append(get_stock_price(s,apiFinn_key))

    # Uniamo tutto in un'unica stringa con 'a capo'
    return "📈 Info su trade:\n" + create_ascii_table_trade(results)    

def get_stock_price(symbol, finnhub_token):
    # Nota: Rimuoviamo il try-except globale qui per gestirlo nel gruppo, 
    # oppure lo lasciamo per sicurezza. Lasciamolo semplice.
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={finnhub_token}"
    
    try:
        resp = http.request('GET', url)
        if resp.status != 200:
            return f"\n"
            
        data = json.loads(resp.data.decode('utf-8'))
        
        s = symbol[8:-3]
        if symbol == "SPY":
            s = "S&P"
        elif symbol == "IWM":
            s = "RS2K"
        elif symbol == "GLD":
            s = "GLD"

        change = data.get('dp', 0)
        icon = "🟢" if change >= 0 else "🔴"
        
        return {
            "symbol": s,
            "price": data.get('c', 0),
            "change": change,
            "icon": icon
        }
    except:
        return None
    
def create_ascii_table_trade(data_list):
    """
    Crea una tabella formattata per Telegram (Monospace).
    Usa:
    <  : allinea a sinistra
    >  : allinea a destra
    6, 9: larghezza fissa della colonna
    """
    if not data_list:
        return "Nessun dato disponibile."

    # 1. Intestazione (Header)
    # Asset: 6 spazi, sinistra | Price: 9 spazi, destra | %: 6 spazi, destra
    table = "```\n" # Apre il blocco codice Telegram
    table += f"{'ASSET':<6} {'Prezzo (€)':>9} {'%':>5} {'ST':^4}\n"
    table += "-" * 30 + "\n" # Linea divisoria

    # 2. Righe Dati
    for item in data_list:
        if item:
            sym = item['symbol'][:6] # Tronchiamo se troppo lungo
            price = f"{item['price']:.2f}" # 2 decimali
            change = f"{item['change']:.2f}"
            icon = item['icon']
            
            # Aggiungiamo il segno + se positivo per allineare meglio
            if item['change'] >= 0:
                change = f"+{change}"
            
            # {icon:^3}   -> L'icona occupa una casella di 3 spazi ed è centrata
            table += f"{sym:<6} {price:>9} {change:>6} {icon:^3}\n"
        else:
            table += "\n"
    table += "```"
    return table
    
def create_ascii_table_weather(data_list):
    """
    Crea una tabella formattata per Telegram (Monospace).
    Usa:
    <  : allinea a sinistra
    >  : allinea a destra
    6, 9: larghezza fissa della colonna
    """
    if not data_list:
        return "Nessun dato disponibile."

    # 1. Intestazione (Header)
    # Asset: 6 spazi, sinistra | Price: 9 spazi, destra | %: 6 spazi, destra
    table = "```\n" 
    table += f" {'St':<3}  {'Ora':<11} {'°C':<5} {'Descrizione':<12}\n"
    table += "-" * 35 + "\n" # Aumentato a 34 per coprire tutta la larghezza

    # Righe Dati
    for item in data_list:
        if item:
            icon = item['icon']
            ora = item['time'] # Stringa di 11 caratteri esatti
            
            descr = item['desc'][:18] 
            
            # Sicurezza: forziamo la temp a 1 numero decimale (es. 12.5)
            # così occupa sempre poco spazio e non rompe la colonna
            temp_val = float(item['temp'])
            temp = f"{temp_val:.1f}"

            # Costruzione riga
            table += f"{icon:^3} {ora:>11} {temp:>5} {descr:<18}\n"
        else:
            table += "\n"
    table += "```"
    return table
    