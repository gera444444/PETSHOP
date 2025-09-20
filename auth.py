from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
#jwt, для кодирования декодирования
SECRET_KEY = "your-secret-key-here-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 #время жизни токена
#для хеширования паролей и автоматическое использование устаревших схем
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)#принимает пароль и хешит
#сравнивает обычный пароль и хешированный на совпадения 
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict): #создание jwt
    #вычисление времени и +30минут к нему
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
   
    to_encode.update({"exp": expire}) #добавляет время истечение в словарь данных⅞
   #копирует данные в jwt
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt #возвращает jwt
