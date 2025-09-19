from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List, Dict, Any
import json
import asyncio
import time

# Создаем приложение
app = FastAPI(title="PetShop", debug=True)

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Простая база данных в памяти
class Database:
    def __init__(self):
        self.products = [
            {
                "id": 1,
                "name": "Корм для кошек Premium",
                "category": "food",
                "price": 15.99,
                "description": "Высококачественный корм для ваших пушистых друзей",
                "image": "🐱"
            },
            {
                "id": 2,
                "name": "Игрушка для собак",
                "category": "toys",
                "price": 8.50,
                "description": "Прочная резиновая игрушка для активных собак",
                "image": "🐶"
            },
            {
                "id": 3,
                "name": "Аквариум 50л",
                "category": "aquarium",
                "price": 45.00,
                "description": "Стеклянный аквариум с подсветкой для рыбок",
                "image": "🐠"
            },
            {
                "id": 4,
                "name": "Наполнитель для кошачьего туалета",
                "category": "hygiene",
                "price": 12.75,
                "description": "Древесный наполнитель с ароматом лаванды",
                "image": "🐈"
            },
            {
                "id": 5,
                "name": "Поводок для собак",
                "category": "accessories",
                "price": 6.99,
                "description": "Прочный нейлоновый поводок 2 метра",
                "image": "🦮"
            }
        ]
        self.users = []
        self.messages = []

db = Database()

# WebSocket менеджер
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ Новое WebSocket подключение. Всего: {len(self.active_connections)}")
        
        # Отправляем историю сообщений новому пользователю
        if db.messages:
            last_messages = db.messages[-10:]  # Последние 10 сообщений
            for msg in last_messages:
                try:
                    await websocket.send_text(json.dumps({
                        "username": msg["username"],
                        "message": msg["message"],
                        "type": "message",
                        "timestamp": msg.get("timestamp", time.time())
                    }))
                except:
                    pass
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"❌ WebSocket отключен. Осталось: {len(self.active_connections)}")
    
    async def broadcast(self, message: str):
        if not self.active_connections:
            return
            
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Ошибка отправки сообщения: {e}")
                disconnected.append(connection)
        
        # Удаляем отключенные соединения
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

# Роуты
@app.get("/")
async def read_root():
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>PetShop - Магазин для животных</h1><p>Файл index.html не найден</p>")

@app.get("/products")
async def get_products(category: str = None):
    if category and category != "all":
        return [p for p in db.products if p["category"] == category]
    return db.products

@app.post("/register")
async def register(user_data: dict):
    username = user_data.get("username", "").strip()
    email = user_data.get("email", "").strip()
    password = user_data.get("password", "").strip()
    
    if not username or not email or not password:
        raise HTTPException(status_code=400, detail="Все поля обязательны для заполнения")
    
    if any(u["username"] == username for u in db.users):
        raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
    if any(u["email"] == email for u in db.users):
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    
    user = {
        "id": len(db.users) + 1,
        "username": username,
        "email": email,
        "password": password,
        "created_at": time.time()
    }
    db.users.append(user)
    
    return {"message": "Пользователь успешно создан", "user_id": user["id"]}

@app.post("/login")
async def login(login_data: dict):
    username = login_data.get("username", "").strip()
    password = login_data.get("password", "").strip()
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Имя пользователя и пароль обязательны")
    
    user = next((u for u in db.users if u["username"] == username and u["password"] == password), None)
    if not user:
        raise HTTPException(status_code=401, detail="Неверные учетные данные")
    
    return {
        "access_token": f"token-{user['id']}-{time.time()}",
        "token_type": "bearer",
        "username": user["username"]
    }

# WebSocket endpoint
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    print("🔄 Подключение к WebSocket...")
    
    await manager.connect(websocket)
    
    try:
        # Отправляем приветственное сообщение
        welcome_msg = {
            "username": "System",
            "message": "Добро пожаловать в чат поддержки PetShop!",
            "type": "info",
            "timestamp": time.time()
        }
        await websocket.send_text(json.dumps(welcome_msg))
        
        # Главный цикл обработки сообщений
        while True:
            try:
                # Ждем сообщение от клиента
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300.0)
                
                try:
                    message_data = json.loads(data)
                    username = message_data.get("username", "Гость").strip()
                    message = message_data.get("message", "").strip()
                    
                    if message:
                        # Сохраняем сообщение
                        chat_message = {
                            "username": username,
                            "message": message,
                            "timestamp": time.time(),
                            "type": "message"
                        }
                        db.messages.append(chat_message)
                        
                        # Отправляем всем клиентам
                        broadcast_msg = json.dumps(chat_message)
                        await manager.broadcast(broadcast_msg)
                        
                except json.JSONDecodeError:
                    error_msg = {
                        "username": "System",
                        "message": "Ошибка: неверный формат сообщения",
                        "type": "error",
                        "timestamp": time.time()
                    }
                    await websocket.send_text(json.dumps(error_msg))
                    
            except asyncio.TimeoutError:
                # Таймаут - проверяем соединение
                try:
                    ping_msg = {"type": "ping", "timestamp": time.time()}
                    await websocket.send_text(json.dumps(ping_msg))
                except:
                    break
                    
    except WebSocketDisconnect:
        print("🔌 WebSocket отключен клиентом")
    except Exception as e:
        print(f"❌ Ошибка WebSocket: {e}")
    finally:
        manager.disconnect(websocket)

# Тестовые endpoints
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "websocket_connections": len(manager.active_connections),
        "total_messages": len(db.messages),
        "total_users": len(db.users),
        "total_products": len(db.products)
    }

@app.get("/chat/messages")
async def get_chat_messages(limit: int = 20):
    return db.messages[-limit:]

@app.get("/test/ws")
async def test_websocket():
    return {"message": "WebSocket endpoint доступен по адресу ws://127.0.0.1:8000/ws/chat"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Запуск PetShop сервера...")
    print("📍 WebSocket доступен по: ws://127.0.0.1:8000/ws/chat")
    print("🌐 Веб-интерфейс: http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, ws_ping_interval=20, ws_ping_timeout=20)