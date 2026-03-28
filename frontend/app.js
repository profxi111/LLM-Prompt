const API_BASE = '';

let uploadedImagePath = null;
let currentPrompt = null;
let messages = [];

document.addEventListener('DOMContentLoaded', function() {
    initImageUpload();
    initSendButton();
    initSettings();
    initModels();
    initVisionModels();
    initFavorites();
    initSearch();
    
    loadSettings();
    loadModels();
    loadVisionModels();
    loadFavorites();
});

function addMessage(content, isUser = false, isSystem = false) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = isUser ? 'message user-message' : (isSystem ? 'message system-message' : 'message bot-message');
    
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.textContent = isUser ? '👤' : '🤖';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (isSystem) {
        contentDiv.innerHTML = content;
    } else {
        const textDiv = document.createElement('div');
        textDiv.textContent = content;
        contentDiv.appendChild(textDiv);
        
        if (!isUser && content) {
            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-message-btn';
            copyBtn.textContent = '📋 复制';
            copyBtn.onclick = () => {
                navigator.clipboard.writeText(content);
                showToast('已复制到剪贴板');
            };
            contentDiv.appendChild(copyBtn);
        }
    }
    
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 2000);
}

function initImageUpload() {
    const imageInput = document.getElementById('imageInput');
    const imagePreview = document.getElementById('imagePreview');
    const previewImg = document.getElementById('previewImg');
    const removeImage = document.getElementById('removeImage');
    const uploadBtn = document.getElementById('uploadBtn');
    const pasteBtn = document.getElementById('pasteBtn');
    
    uploadBtn.addEventListener('click', () => imageInput.click());
    
    pasteBtn.addEventListener('click', async () => {
        try {
            const clipboardItems = await navigator.clipboard.read();
            for (const item of clipboardItems) {
                for (const type of item.types) {
                    if (type.startsWith('image/')) {
                        const blob = await item.getType(type);
                        const file = new File([blob], 'screenshot.png', { type: type });
                        uploadImage(file);
                        return;
                    }
                }
            }
            showToast('剪贴板中没有图片');
        } catch (error) {
            console.error('粘贴失败:', error);
            showToast('粘贴失败: ' + error.message);
        }
    });
    
    imageInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            uploadImage(file);
        }
    });
    
    removeImage.addEventListener('click', () => {
        uploadedImagePath = null;
        imagePreview.style.display = 'none';
        imageInput.value = '';
        showToast('已移除图片');
    });
}

async function uploadImage(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.code === 0) {
            uploadedImagePath = result.data.path;
            const previewImg = document.getElementById('previewImg');
            previewImg.src = `${API_BASE}/${uploadedImagePath}`;
            document.getElementById('imagePreview').style.display = 'block';
            showToast('图片上传成功');
        } else {
            showToast('上传失败: ' + result.message);
        }
    } catch (error) {
        showToast('上传失败: ' + error.message);
    }
}

