from sqlalchemy.orm import Session
from models import User, Product
from auth import get_password_hash, verify_password
#подключение к бд через Session 
class UserRepository:
    def __init__(self, db: Session):
        self.db = db
    #запрос к бд для получения имени п
    def get_user_by_username(self, username: str):
        return self.db.query(User).filter(User.username == username).first()
    #запрос на email
    def get_user_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()
    #создание нового пользователя 
    def create_user(self, user_data):
        hashed_password = get_password_hash(user_data.password) #хеширование
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password
        )
        self.db.add(db_user)
        self.db.commit() #сохранение изменений и обновление данных
        self.db.refresh(db_user)
        return db_user
    #вход в систему и проверка на пароль
    def authenticate_user(self, username: str, password: str):
        user = self.get_user_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            return False #пароль не вернй 
        return user
#Инициализация объекта класса через Session 
class ProductRepository:
    def __init__(self, db: Session):
        self.db = db
    #список продуктов с лимитом
    def get_products(self, skip: int = 0, limit: int = 100):
        return self.db.query(Product).offset(skip).limit(limit).all()
    
    def get_product_by_id(self, product_id: int):
        return self.db.query(Product).filter(Product.id == product_id).first()
    
    def get_products_by_category(self, category: str):
        return self.db.query(Product).filter(Product.category == category).all()
    
    def create_product(self, product_data):
        db_product = Product(**product_data.dict())
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        return db_product
