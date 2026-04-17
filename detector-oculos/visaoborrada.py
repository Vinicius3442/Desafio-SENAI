import cv2
import numpy as np
import time
import math

# --- CONFIGURAÇÕES DO SISTEMA ---
PROTO_PATH = "deploy.prototxt"
MODEL_PATH = "res10_300x300_ssd_iter_140000.caffemodel"
try:
    net = cv2.dnn.readNetFromCaffe(PROTO_PATH, MODEL_PATH)
except:
    print("ALERTA: Falha ao carregar modelo de IA para rostos (Caffe SSD).")
    net = None

# Paleta de Cores HUD AR (Padrão Enterprise Premium)
COLOR_TEXT = (255, 255, 255)
COLOR_FACE = (80, 100, 255)  # Vermelho suave / Coral
COLOR_SCREEN = (255, 200, 0) # Ciano Futuro (BGR)
COLOR_DOC = (0, 215, 255)    # Dourado / Âmbar
COLOR_HUD = (180, 255, 130)  # Verde Cyber
COLOR_WARNING = (0, 0, 255)  # Vermelho Vivo

def apply_secure_redaction(img, x, y, w, h):
    """Censura blindada (grau militar) para impedir o vazamento no envio da IA."""
    ih, iw = img.shape[:2]
    # Margem de segurança de 5% além da área detectada
    margin = int(max(w, h) * 0.05)
    x, y = max(0, x - margin), max(0, y - margin)
    w, h = min(w + margin*2, iw - x), min(h + margin*2, ih - y)
    
    if w > 5 and h > 5:
        roi = img[y:y+h, x:x+w]
        
        # 1. Destruição estrutural por forte Mosaico
        pz = max(15, min(w, h) // 10)
        mX, mY = max(1, w // pz), max(1, h // pz)
        small = cv2.resize(roi, (mX, mY), interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
        
        # 2. Desfoque impenetrável por gaussian blur agressivo
        blurred = cv2.GaussianBlur(pixelated, (51, 51), 0)
        
        # 3. Vidro Fumê Digital Oculto
        tint = np.full_like(blurred, (15, 15, 20)) # Escuro
        
        # 4. Inserção de padrão Hash (Grade protetora anti-IA)
        dist = 20
        for i in range(0, w + h, dist):
             cv2.line(tint, (i, 0), (0, i), (30, 30, 40), 2)

        # Mesclagem segura
        secure_roi = cv2.addWeighted(blurred, 0.3, tint, 0.7, 0)
        img[y:y+h, x:x+w] = secure_roi

def draw_ar_box(img, x, y, w, h, color, label, frame_count):
    """Componente Visual: Interface de caixa delimitadora HUD de realidade aumentada."""
    thickness = 2
    # Comprimento dinâmico dos vértices das bordas
    length = max(15, int(min(w, h) * 0.15))
    
    # Animação de pulsação leve nos cantos (respiradouro virtual)
    pulse = (math.sin(frame_count * 0.15) + 1) / 2 # Variando entre 0 e 1
    alpha = 0.1 + (0.15 * pulse)

    # Cantoneiras HUD Tech 
    pts = [
        ((x, y), (x + length, y)), ((x, y), (x, y + length)),
        ((x + w, y), (x + w - length, y)), ((x + w, y), (x + w, y + length)),
        ((x, y + h), (x + length, y + h)), ((x, y + h), (x, y + h - length)),
        ((x + w, y + h), (x + w - length, y + h)), ((x + w, y + h), (x + w, y + h - length))
    ]
    for (p1, p2) in pts:
        cv2.line(img, p1, p2, color, thickness, cv2.LINE_AA)

    # Box translúcido levemente colorido
    overlay = img.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)

    # Container Superior para a Etiqueta de Identificação
    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale = max(0.4, min(0.7, w / 350.0))
    (tv_w, tv_h), baseline = cv2.getTextSize(label, font, font_scale, 1)
    
    pad = 6
    tx, ty = x, y - 8
    
    # Se o texto ultrapassar o topo da tela, colocar abaixo da caixa detectada
    if ty - tv_h - pad*2 < 0: ty = y + h + tv_h + pad*2

    # Formato do rótulo
    cv2.rectangle(img, (tx, ty - tv_h - pad*2), (tx + tv_w + pad*2, ty), color, -1)
    cv2.rectangle(img, (tx, ty - tv_h - pad*2), (tx + tv_w + pad*2, ty), COLOR_TEXT, 1)
    cv2.putText(img, label, (tx + pad, ty - pad), font, font_scale, (0, 0, 0), 1, cv2.LINE_AA)

    # Carimbo Central: "BLOQUEADO"
    sec_label = "BLOQUEADO"
    sec_scale = max(0.5, min(1.2, w / 250.0))
    (sw, sh), _ = cv2.getTextSize(sec_label, font, sec_scale, 2)
    sx, sy = x + (w - sw) // 2, y + (h + sh) // 2
    
    if w > sw + 20 and h > sh + 20: 
        s_overlay = img.copy()
        cv2.rectangle(s_overlay, (sx - 10, sy - sh - 10), (sx + sw + 10, sy + 10), (0, 0, 50), -1) # Fundo dark red
        cv2.addWeighted(s_overlay, 0.7, img, 0.3, 0, img)
        cv2.putText(img, sec_label, (sx, sy), font, sec_scale, COLOR_TEXT, 2, cv2.LINE_AA)

def draw_hud_overlay(img, stats, frame_count):
    """Elementos de vidro inteligente estáticos (Molduras, Header e Footer)."""
    h, w = img.shape[:2]
    font = cv2.FONT_HERSHEY_DUPLEX
    
    # Efeito Vinheta Corporativa (Letterboxing Dark Mode)
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (w, 50), (12, 12, 18), -1)
    cv2.rectangle(overlay, (0, h - 45), (w, h), (12, 12, 18), -1)
    cv2.addWeighted(overlay, 0.9, img, 0.1, 0, img)

    # Grid Minimalista ao Centro
    cx, cy = w // 2, h // 2
    cv2.line(img, (cx, cy - 20), (cx, cy + 20), (255, 255, 255), 1)
    cv2.line(img, (cx - 20, cy), (cx + 20, cy), (255, 255, 255), 1)
    pulse_radius = 25 + int(math.sin(frame_count * 0.1) * 3)
    cv2.circle(img, (cx, cy), pulse_radius, COLOR_HUD, 1, cv2.LINE_AA)
    
    # === HEADER ESQUERDO ===
    cv2.putText(img, "> BRIDGE AR: PROTECAO DE DADOS", (15, 22), font, 0.5, COLOR_HUD, 1, cv2.LINE_AA)
    cv2.putText(img, f"UPTIME SINC: {frame_count} F", (15, 40), font, 0.4, (200, 200, 200), 1, cv2.LINE_AA)
    
    # === HEADER DIREITO ===
    t_str = time.strftime("%H:%M:%S")
    cv2.putText(img, f"CONEXAO SEGURA | {t_str}", (w - 270, 22), font, 0.5, COLOR_SCREEN, 1, cv2.LINE_AA)
    cv2.line(img, (w - 270, 28), (w - 15, 28), COLOR_SCREEN, 1)

    # === FOOTER INFOS ===
    total_blocks = stats['faces'] + stats['screens'] + stats['docs']
    
    status_text = "SCANNER ATIVO: NENHUM DADO SENSIVEL A VISTA"
    status_col = COLOR_HUD
    
    if total_blocks > 0:
        status_text = f"ALERTA AR: {total_blocks} REDIAO(OES) PROTEGIDA(S) EM TEMPO REAL"
        # Blink Warning vermelho leve interativo
        status_col = COLOR_WARNING if (frame_count % 20 < 10) else (255, 220, 220)

    cv2.putText(img, status_text, (15, h - 18), font, 0.5, status_col, 1, cv2.LINE_AA)
    
    info_str = f"ROSTOS: {stats['faces']} | TELAS: {stats['screens']} | LOGs/DOCs: {stats['docs']}"
    str_w = cv2.getTextSize(info_str, font, 0.5, 1)[0][0]
    cv2.putText(img, info_str, (w - str_w - 15, h - 18), font, 0.5, COLOR_TEXT, 1, cv2.LINE_AA)

def is_overlapping(box1, box2):
    """Compara intersecção e impede caixas fantasmas duplicadas na mesma área."""
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    return not (x1 + w1 < x2 or x2 + w2 < x1 or y1 + h1 < y2 or y2 + h2 < y1)

def main():
    cap = cv2.VideoCapture(0)
    
    # Sugestão de resolução larga paramétrica de AR Glass (ex. 1280x720)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    frame_count = 0
    
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

        # -------------------------------------------------------------
        #  FASE 1: RASTREAMENTO FACIAL (ALTA PRIORIDADE)
        # -------------------------------------------------------------
        if net:
            blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
            net.setInput(blob)
            detections = net.forward()
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence > 0.50: 
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (x1, y1, x2, y2) = box.astype("int")
                    
                    # Refina a expansão da "bounding box" para abranger cabelo/golas
                    margin_x = int((x2 - x1) * 0.15)
                    margin_y = int((y2 - y1) * 0.20)
                    bx = max(0, x1 - margin_x)
                    by = max(0, y1 - margin_y)
                    bw_rect = min(w - bx, (x2 - x1) + margin_x * 2)
                    bh_rect = min(h - by, (y2 - y1) + margin_y * 2)
                    
                    protected_regions.append((bx, by, bw_rect, bh_rect))
                    apply_secure_redaction(display_frame, bx, by, bw_rect, bh_rect)
                    
                    label_str = f"ROSTO IDENTIFICADO [{int(confidence*100)}%]"
                    draw_ar_box(display_frame, bx, by, bw_rect, bh_rect, COLOR_FACE, label_str, frame_count)
                    stats['faces'] += 1

        # -------------------------------------------------------------
        #  FASE 2: ANÁLISE DE SUPERFÍCIES E TELAS (MELHORADA)
        # -------------------------------------------------------------
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # O Filtro Bilateral conserva as bordas brutas, removendo miúdos do papel
        gray_filt = cv2.bilateralFilter(gray, 11, 80, 80)
        
        # 2.A: Captura de painéis iluminados (Telas) com Canny
        edged = cv2.Canny(gray_filt, 40, 140)
        
        # 2.B: Captura de papel contra a mesa pelas discrepâncias orgânicas
        thresh = cv2.adaptiveThreshold(gray_filt, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 3)
        edged_thresh = cv2.Canny(thresh, 50, 150)
        
        # Merge agressivo das duas visões
        combined = cv2.bitwise_or(edged, edged_thresh)
        
        # Operadores morfológicos para preencher arestas picotadas (frequentemente vistas em telas e Docs)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        closed = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
        closed = cv2.dilate(closed, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtra os 10 contornos dominantes para real-time FPS
        for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
            area = cv2.contourArea(cnt)
            min_area = (w * h) * 0.03 # 3% do quadro 
            
            if area > min_area:
                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
                
                # Procura quadriláteros irregulares (até 6 pontas por pequenas quebras/mãos por cima)
                if 4 <= len(approx) <= 6:
                    rx, ry, rw, rh = cv2.boundingRect(approx)
                    ar = rw / float(rh)
                    
                    # Entre a finura de um celular em pé e de um monitor mega largo
                    if 0.3 < ar < 3.0:
                        
                        overlap = False
                        current_box = (rx, ry, rw, rh)
                        for pb in protected_regions:
                            if is_overlapping(current_box, pb):
                                overlap = True
                                break
                        if overlap:
                            continue
                            
                        # Determinação pela luma (Emitir luz = Tela. Opaco = Físico)
                        roi_gray = gray_filt[ry:ry+rh, rx:rx+rw]
                        if roi_gray.size > 0:
                            avg_luma = cv2.mean(roi_gray)[0]
                            if avg_luma > 140:
                                label = "MONITOR/TELA DETECTADA"
                                color = COLOR_SCREEN
                                stats['screens'] += 1
                            else:
                                label = "DOCS/PAPEL DETECTADO"
                                color = COLOR_DOC
                                stats['docs'] += 1
                        
                            protected_regions.append(current_box)
                            apply_secure_redaction(display_frame, rx, ry, rw, rh)
                            draw_ar_box(display_frame, rx, ry, rw, rh, color, label, frame_count)

        # -------------------------------------------------------------
        #  FASE 3: RENDERIZAÇÕES EXTRAS E JANELA
        # -------------------------------------------------------------
        draw_hud_overlay(display_frame, stats, frame_count)

        cv2.imshow("Sistema Oculos AR - Filtro Privado", display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()