let ws = null;
let currentUser = null;
let isConnected = false;

// Загрузка товаров
async function loadProducts(category = null) {
    try {
        let url = '/products';
        if (category && category !== 'all') {
            url += `?category=${category}`;
        }
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`Ошибка HTTP: ${response.status}`);
        }
        
        const products = await response.json();
        displayProducts(products);
        
    } catch (error) {
        console.error('Ошибка загрузки товаров:', error);
        const productsList = document.getElementById('products-list');
        productsList.innerHTML = '<div class="error">Не удалось загрузить товары. Попробуйте перезагрузить страницу.</div>';
    }
}

// Отображение товаров
function displayProducts(products) {
    const productsList = document.getElementById('products-list');
    productsList.innerHTML = '';
    
    if (products.length === 0) {
        productsList.innerHTML = '<div class="no-products">Товары не найдены</div>';
        return;
    }
    
    products.forEach(product => {
        const productCard = document.createElement('div');
        productCard.className = 'product-card';
        productCard.innerHTML = `
            <div class="product-image">${product.image || '🐾'}</div>
            <h3>${product.name}</h3>
            <p class="product-description">${product.description}</p>
            <div class="product-footer">
                <span class="product-price">$${product.price}</span>
                <span class="product-category">${getCategoryName(product.category)}</span>
            </div>
        `;
        productsList.appendChild(productCard);
    });
}

// Названия категорий
function getCategoryName(category) {
    const categories = {
        'food': 'Корм',
        'toys': 'Игрушки',
        'aquarium': 'Аквариумы',
        'hygiene': 'Гигиена',
        'accessories': 'Аксессуары'
    };
    return categories[category] || category;
}

// WebSocket соединение
function connectWebSocket() {
    try {
        // Закрываем предыдущее соединение
        if (ws) {
            try {
                ws.close();
            } catch (e) {
                console.log('Ошибка при закрытии предыдущего соединения:', e);
            }
        }
        
        const wsUrl = "ws://127.0.0.1:8000/ws/chat";
        console.log('🔗 Подключаемся к WebSocket:', wsUrl);
        
        ws = new WebSocket(wsUrl);
        isConnected = false;
        
        ws.onopen = function() {
            console.log('✅ WebSocket соединение установлено');
            isConnected = true;
            updateConnectionStatus(true);
            addChatMessage('System', 'Подключение к чату установлено', 'success');
        };
        
        ws.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                
                // Игнорируем ping-сообщения
                if (data.type === 'ping') {
                    return;
                }
                
                addChatMessage(data.username, data.message, data.type || 'message');
            } catch (error) {
                console.error('❌ Ошибка обработки сообщения:', error);
            }
        };
        
        ws.onclose = function(event) {
            console.log('🔌 WebSocket соединение закрыто:', event.code);
            isConnected = false;
            updateConnectionStatus(false);
            
            if (event.code !== 1000) {
                addChatMessage('System', 'Соединение с чатом потеряно', 'error');
            }
        };
        
        ws.onerror = function(error) {
            console.error('❌ WebSocket ошибка:', error);
            isConnected = false;
            updateConnectionStatus(false);
        };
        
    } catch (error) {
        console.error('❌ Ошибка создания WebSocket:', error);
        updateConnectionStatus(false);
    }
}

// Обновление статуса соединения
function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
        statusElement.textContent = connected ? '✅ Online' : '❌ Offline';
        statusElement.style.color = connected ? 'green' : 'red';
    }
}

