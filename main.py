from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List
import json

from database import get_db, Base, engine
from models import User, Product
from schemas import UserCreate, ProductCreate, LoginRequest, ChatMessage
from repository import Repository
from auth import create_access_token

app = FastAPI(title="PetShop")

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# WebSocket соединения
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# Создаем таблицы
Base.metadata.create_all(bind=engine)

# Инициализируем начальные данные
@app.on_event("startup")
def startup():
    db = next(get_db())
    repo = Repository(db)
    
    # Добавляем тестовые товары
    if not repo.get_products():
        products = [
            Product(
                name="Корм для кошек",
                category="food",
                price=15.99,
                description="Питательный корм для вашего питомца",
                image_url="/static/cat-food.jpg"
            ),
            Product(
                name="Игрушка для собак",
                category="toys",
                price=8.50,
                description="Прочная игрушка для активных собак",
                image_url="/static/dog-toy.jpg"
            ),
            Product(
                name="Аквариум",
                category="aquarium",
                price=45.00,
                description="Стеклянный аквариум для рыбок",
                image_url="/static/aquarium.jpg"
            )
        ]
        db.add_all(products)
        db.commit()
    db.close()

# Роуты
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/register")
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    repo = Repository(db)
    if repo.get_user_by_username(user_data.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    if repo.get_user_by_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = repo.create_user(user_data)
    return {"message": "User created successfully", "user_id": user.id}

@app.post("/login")
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    repo = Repository(db)
    user = repo.authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/products")
def get_products(category: str = None, db: Session = Depends(get_db)):
    repo = Repository(db)
    if category:
        return repo.get_products_by_category(category)
    return repo.get_products()

@app.post("/products")
def create_product(product_data: ProductCreate, db: Session = Depends(get_db)):
    repo = Repository(db)
    return repo.create_product(product_data)

# WebSocket для чата поддержки
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            chat_message = ChatMessage(**message_data)
            
            await manager.broadcast(json.dumps({
                "username": chat_message.username,
                "message": chat_message.message,
                "type": "message"
            }))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(json.dumps({
            "message": "Пользователь покинул чат",
            "type": "info"
        }))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
