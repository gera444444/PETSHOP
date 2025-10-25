from pydantic import BaseModel

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    
    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    category: str
    price: float
    description: str

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    image_url: str
    
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatMessage(BaseModel):
    username: str
    message: str
