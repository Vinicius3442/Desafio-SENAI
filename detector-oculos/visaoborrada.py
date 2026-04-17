import os
import json
import base64
import time
import math
import cv2
import numpy as np

# --- BIBLIOTECAS DE CRIPTOGRAFIA E IA ---
try:
    from cryptography.fernet import Fernet
except ImportError:
    print("ERRO CRITICO: Pacote 'cryptography' nao instalado. A execucao ficara comprometida.")
    print("Por favor, execute no terminal: pip install cryptography")
    time.sleep(2)

try:
    from ultralytics import YOLO
    print("[SISTEMA AR] Motor Neural Avancado (YOLOv8) carregado com sucesso!")
    # O YOLOv8 nano é extremamente veloz e preciso para objetos no ambiente real.
    yolo_model = YOLO("yolov8n.pt") 
except ImportError:
    print("ALERTA: Pacote ultralytics não encontrado. Usando detecções antigas de baixa precisão.")
    yolo_model = None
except Exception as e:
    print(f"ALERTA: Falha no YOLO: {e}")
    yolo_model = None

# Configuração Padrão de Rosto (Continua usando o anterior, já que seu desempenho é incrível)
PROTO_PATH = "deploy.prototxt"
MODEL_PATH = "res10_300x300_ssd_iter_140000.caffemodel"
try:
    face_net = cv2.dnn.readNetFromCaffe(PROTO_PATH, MODEL_PATH)
except:
    print("ALERTA: Falha ao carregar modelo de rostos (Caffe SSD).")
    face_net = None


# --- GERENCIAMENTO DE CHAVES E CRIPTOGRAFIA ---
def get_or_create_key():
    """Gera e armazena a chave de criptografia de ponta a ponta que o Servidor Seguro usa."""
    key_path = "master_key.key"
    if not os.path.exists(key_path):
        key = Fernet.generate_key()
        with open(key_path, "wb") as key_file:
            key_file.write(key)
        print("[SEGURANCA] Nova chave mestra de criptografia gerada e persistida.")
    else:
        with open(key_path, "rb") as key_file:
            key = key_file.read()
    return key

def save_secure_snapshot(frame, stats):
    """
    Empacota a captura, metadados sensíveis (Ex: Localização, Hora, Dispositivo),
    transforma tudo em JSON e criptografa a nivel militar (AES via Fernet).
    """
    key = get_or_create_key()
    fernet = Fernet(key)
    
    # Comprime a imagem (Censurada) e codifica com Base64
    _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    
    # Simula metadados sensíveis que os óculos colheriam do ambiente
    payload = {
        "device_id": "OCULOS_AR_OPERACIONAL_01",
        "timestamp": time.time(),
        "local_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "gps_telemetry": {"lat": -23.550520, "lng": -46.633308, "alt": "760m"},
        "status_seguranca": "CENSURA ATIVA",
        "entities_blocked": stats,
        "image_data": jpg_as_text
    }
    
    # Converte e criptografa
    json_data = json.dumps(payload).encode('utf-8')
    encrypted_payload = fernet.encrypt(json_data)
    
    # Salva no disco rígido fisicamente blindado
    filename = f"captura_segura_{int(time.time())}.secure"
    with open(filename, "wb") as f:
        f.write(encrypted_payload)
        
    return filename


# --- UI E CORES ---
COLOR_TEXT = (255, 255, 255)
COLOR_FACE = (80, 100, 255)  
COLOR_SCREEN = (255, 200, 0) 
COLOR_DOC = (0, 215, 255)    
COLOR_HUD = (180, 255, 130)  
COLOR_WARNING = (0, 0, 255)  