function initSendButton() {
    const sendBtn = document.getElementById('sendBtn');
    const textInput = document.getElementById('textInput');
    
    sendBtn.addEventListener('click', async () => {
        const text = textInput.value.trim();
        if (!text) {
            showToast('请输入需求');
            return;
        }
        
        addMessage(text, true);
        
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<span>⏳ 生成中...</span>';
        
        try {
            const response = await fetch(`${API_BASE}/api/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    image_path: uploadedImagePath,
                    text: text
                })
            });
            
            const result = await response.json();
            
            if (result.code === 0) {
                currentPrompt = result.data.prompt;
                addMessage(result.data.prompt, false);
                
                const resultInfo = `
                    <div class="result-meta">
                        <span>场景: ${result.data.scene}</span>
                        <span>置信度: ${(result.data.confidence * 100).toFixed(1)}%</span>
                        <span>模型: ${result.data.model_used}</span>
                        <span>耗时: ${result.data.duration_ms}ms</span>
                    </div>
                `;
                addMessage(resultInfo, false, true);
                
                showToast('生成成功');
            } else {
                addMessage('生成失败: ' + result.message, false, true);
                showToast('生成失败: ' + result.message);
            }
        } catch (error) {
            addMessage('生成失败: ' + error.message, false, true);
            showToast('生成失败: ' + error.message);
        } finally {
            sendBtn.disabled = false;
            sendBtn.innerHTML = '<span>发送</span>';
            textInput.value = '';
        }
    });
    
    textInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            sendBtn.click();
        }
    });
    
    textInput.addEventListener('input', () => {
        textInput.style.height = 'auto';
        textInput.style.height = Math.min(textInput.scrollHeight, 150) + 'px';
    });
}

function initSettings() {
    const settingsBtn = document.getElementById('settingsBtn');
    const settingsModal = document.getElementById('settingsModal');
    const closeSettingsBtn = document.getElementById('closeSettingsBtn');
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');
    
    settingsBtn.addEventListener('click', () => {
        settingsModal.style.display = 'flex';
    });
    
    closeSettingsBtn.addEventListener('click', () => {
        settingsModal.style.display = 'none';
    });
    
    saveSettingsBtn.addEventListener('click', async () => {
        const settings = {
            style: document.getElementById('styleInput').value,
            keywords: document.getElementById('keywordsInput').value,
            tone: document.getElementById('toneInput').value,
            default_scene: document.getElementById('sceneInput').value
        };
        
        try {
            const response = await fetch(`${API_BASE}/api/user/preference`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });
            
            const result = await response.json();
            
            if (result.code === 0) {
                showToast('设置保存成功');
                settingsModal.style.display = 'none';
            } else {
                showToast('保存失败: ' + result.message);
            }
        } catch (error) {
            showToast('保存失败: ' + error.message);
        }
    });
}

async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE}/api/user/preference`);
        const result = await response.json();
        
        if (result.code === 0) {
            document.getElementById('styleInput').value = result.data.style || '';
            document.getElementById('keywordsInput').value = result.data.keywords || '';
            document.getElementById('toneInput').value = result.data.tone || '';
            document.getElementById('sceneInput').value = result.data.default_scene || '';
        }
    } catch (error) {
        console.error('加载设置失败:', error);
    }
}

function initModels() {
    const modelsBtn = document.getElementById('modelsBtn');
    const modelsModal = document.getElementById('modelsModal');
    const closeModelsBtn = document.getElementById('closeModelsBtn');
    const addModelBtn = document.getElementById('addModelBtn');
    const addModelModal = document.getElementById('addModelModal');
    const closeAddModelBtn = document.getElementById('closeAddModelBtn');
    const confirmModelBtn = document.getElementById('confirmModelBtn');
    
    modelsBtn.addEventListener('click', () => {
        modelsModal.style.display = 'flex';
    });
    
    closeModelsBtn.addEventListener('click', () => {
        modelsModal.style.display = 'none';
    });
    
    addModelBtn.addEventListener('click', () => {
        addModelModal.style.display = 'flex';
    });
    
    closeAddModelBtn.addEventListener('click', () => {
        addModelModal.style.display = 'none';
    });
    
    confirmModelBtn.addEventListener('click', async () => {
        const modelData = {
            vendor: document.getElementById('modelVendor').value,
            name: document.getElementById('modelName').value,
            api_url: document.getElementById('modelApiUrl').value,
            api_key: document.getElementById('modelApiKey').value,
            priority: parseInt(document.getElementById('modelPriority').value),
            scene: document.getElementById('modelScene').value
        };
        
        if (!modelData.name || !modelData.api_url || !modelData.api_key) {
            showToast('请填写完整信息');
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE}/api/models`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(modelData)
            });
            
            const result = await response.json();
            
            if (result.code === 0) {
                showToast('模型添加成功');
                addModelModal.style.display = 'none';
                loadModels();
            } else {
                showToast('添加失败: ' + result.message);
            }
        } catch (error) {
            showToast('添加失败: ' + error.message);
        }
    });
}

async function loadModels() {
    try {
        const response = await fetch(`${API_BASE}/api/models`);
        const result = await response.json();
        
        const modelsList = document.getElementById('modelsList');
        
        if (result.code === 0 && result.data.length > 0) {
            modelsList.innerHTML = result.data.map(model => `
                <div class="model-item">
                    <div class="model-info">
                        <strong>${model.vendor} - ${model.name}</strong>
                        <div class="model-meta">
                            优先级: ${model.priority} | 场景: ${model.scene || '通用'} | 状态: ${model.enabled ? '启用' : '禁用'}
                        </div>
                    </div>
                    <div class="model-actions">
                        <button class="delete-btn" onclick="deleteModel(${model.id})">删除</button>
                    </div>
                </div>
            `).join('');
        } else {
            modelsList.innerHTML = '<p class="empty-hint">暂无模型配置</p>';
        }
    } catch (error) {
        console.error('加载模型失败:', error);
    }
}

function initVisionModels() {
    const visionModelsBtn = document.getElementById('visionModelsBtn');
    const visionModelsModal = document.getElementById('visionModelsModal');
    const closeVisionModelsBtn = document.getElementById('closeVisionModelsBtn');
    const addVisionModelBtn = document.getElementById('addVisionModelBtn');
    const addVisionModelModal = document.getElementById('addVisionModelModal');
    const closeAddVisionModelBtn = document.getElementById('closeAddVisionModelBtn');
    const confirmVisionModelBtn = document.getElementById('confirmVisionModelBtn');
    
    visionModelsBtn.addEventListener('click', () => {
        visionModelsModal.style.display = 'flex';
        loadVisionModels();
    });
    
    closeVisionModelsBtn.addEventListener('click', () => {
        visionModelsModal.style.display = 'none';
    });
    
    addVisionModelBtn.addEventListener('click', () => {
        addVisionModelModal.style.display = 'flex';
    });
    
    closeAddVisionModelBtn.addEventListener('click', () => {
        addVisionModelModal.style.display = 'none';
    });
    
    confirmVisionModelBtn.addEventListener('click', async () => {
        const visionModelData = {
            vendor: document.getElementById('visionModelVendor').value,
            name: document.getElementById('visionModelName').value,
            api_url: document.getElementById('visionModelApiUrl').value,
            api_key: document.getElementById('visionModelApiKey').value
        };
        
        if (!visionModelData.name || !visionModelData.api_url || !visionModelData.api_key) {
            showToast('请填写完整信息');
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE}/api/vision-models`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(visionModelData)
            });
            
            const result = await response.json();
            
            if (result.code === 0) {
                showToast('视觉模型添加成功');
                addVisionModelModal.style.display = 'none';
                loadVisionModels();
            } else {
                showToast('添加失败: ' + result.message);
            }
        } catch (error) {
            showToast('添加失败: ' + error.message);
        }
    });
}

