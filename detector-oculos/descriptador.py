import os
import json
import base64
import glob
import cv2
import numpy as np
try:
    from cryptography.fernet import Fernet
except ImportError:
    print("Execute 'pip install cryptography' antes de rodar o descriptador.")
    exit(1)

def get_master_key():
    key_path = "master_key.key"
    if not os.path.exists(key_path):
         print("CRITICO: Chave mestra 'master_key.key' nao encontrada. ACESSO NEGADO.")
         return None
    with open(key_path, "rb") as key_file:
         return key_file.read()

def decrypt_secure_file(filename, fernet):
    print(f"\n[SERVIDOR CENTRAL] Descriptografando pacote: {filename}...")
    with open(filename, "rb") as f:
         encrypted_data = f.read()
         
    try:
         # 1. Descriptografia Bruta
         decrypted_bytes = fernet.decrypt(encrypted_data)
         payload = json.loads(decrypted_bytes.decode('utf-8'))
         
         # 2. Leitura da Telemetria Mockada (Segura e Privada)
         print("\n>>> DADOS DE TELEMETRIA RECUPERADOS >>>")
         print(f"Dispositivo Original : {payload.get('device_id')}")
         print(f"Data/Hora Captura    : {payload.get('local_time')}")
         
         gps = payload.get("gps_telemetry", {})
         print(f"Localizacao (GPS)    : Lat:{gps.get('lat')}, Lng:{gps.get('lng')}, Alt:{gps.get('alt')}")
         
         print(f"Status e Entidades Ocultas pelo AR: {payload.get('entities_blocked')}")
         print("---------------------------------------")
         
         # 3. Decodificar e Reconstruir Imagem Censurada
         b64_image = payload.get("image_data")
         if b64_image:
             img_bytes = base64.b64decode(b64_image)
             np_arr = np.frombuffer(img_bytes, np.uint8)
             img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
             
             window_name = f"ACESSO PERMITIDO - {filename}"
             cv2.imshow(window_name, img)
             print(">> Imagem (JA CENSURADA) extraida com sucesso! Pressione QUALQUER TECLA na imagem para ver o proximo.")
             cv2.waitKey(0) # Aguarda input para fechar e ver o próximo arquivo
             cv2.destroyWindow(window_name)
         else:
             print("Aviso: Nenhuma imagem de payload foi encontrada dentro deste pacote.")
             
    except Exception as e:
         print(f"FALHA GERAL: Erro ao quebrar a criptografia. O log pode estar corrompido ou voce nao possui autorizacao. Erro: {e}")

def main():
    print("=========================================================")
    print("   CENTRAL SEGURA DE DESCRIPTOGRAFIA - OMNI CORP AR")
    print("=========================================================")
    
    key = get_master_key()
    if not key: return
    fernet = Fernet(key)
    print("[SUCCESS] Chave simétrica militar inicializada.\n")
    
    secure_files = glob.glob("*.secure")
    
    if not secure_files:
         print("Nenhum registro '.secure' pendente de analise nesta pasta.")
         return
         
    print(f"-> Foram encontrados {len(secure_files)} pacotes blindados na fila.")
    
    for file in secure_files:
         decrypt_secure_file(file, fernet)
         
    print("\n[SERVIDOR CENTRAL] Concluido. Nenhum pacote restante na fila.")

if __name__ == "__main__":
    main()
