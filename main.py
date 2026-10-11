import os
import time
import random
import threading
from datetime import datetime
from curl_cffi import requests as cffi_requests

# LÊ AS VARIÁVEIS DE AMBIENTE DO RAILWAY (ou usa padrão se não encontrar)
TARGET_URL = os.getenv("TARGET_URL", "https://guns.lol/teste")
THREADS = int(os.getenv("THREADS", "10"))
VIEW_COUNT = int(os.getenv("VIEW_COUNT", "1000"))

def log(msg, level="INFO"):
    icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARN": "⚠️"}
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {icons.get(level, 'ℹ️')} {msg}")

def get_free_proxies():
    log("Buscando proxies públicas...", "INFO")
    try:
        r = cffi_requests.get(
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all", 
            impersonate="chrome120", 
            timeout=10
        )
        proxies = [p.strip() for p in r.text.split('\n') if p.strip() and ':' in p]
        log(f"Encontradas {len(proxies)} proxies brutas. Testando as 100 mais rápidas...", "INFO")
        
        valid_proxies = []
        for p in proxies[:100]:
            try:
                start = time.time()
                cffi_requests.get(
                    "https://httpbin.org/ip", 
                    proxies={"http": f"http://{p}", "https": f"http://{p}"}, 
                    timeout=4, 
                    impersonate="chrome120"
                )
                if time.time() - start < 4:
                    valid_proxies.append(p)
            except:
                pass
        log(f"Proxies válidas prontas para uso: {len(valid_proxies)}", "SUCCESS")
        return valid_proxies
    except Exception as e:
        log(f"Falha ao buscar proxies: {e}", "ERROR")
        return []

def send_view(proxy, view_id):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8"
    }
    proxy_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None
    
    try:
        start = time.time()
        r = cffi_requests.get(
            TARGET_URL, 
            headers=headers, 
            proxies=proxy_dict, 
            timeout=10, 
            impersonate="chrome120"
        )
        latency = time.time() - start
        
        if r.status_code == 200 and "cloudflare" not in r.text.lower() and "challenge" not in r.text.lower():
            log(f"View #{view_id} SUCESSO via {proxy or 'IP DIRETO'} ({latency:.2f}s)", "SUCCESS")
            return True
        else:
            log(f"View #{view_id} BLOQUEADA (CF/403) via {proxy or 'IP DIRETO'}", "ERROR")
            return False
    except Exception as e:
        log(f"View #{view_id} FALHA via {proxy or 'IP DIRETO'}: {str(e)[:40]}", "ERROR")
        return False

def worker(proxy_list, view_id):
    proxy = random.choice(proxy_list) if proxy_list else None
    send_view(proxy, view_id)
    time.sleep(random.uniform(1.5, 3.5)) # Delay humano entre requisições

def main_cycle():
    log(f"INICIANDO CICLO PARA: {TARGET_URL}", "INFO")
    log(f"Meta: {VIEW_COUNT} views com {THREADS} threads", "INFO")
    
    proxy_list = get_free_proxies()
    if not proxy_list:
        log("Nenhuma proxy válida encontrada. Usando IP direto do Railway (risco de rate-limit).", "WARN")
        proxy_list = [None]

    completed = 0
    while completed < VIEW_COUNT:
        threads = []
        batch_size = min(THREADS, VIEW_COUNT - completed)
        
        for i in range(batch_size):
            t = threading.Thread(target=worker, args=(proxy_list, completed + i + 1), daemon=True)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
            
        completed += batch_size
        log(f"Progresso: {completed}/{VIEW_COUNT} views processadas.", "INFO")
        time.sleep(random.uniform(3.0, 6.0)) # Pausa entre lotes

    log("Ciclo concluído. Aguardando 5 minutos para o próximo...", "WARN")
    time.sleep(300)

if __name__ == "__main__":
    while True:
        main_cycle()