async function loadVisionModels() {
    try {
        const response = await fetch(`${API_BASE}/api/vision-models`);
        const result = await response.json();
        
        const visionModelsList = document.getElementById('visionModelsList');
        
        if (result.code === 0 && result.data.length > 0) {
            visionModelsList.innerHTML = result.data.map(model => `
                <div class="model-item">
                    <div class="model-info">
                        <strong>${model.vendor} - ${model.name}</strong>
                        <div class="model-meta">
                            状态: ${model.enabled ? '启用' : '禁用'}
                        </div>
                    </div>
                    <div class="model-actions">
                        <button class="delete-btn" onclick="deleteVisionModel(${model.id})">删除</button>
                    </div>
                </div>
            `).join('');
        } else {
            visionModelsList.innerHTML = '<p class="empty-hint">暂无视觉模型配置</p>';
        }
    } catch (error) {
        console.error('加载视觉模型失败:', error);
    }
}

async function deleteVisionModel(id) {
    if (!confirm('确定要删除这个视觉模型配置吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/vision-models/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.code === 0) {
            showToast('删除成功');
            loadVisionModels();
        } else {
            showToast('删除失败: ' + result.message);
        }
    } catch (error) {
        showToast('删除失败: ' + error.message);
    }
}

async function deleteModel(id) {
    if (!confirm('确定要删除这个模型配置吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/models/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.code === 0) {
            showToast('删除成功');
            loadModels();
        } else {
            showToast('删除失败: ' + result.message);
        }
    } catch (error) {
        showToast('删除失败: ' + error.message);
    }
}

function initFavorites() {
    const favoriteBtn = document.getElementById('favoriteBtn');
    const favoritesModal = document.getElementById('favoritesModal');
    const closeFavoritesBtn = document.getElementById('closeFavoritesBtn');
    
    favoriteBtn.addEventListener('click', () => {
        favoritesModal.style.display = 'flex';
        loadFavorites();
    });
    
    closeFavoritesBtn.addEventListener('click', () => {
        favoritesModal.style.display = 'none';
    });
}