def apply_secure_redaction(img, x, y, w, h):
    ih, iw = img.shape[:2]
    margin = int(max(w, h) * 0.05)
    x, y = max(0, x - margin), max(0, y - margin)
    w, h = min(w + margin*2, iw - x), min(h + margin*2, ih - y)
    
    if w > 5 and h > 5:
        roi = img[y:y+h, x:x+w]
        
        pz = max(15, min(w, h) // 10)
        small = cv2.resize(roi, (max(1, w // pz), max(1, h // pz)), interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
        blurred = cv2.GaussianBlur(pixelated, (51, 51), 0)
        
        tint = np.full_like(blurred, (15, 15, 20))
        for i in range(0, w + h, 20):
             cv2.line(tint, (i, 0), (0, i), (30, 30, 40), 2)

        secure_roi = cv2.addWeighted(blurred, 0.3, tint, 0.7, 0)
        img[y:y+h, x:x+w] = secure_roi

def draw_ar_box(img, x, y, w, h, color, label, frame_count):
    thickness = 2
    length = max(15, int(min(w, h) * 0.15))
    pulse = (math.sin(frame_count * 0.15) + 1) / 2 
    alpha = 0.1 + (0.15 * pulse)

    pts = [
        ((x, y), (x + length, y)), ((x, y), (x, y + length)),
        ((x + w, y), (x + w - length, y)), ((x + w, y), (x + w, y + length)),
        ((x, y + h), (x + length, y + h)), ((x, y + h), (x, y + h - length)),
        ((x + w, y + h), (x + w - length, y + h)), ((x + w, y + h), (x + w, y + h - length))
    ]
    for (p1, p2) in pts:
        cv2.line(img, p1, p2, color, thickness, cv2.LINE_AA)

    overlay = img.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)

    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale = max(0.4, min(0.7, w / 350.0))
    (tv_w, tv_h), _ = cv2.getTextSize(label, font, font_scale, 1)
    
    pad = 6
    tx, ty = x, y - 8
    if ty - tv_h - pad*2 < 0: ty = y + h + tv_h + pad*2

    cv2.rectangle(img, (tx, ty - tv_h - pad*2), (tx + tv_w + pad*2, ty), color, -1)
    cv2.rectangle(img, (tx, ty - tv_h - pad*2), (tx + tv_w + pad*2, ty), COLOR_TEXT, 1)
    cv2.putText(img, label, (tx + pad, ty - pad), font, font_scale, (0, 0, 0), 1, cv2.LINE_AA)

    sec_label = "BLOQUEADO"
    sec_scale = max(0.5, min(1.2, w / 250.0))
    (sw, sh), _ = cv2.getTextSize(sec_label, font, sec_scale, 2)
    sx, sy = x + (w - sw) // 2, y + (h + sh) // 2
    
    if w > sw + 20 and h > sh + 20: 
        s_overlay = img.copy()
        cv2.rectangle(s_overlay, (sx - 10, sy - sh - 10), (sx + sw + 10, sy + 10), (0, 0, 50), -1) 
        cv2.addWeighted(s_overlay, 0.7, img, 0.3, 0, img)
        cv2.putText(img, sec_label, (sx, sy), font, sec_scale, COLOR_TEXT, 2, cv2.LINE_AA)

def draw_hud_overlay(img, stats, frame_count):
    h, w = img.shape[:2]
    font = cv2.FONT_HERSHEY_DUPLEX
    
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (w, 50), (12, 12, 18), -1)
    cv2.rectangle(overlay, (0, h - 45), (w, h), (12, 12, 18), -1)
    cv2.addWeighted(overlay, 0.9, img, 0.1, 0, img)

    cx, cy = w // 2, h // 2
    cv2.line(img, (cx, cy - 20), (cx, cy + 20), (255, 255, 255), 1)
    cv2.line(img, (cx - 20, cy), (cx + 20, cy), (255, 255, 255), 1)
    pulse_radius = 25 + int(math.sin(frame_count * 0.1) * 3)
    cv2.circle(img, (cx, cy), pulse_radius, COLOR_HUD, 1, cv2.LINE_AA)
    
    cv2.putText(img, "> BRIDGE AR: OMNI PRIVACY", (15, 22), font, 0.5, COLOR_HUD, 1, cv2.LINE_AA)
    cv2.putText(img, f"CMD: PRESSIONE 'S' P/ UPLINK CRIPTOGRAFADO", (15, 40), font, 0.4, (100, 255, 255), 1, cv2.LINE_AA)
    
    t_str = time.strftime("%H:%M:%S")
    cv2.putText(img, f"CONEXAO SEGURA | {t_str}", (w - 270, 22), font, 0.5, COLOR_SCREEN, 1, cv2.LINE_AA)
    cv2.line(img, (w - 270, 28), (w - 15, 28), COLOR_SCREEN, 1)

    total_blocks = stats['faces'] + stats['screens'] + stats['docs']
    status_text = "SCANNER ATIVO: AMBIENTE LIMPO"
    status_col = COLOR_HUD
    
    if total_blocks > 0:
        status_text = f"ALERTA: {total_blocks} INFO(S) PROTEGIDA(S) EM TEMPO REAL"
        status_col = COLOR_WARNING if (frame_count % 20 < 10) else (255, 220, 220)

    cv2.putText(img, status_text, (15, h - 18), font, 0.5, status_col, 1, cv2.LINE_AA)
    
    info_str = f"ROSTOS: {stats['faces']} | TELAS: {stats['screens']} | DOCS: {stats['docs']}"
    str_w = cv2.getTextSize(info_str, font, 0.5, 1)[0][0]
    cv2.putText(img, info_str, (w - str_w - 15, h - 18), font, 0.5, COLOR_TEXT, 1, cv2.LINE_AA)

def is_overlapping(box1, box2):
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    return not (x1 + w1 < x2 or x2 + w2 < x1 or y1 + h1 < y2 or y2 + h2 < y1)

def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    frame_count = 0
    
    # Inicializa chave mestra caso não exista
    get_or_create_key()
    
    while True:
        ret, frame = cap.read()
        if not ret or frame is None: 
            time.sleep(0.1)
            continue
            
        frame_count += 1
        display_frame = frame.copy()
        h, w = frame.shape[:2]
        
        stats = {'faces': 0, 'screens': 0, 'docs': 0}
        protected_regions = []

        # 1. RASTREAMENTO FACIAL (CAFFE SSD)
        if face_net:
            blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
            face_net.setInput(blob)
            detections = face_net.forward()
            for i in range(detections.shape[2]):
                conf = detections[0, 0, i, 2]
                if conf > 0.50: 
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (x1, y1, x2, y2) = box.astype("int")
                    
                    m_x, m_y = int((x2 - x1)*0.15), int((y2 - y1)*0.20)
                    bx, by = max(0, x1 - m_x), max(0, y1 - m_y)
                    bw_rect, bh_rect = min(w - bx, (x2 - x1) + m_x*2), min(h - by, (y2 - y1) + m_y*2)
                    
                    protected_regions.append((bx, by, bw_rect, bh_rect))
                    apply_secure_redaction(display_frame, bx, by, bw_rect, bh_rect)
                    draw_ar_box(display_frame, bx, by, bw_rect, bh_rect, COLOR_FACE, f"ROSTO [{int(conf*100)}%]", frame_count)
                    stats['faces'] += 1

        # 2. DETECÇÃO DE APARELHOS E DOCS COM INTELIGENCIA AVANCADA (YOLOv8)
        if yolo_model:
            # Classes COCO -> 62: tv, 63: laptop, 67: cell phone, 73: book
            results = yolo_model.predict(frame, verbose=False, conf=0.45)
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                if cls_id in [62, 63, 67]:
                    label_str = f"MONITOR/CELULAR"
                    color = COLOR_SCREEN
                elif cls_id == 73:
                    label_str = "DOC FISICO / LIVRO"
                    color = COLOR_DOC
                else:
                    continue
                
                # Coordenadas do YOLO
                y_x1, y_y1, y_x2, y_y2 = map(int, box.xyxy[0])
                y_w, y_h = y_x2 - y_x1, y_y2 - y_y1
                
                # Verificação de sobreposição
                overlap = False
                c_box = (y_x1, y_y1, y_w, y_h)
                for pb in protected_regions:
                    if is_overlapping(c_box, pb):
                        overlap = True
                        break
                if overlap: continue
                
                protected_regions.append(c_box)
                apply_secure_redaction(display_frame, y_x1, y_y1, y_w, y_h)
                draw_ar_box(display_frame, y_x1, y_y1, y_w, y_h, color, f"{label_str} [{int(conf*100)}%]", frame_count)
                
                if cls_id in [62, 63, 67]: stats['screens'] += 1
                else: stats['docs'] += 1

        draw_hud_overlay(display_frame, stats, frame_count)

        cv2.imshow("Sistema Oculos AR - Filtro Privado", display_frame)
        
        # Leitura de botões (S para salvar seguro)
        key_press = cv2.waitKey(1) & 0xFF
        if key_press == ord('q'): 
            break
        elif key_press == ord('s') or key_press == ord('S'):
            # Efeito Pós-Snap: Mostra a mensagem antes de travar processando
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(display_frame, ">> UPLINK CRIPTOGRAFADO EM ANDAMENTO...", (w//2 - 250, h//2), font, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.imshow("Sistema Oculos AR - Filtro Privado", display_frame)
            cv2.waitKey(1)
            
            # Gera a foto censurada e empacota + criptografa na hora
            file_name_enc = save_secure_snapshot(display_frame, stats)
            print(f"[AR GLASS] Snapshot salvo e criptografado com sucesso em '{file_name_enc}'")
            
            # Flash Effect imersivo de confirmação
            flash = np.ones_like(display_frame) * 200 # Tela clara simulando "flash" de foto
            cv2.imshow("Sistema Oculos AR - Filtro Privado", flash)
            cv2.waitKey(100) # Mantém por 100ms

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()