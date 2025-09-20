from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List
import json


app = FastAPI(title="PetShop")

#доступ разрешен для одного источника 
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000"], 
    allow_credentials=True, #позволяет отправлять учётные данные с запросами 
    allow_methods=["*"], #http все
    allow_headers=["*"], #заголовки все
)
