from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import json
import asyncio
import time
from datetime import datetime

from database import get_db, SessionLocal
from models import User, Product, ChatMessage
from schemas import UserCreate, LoginRequest
from auth import get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from jose import JWTError, jwt

# Создаем приложение
app = FastAPI(title="PetShop", debug=True)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# WebSocket менеджер
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Новое WebSocket подключение. Всего: {len(self.active_connections)}")
        
        # Отправляем историю сообщений новому пользователю
        db = SessionLocal()
        try:
            messages = db.query(ChatMessage).order_by(ChatMessage.timestamp.desc()).limit(10).all()
            for msg in reversed(messages):  # В правильном порядк
                try:
                    await websocket.send_text(json.dumps({
                        "username": msg.username,
                        "message": msg.message,
                        "type": msg.type,
                        "timestamp": msg.timestamp.timestamp()
                    }))
                except:
                    pass
        finally:
            db.close()
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"WebSocket отключен. Осталось: {len(self.active_connections)}")
    
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

# Зависимости
def get_current_user(token: str = Depends(lambda: ""), db: Session = Depends(get_db)):
    if not token or not token.startswith("Bearer "):
        return None
    try:
        token = token.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        user = db.query(User).filter(User.username == username).first()
        return user
    except JWTError:
        return None

# Главная страница
@app.get("/")
async def read_root():
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>PetShop - Магазин для животных</h1><p>Файл index.html не найден</p>")

# API эндпоинты
@app.get("/products")
async def get_products(category: str = None, db: Session = Depends(get_db)):
    if category and category != "all":
        products = db.query(Product).filter(Product.category == category).all()
    else:
        products = db.query(Product).all()
    
    return [{
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "price": p.price,
        "description": p.description,
        "image": p.image_url
    } for p in products]

@app.post("/register")
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Проверяем существование пользователя
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    
    # Создаем пользователя
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"message": "Пользователь успешно создан", "user_id": user.id}

@app.post("/login")
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверные учетные данные")
    
    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username
    }

# WebSocket endpoint
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    print("Подключение к WebSocket...")
    
    await manager.connect(websocket)
    db = SessionLocal()
    
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
                        # Сохраняем сообщение в БД
                        chat_message = ChatMessage(
                            username=username,
                            message=message,
                            type="message"
                        )
                        db.add(chat_message)
                        db.commit()
                        
                        # Отправляем всем клиентам
                        broadcast_msg = json.dumps({
                            "username": username,
                            "message": message,
                            "timestamp": chat_message.timestamp.timestamp(),
                            "type": "message"
                        })
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
                # проверяем соединение
                try:
                    ping_msg = {"type": "ping", "timestamp": time.time()}
                    await websocket.send_text(json.dumps(ping_msg))
                except:
                    break
                    
    except WebSocketDisconnect:
        print("WebSocket отключен клиентом")
    except Exception as e:
        print(f"Ошибка WebSocket: {e}")
    finally:
        manager.disconnect(websocket)
        db.close()

# Тестовые endpoints
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    users_count = db.query(User).count()
    products_count = db.query(Product).count()
    messages_count = db.query(ChatMessage).count()
    
    return {
        "status": "ok",
        "websocket_connections": len(manager.active_connections),
        "total_messages": messages_count,
        "total_users": users_count,
        "total_products": products_count
    }

@app.get("/chat/messages")
async def get_chat_messages(limit: int = 20, db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).order_by(ChatMessage.timestamp.desc()).limit(limit).all()
    return [{
        "username": msg.username,
        "message": msg.message,
        "timestamp": msg.timestamp.timestamp(),
        "type": msg.type
    } for msg in reversed(messages)]

@app.get("/test/ws")
async def test_websocket():
    return {"message": "WebSocket endpoint доступен по адресу ws://127.0.0.1:8000/ws/chat"}

# Инициализация базы данных
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        # тестовые продукты
        if db.query(Product).count() == 0:
            test_products = [
                Product(
                    name="Корм для кошек Premium",
                    category="food",
                    price=15.99,
                    description="Высококачественный корм для ваших пушистых друзей",
                    image_url="🐱"
                ),
                Product(
                    name="Игрушка для собак",
                    category="toys", 
                    price=8.50,
                    description="Прочная резиновая игрушка для активных собак",
                    image_url="🐶"
                ),
                Product(
                    name="Аквариум 50л",
                    category="aquarium",
                    price=45.00,
                    description="Стеклянный аквариум с подсветкой для рыбок", 
                    image_url="🐠"
                ),
                Product(
                    name="Наполнитель для кошачьего туалета",
                    category="hygiene",
                    price=12.75,
                    description="Древесный наполнитель с ароматом лаванды",
                    image_url="🐈"
                ),
                Product(
                    name="Поводок для собак",
                    category="accessories",
                    price=6.99,
                    description="Прочный нейлоновый поводок 2 метра",
                    image_url="🦮"
                )
            ]
            db.add_all(test_products)
            db.commit()
            print("Тестовые продукты добавлены в базу данных")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    print("Запуск PetShop сервера...")
    print("WebSocket доступен по: ws://127.0.0.1:8000/ws/chat")
    print("Веб-интерфейс: http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, ws_ping_interval=20, ws_ping_timeout=20)
    print(" Запуск PetShop сервера...")
    print(" WebSocket доступен по: ws://127.0.0.1:8000/ws/chat")
    print(" Веб-интерфейс: http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, ws_ping_interval=20, ws_ping_timeout=20)