async function loadFavorites() {
    try {
        const response = await fetch(`${API_BASE}/api/favorites`);
        const result = await response.json();
        
        const favoritesList = document.getElementById('favoritesList');
        
        if (result.code === 0 && result.data.length > 0) {
            favoritesList.innerHTML = result.data.map(fav => `
                <div class="favorite-item">
                    <div class="favorite-info">
                        <strong>分类: ${fav.category || '未分类'}</strong>
                        <div class="favorite-meta">时间: ${new Date(fav.created_at).toLocaleString()}</div>
                    </div>
                    <div class="favorite-content">${fav.content.substring(0, 200)}...</div>
                    <div class="favorite-actions">
                        <button class="use-btn" onclick="useFavorite(${fav.id})">使用</button>
                        <button class="delete-btn" onclick="deleteFavorite(${fav.id})">删除</button>
                    </div>
                </div>
            `).join('');
        } else {
            favoritesList.innerHTML = '<p class="empty-hint">暂无收藏</p>';
        }
    } catch (error) {
        console.error('加载收藏失败:', error);
    }
}

async function useFavorite(id) {
    try {
        const response = await fetch(`${API_BASE}/api/favorites`);
        const result = await response.json();
        
        if (result.code === 0) {
            const fav = result.data.find(f => f.id === id);
            if (fav) {
                document.getElementById('textInput').value = fav.content;
                document.getElementById('favoritesModal').style.display = 'none';
                showToast('已加载到输入框');
            }
        }
    } catch (error) {
        console.error('加载收藏失败:', error);
    }
}

async function deleteFavorite(id) {
    if (!confirm('确定要删除这条收藏吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/favorite/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.code === 0) {
            showToast('删除成功');
            loadFavorites();
        } else {
            showToast('删除失败: ' + result.message);
        }
    } catch (error) {
        showToast('删除失败: ' + error.message);
    }
}

function initSearch() {
    const searchBtn = document.getElementById('searchBtn');
    const searchModal = document.getElementById('searchModal');
    const closeSearchBtn = document.getElementById('closeSearchBtn');
    const searchActionBtn = document.getElementById('searchActionBtn');
    const searchInput = document.getElementById('searchInput');
    
    searchBtn.addEventListener('click', () => {
        searchModal.style.display = 'flex';
    });
    
    closeSearchBtn.addEventListener('click', () => {
        searchModal.style.display = 'none';
    });
    
    searchActionBtn.addEventListener('click', async () => {
        const query = searchInput.value.trim();
        if (!query) {
            showToast('请输入搜索关键词');
            return;
        }
        
        performSearch(query);
    });
    
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchActionBtn.click();
        }
    });
}

async function performSearch(query) {
    try {
        const response = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}`);
        const result = await response.json();
        
        const searchResults = document.getElementById('searchResults');
        
        if (result.code === 0 && result.data.length > 0) {
            searchResults.innerHTML = result.data.map(item => `
                <div class="search-item" onclick="useSearchResult(${item.id})">
                    <div class="search-meta">
                        <span>分类: ${item.category || '未分类'}</span>
                        <span>相似度: ${(item.similarity * 100).toFixed(1)}%</span>
                    </div>
                    <div class="search-content">${item.content.substring(0, 150)}...</div>
                </div>
            `).join('');
        } else {
            searchResults.innerHTML = '<p class="empty-hint">未找到相关结果</p>';
        }
    } catch (error) {
        console.error('搜索失败:', error);
        searchResults.innerHTML = '<p class="empty-hint">搜索失败</p>';
    }
}

async function useSearchResult(id) {
    try {
        const response = await fetch(`${API_BASE}/api/favorites`);
        const result = await response.json();
        
        if (result.code === 0) {
            const fav = result.data.find(f => f.id === id);
            if (fav) {
                document.getElementById('textInput').value = fav.content;
                document.getElementById('searchModal').style.display = 'none';
                showToast('已加载到输入框');
            }
        }
    } catch (error) {
        console.error('加载搜索结果失败:', error);
    }
}

window.deleteModel = deleteModel;
window.deleteVisionModel = deleteVisionModel;
window.deleteFavorite = deleteFavorite;
window.useFavorite = useFavorite;
window.useSearchResult = useSearchResult;
