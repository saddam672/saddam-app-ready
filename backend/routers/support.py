from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# ==========================================
# CONNECTION MANAGER (In-Memory for MVP)
# ==========================================
class ConnectionManager:
    def __init__(self):
        # সক্রিয় ইউজারদের চ্যাট কানেকশন (user_id: WebSocket)
        self.user_chats: Dict[str, WebSocket] = {}
        # সক্রিয় অ্যাডমিনদের চ্যাট কানেকশন (admin_id: WebSocket)
        self.admin_chats: Dict[str, WebSocket] = {}
        # WebRTC সিগন্যালিং কানেকশন (user_id/admin_id: WebSocket)
        self.webrtc_connections: Dict[str, WebSocket] = {}

    async def connect_user(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.user_chats[user_id] = websocket
        logger.info(f"User {user_id} connected to Live Chat.")
        # অ্যাডমিনদের জানানো যে নতুন ইউজার অনলাইনে এসেছে
        await self.broadcast_to_admins({"type": "user_online", "user_id": user_id})

    def disconnect_user(self, user_id: str):
        if user_id in self.user_chats:
            del self.user_chats[user_id]
            logger.info(f"User {user_id} disconnected from Live Chat.")

    async def connect_admin(self, websocket: WebSocket, admin_id: str):
        await websocket.accept()
        self.admin_chats[admin_id] = websocket
        logger.info(f"Admin {admin_id} connected to Live Chat.")

    def disconnect_admin(self, admin_id: str):
        if admin_id in self.admin_chats:
            del self.admin_chats[admin_id]

    async def send_to_user(self, message: dict, user_id: str):
        if user_id in self.user_chats:
            await self.user_chats[user_id].send_text(json.dumps(message))

    async def broadcast_to_admins(self, message: dict):
        for admin_ws in self.admin_chats.values():
            await admin_ws.send_text(json.dumps(message))

manager = ConnectionManager()


# ==========================================
# 1. LIVE TEXT CHAT (WebSockets)
# ==========================================

@router.websocket("/ws/chat/user/{user_id}")
async def user_chat_endpoint(websocket: WebSocket, user_id: str):
    """
    User connects to this WebSocket to chat with Admin.
    """
    await manager.connect_user(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # মেসেজটি সব অ্যাডমিনের কাছে পাঠিয়ে দেওয়া
            await manager.broadcast_to_admins({
                "type": "chat_message",
                "from": "user",
                "user_id": user_id,
                "message": message_data.get("message")
            })
            
            # (ভবিষ্যতে এখানে ডেটাবেসে চ্যাট হিস্ট্রি সেভ করার লজিক বসানো যাবে)
            
    except WebSocketDisconnect:
        manager.disconnect_user(user_id)
        await manager.broadcast_to_admins({"type": "user_offline", "user_id": user_id})
    except Exception as e:
        logger.error(f"User chat error: {e}")
        manager.disconnect_user(user_id)


@router.websocket("/ws/chat/admin/{admin_id}")
async def admin_chat_endpoint(websocket: WebSocket, admin_id: str):
    """
    Admin connects to this WebSocket to receive messages from users.
    """
    await manager.connect_admin(websocket, admin_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            target_user = message_data.get("target_user_id")
            
            if target_user:
                # নির্দিষ্ট ইউজারের কাছে মেসেজ পাঠানো
                await manager.send_to_user({
                    "type": "chat_message",
                    "from": "admin",
                    "message": message_data.get("message")
                }, target_user)
    except WebSocketDisconnect:
        manager.disconnect_admin(admin_id)
    except Exception as e:
        logger.error(f"Admin chat error: {e}")
        manager.disconnect_admin(admin_id)


# ==========================================
# 2. WEBRTC SIGNALING (Voice/Video Call)
# ==========================================

@router.websocket("/ws/webrtc/{peer_id}")
async def webrtc_signaling(websocket: WebSocket, peer_id: str):
    """
    WebRTC Signaling Server.
    Relay for SDP Offers, Answers, and ICE Candidates between User and Admin.
    """
    await websocket.accept()
    manager.webrtc_connections[peer_id] = websocket
    logger.info(f"WebRTC Peer {peer_id} connected.")
    
    try:
        while True:
            data = await websocket.receive_text()
            signal_data = json.loads(data)
            target_peer = signal_data.get("target_peer")
            
            # কানেকশন রিকোয়েস্ট (Offer/Answer/ICE) টার্গেটের কাছে পাঠানো
            if target_peer in manager.webrtc_connections:
                await manager.webrtc_connections[target_peer].send_text(data)
            else:
                # টার্গেট অনলাইনে না থাকলে
                await websocket.send_text(json.dumps({
                    "error": "Target peer is offline or not connected to WebRTC."
                }))
                
    except WebSocketDisconnect:
        if peer_id in manager.webrtc_connections:
            del manager.webrtc_connections[peer_id]
        logger.info(f"WebRTC Peer {peer_id} disconnected.")
    except Exception as e:
        logger.error(f"WebRTC error: {e}")
        if peer_id in manager.webrtc_connections:
            del manager.webrtc_connections[peer_id]