// Добавление сообщения в чат
function addChatMessage(username, message, type = 'message') {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;
    
    let icon = '💬';
    let bgColor = '#f0f0f0';
    
    switch (type) {
        case 'success':
            icon = '✅';
            bgColor = '#e8f5e8';
            break;
        case 'error':
            icon = '❌';
            bgColor = '#ffebee';
            break;
        case 'info':
            icon = '💡';
            bgColor = '#e3f2fd';
            break;
    }
    
    if (type === 'message') {
        messageDiv.innerHTML = `
            <strong>${username}:</strong> 
            <span>${message}</span>
        `;
    } else {
        messageDiv.innerHTML = `
            <span class="message-icon">${icon}</span>
            <em>${message}</em>
        `;
    }
    
    messageDiv.style.backgroundColor = bgColor;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Отправка сообщения
function sendMessage() {
    const messageInput = document.getElementById('message-input');
    if (!messageInput) return;
    
    const message = messageInput.value.trim();
    if (!message) return;
    
    if (!ws || ws.readyState !== WebSocket.OPEN || !isConnected) {
        addChatMessage('System', 'Соединение не установлено. Нажмите "Переподключить"', 'error');
        return;
    }
    
    if (!currentUser) {
        alert('Пожалуйста, войдите в систему для отправки сообщений');
        return;
    }
    
    try {
        const messageData = {
            username: currentUser,
            message: message
        };
        
        ws.send(JSON.stringify(messageData));
        messageInput.value = '';
        
    } catch (error) {
        console.error('❌ Ошибка отправки сообщения:', error);
        addChatMessage('System', 'Ошибка отправки сообщения', 'error');
    }
}

// Авторизация
function showRegister() {
    document.getElementById('form-title').textContent = 'Регистрация';
    document.getElementById('email-input').style.display = 'block';
    document.getElementById('auth-form').onsubmit = register;
    document.getElementById('auth-forms').style.display = 'block';
}

function showLogin() {
    document.getElementById('form-title').textContent = 'Вход';
    document.getElementById('email-input').style.display = 'none';
    document.getElementById('auth-form').onsubmit = login;
    document.getElementById('auth-forms').style.display = 'block';
}

function hideAuthForms() {
    document.getElementById('auth-forms').style.display = 'none';
    // Очищаем форму
    document.getElementById('username-input').value = '';
    document.getElementById('email-input').value = '';
    document.getElementById('password-input').value = '';
}

async function register(e) {
    if (e) e.preventDefault();
    
    const userData = {
        username: document.getElementById('username-input').value.trim(),
        email: document.getElementById('email-input').value.trim(),
        password: document.getElementById('password-input').value
    };
    
    if (!userData.username || !userData.email || !userData.password) {
        alert('Все поля обязательны для заполнения');
        return;
    }
    
    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(userData)
        });
        
        if (response.ok) {
            alert('Регистрация успешна! Теперь войдите в систему.');
            hideAuthForms();
            showLogin();
        } else {
            const error = await response.json();
            alert('Ошибка: ' + error.detail);
        }
    } catch (error) {
        alert('Ошибка сети: ' + error.message);
    }
}

async function login(e) {
    if (e) e.preventDefault();
    
    const loginData = {
        username: document.getElementById('username-input').value.trim(),
        password: document.getElementById('password-input').value
    };
    
    if (!loginData.username || !loginData.password) {
        alert('Введите имя пользователя и пароль');
        return;
    }
    
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(loginData)
        });
        
        if (response.ok) {
            const data = await response.json();
            currentUser = data.username;
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('username', currentUser);
            
            updateAuthUI();
            hideAuthForms();
            
            // Переподключаем WebSocket после входа
            setTimeout(connectWebSocket, 500);
            
        } else {
            const error = await response.json();
            alert('Ошибка: ' + error.detail);
        }
    } catch (error) {
        alert('Ошибка сети: ' + error.message);
    }
}

function logout() {
    currentUser = null;
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    
    if (ws) {
        try {
            ws.close();
        } catch (e) {
            console.log('Ошибка при закрытии WebSocket:', e);
        }
    }
    
    updateAuthUI();
    addChatMessage('System', 'Вы вышли из системы', 'info');
}

function updateAuthUI() {
    const authButtons = document.getElementById('auth-buttons');
    const userInfo = document.getElementById('user-info');
    const usernameSpan = document.getElementById('username');
    
    if (currentUser) {
        authButtons.style.display = 'none';
        userInfo.style.display = 'block';
        usernameSpan.textContent = currentUser;
    } else {
        authButtons.style.display = 'block';
        userInfo.style.display = 'none';
    }
}

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
    // Восстанавливаем пользователя из localStorage
    const savedUsername = localStorage.getItem('username');
    const savedToken = localStorage.getItem('token');
    
    if (savedUsername && savedToken) {
        currentUser = savedUsername;
        updateAuthUI();
    }
    
    // Загружаем товары
    loadProducts();
    
    // Подключаемся к WebSocket с задержкой
    setTimeout(connectWebSocket, 1000);
    
    // Обработчики событий
    const messageInput = document.getElementById('message-input');
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendMessage();
            }
        });
    }
    
    // Добавляем кнопку переподключения
    const chatContainer = document.querySelector('.chat-container');
    if (chatContainer) {
        const reconnectBtn = document.createElement('button');
        reconnectBtn.textContent = '🔄 Переподключить';
        reconnectBtn.className = 'reconnect-btn';
        reconnectBtn.onclick = connectWebSocket;
        chatContainer.appendChild(reconnectBtn);
        
        // Добавляем статус соединения
        const statusDiv = document.createElement('div');
        statusDiv.id = 'connection-status';
        statusDiv.className = 'connection-status';
        statusDiv.textContent = '❌ Offline';
        statusDiv.style.color = 'red';
        chatContainer.appendChild(statusDiv);
    }
    
    console.log('🐾 PetShop инициализирован');
});