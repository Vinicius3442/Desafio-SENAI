import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from eth_account import Account
from eth_account.messages import encode_defunct

from sentinel import SentinelAI
from blockchain_client import BlockchainClient

app = FastAPI(title="Gateway Zero Trust API - Petrobras")

# Allow Frontend to communicate with Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to verified domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Security Modules
sentinel_ai = SentinelAI()
blockchain = BlockchainClient()

class RequestPayload(BaseModel):
    message: str
    metadata: dict
    signature: str

@app.post("/api/request")
async def process_request(payload: RequestPayload):
    """
    Central Zero Trust endpoint.
    Orchestrates Security measures before passing the request to the LLM.
    """
    
    # 1. Verification of hardware identity via Cryptographic Signature
    try:
        # Reconstruct the string that was signed by the frontend
        # Sort keys to ensure deterministic stringification
        signed_text = json.dumps(payload.metadata, separators=(',', ':'), sort_keys=True)
        signable_message = encode_defunct(text=signed_text)
        
        # Recover the address of the device that signed it
        device_address = Account.recover_message(signable_message, signature=payload.signature)
        print(f"[AUTH] Signature verified. Device Address: {device_address}")
        
    except Exception as e:
        print(f"[AUTH] Signature Verification Failed: {e}")
        raise HTTPException(status_code=403, detail="Invalid cryptographic signature.")

    # 2. Blockchain Access Control Verification
    if not blockchain.is_authorized(device_address):
        print(f"[BLOCKCHAIN] Device {device_address} is NOT authorized.")
        blockchain.log_event(device_address, "Request LLM", "Blocked", "Unauthorized Device")
        raise HTTPException(status_code=403, detail="Device not registered in Blockchain Access Control.")
    print(f"[BLOCKCHAIN] Device {device_address} authorized.")

    # 3. Sentinel AI Behavioral & Contextual Analysis
    if sentinel_ai.predict(payload.metadata):
        print(f"[SENTINEL] Request anomalous. Blocking.")
        blockchain.log_event(device_address, "Request LLM", "Blocked", "Anomalous Behavior Detected")
        raise HTTPException(status_code=403, detail="Request blocked due to anomalous behavior (DLP/Security).")
    print(f"[SENTINEL] Request passed behavior checks.")

    # 4. If all validations pass -> Call LLM (using Gemini/Groq/OpenAI in a real setting)
    # Using a placeholder here to prevent requiring an external key while still validating architecture
    # e.g., client = OpenAI(api_key="..."); response = client.chat.completions.create(...)
    assistant_response = f"Eu processei sua pergunta '{payload.message}' e acessei os manuais. As pressões estão normais. Essa é uma resposta do assistente via LLM."
    
    # 5. Log success to Blockchain
    blockchain.log_event(device_address, "Request LLM", "Success", "All Zero Trust checks passed")

    return {
        "status": "success",
        "device": device_address,
        "response": assistant_response
    }

@app.post("/api/admin/authorize")
async def authorize_device(address: str):
    """
    Utility endpoint for the PoC ONLY.
    Allows the frontend script to self-register its generated address in the blockchain
    so we don't need to manually interact with ABI/metamask.
    """
    if blockchain.contract:
        try:
            tx_hash = blockchain.contract.functions.authorizeDevice(address).transact({"from": blockchain.gateway_account})
            blockchain.w3.eth.wait_for_transaction_receipt(tx_hash)
            return {"status": f"Device {address} authorized in Blockchain successfully."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=500, detail="Blockchain not configured")
