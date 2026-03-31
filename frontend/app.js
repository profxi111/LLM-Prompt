const API_BASE = 'http://localhost:8000';

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
                const finalPrompt = result.data.final_prompt || result.data.prompt || '';
                currentPrompt = finalPrompt;
                currentFinalPrompt = finalPrompt;
                currentSessionId = result.data.session_id || null;
                currentVariants = result.data.variants || [];

                addMessage(finalPrompt, false);

                // V2 新增：显示生成元信息
                if (result.data.agent_chain) {
                    const chainNames = result.data.agent_chain.map(id => {
                        const names = { S1: '图片理解', S2: '构图生成', S3: '整理优化', S4: '风格延展', S5: '视频空镜' };
                        return names[id] || id;
                    }).join(' → ');
                    addMessage(`<div class="result-meta"><span>链路: ${chainNames}</span><span>耗时: ${result.data.duration_ms}ms</span></div>`, false, true);
                } else if (result.data.scene) {
                    // V1 兼容
                    const resultInfo = `
                        <div class="result-meta">
                            <span>场景: ${result.data.scene}</span>
                            <span>置信度: ${(result.data.confidence * 100).toFixed(1)}%</span>
                            <span>模型: ${result.data.model_used}</span>
                            <span>耗时: ${result.data.duration_ms}ms</span>
                        </div>
                    `;
                    addMessage(resultInfo, false, true);
                }

                // V2 新增：显示调整工具栏
                showAdjustToolbar(result.data);

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
        
        if (!modelData.name) {
            showToast('请填写模型名称');
            return;
        }
        
        // 编辑模式：API URL可以为空（表示不修改），但API Key不能为空
        if (editingModelId) {
            if (!modelData.api_url && !modelData.api_key) {
                // 编辑模式且没有填写API信息，只更新其他字段
                modelData.api_url = '';
                modelData.api_key = '';
            } else if (!modelData.api_key) {
                // 如果提供了API URL但没有提供API Key，提示用户
                showToast('请填写API Key');
                return;
            }
        } else {
            // 新增模式：API URL和API Key都不能为空
            if (!modelData.api_url || !modelData.api_key) {
                showToast('请填写完整信息');
                return;
            }
        }
        
        try {
            const isEditing = editingModelId !== null;
            const url = isEditing ? `${API_BASE}/api/models/${editingModelId}` : `${API_BASE}/api/models`;
            const method = isEditing ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(modelData)
            });
            
            const result = await response.json();
            
            if (result.code === 0) {
                showToast(isEditing ? '模型更新成功' : '模型添加成功');
                addModelModal.style.display = 'none';
                
                // 重置编辑状态
                editingModelId = null;
                document.querySelector('#addModelModal .modal-header h3').textContent = '➕ 添加模型配置';
                document.getElementById('confirmModelBtn').textContent = '确认添加';
                
                loadModels();
            } else {
                showToast((isEditing ? '更新' : '添加') + '失败: ' + result.message);
            }
        } catch (error) {
            showToast((isEditing ? '更新' : '添加') + '失败: ' + error.message);
        }
    });
    
    // 点击添加模型按钮时重置编辑状态
    addModelBtn.addEventListener('click', () => {
        editingModelId = null;
        document.getElementById('modelVendor').value = 'qwen';
        document.getElementById('modelName').value = '';
        document.getElementById('modelApiUrl').value = '';
        document.getElementById('modelApiKey').value = '';
        document.getElementById('modelPriority').value = '1';
        document.getElementById('modelScene').value = '';
        document.querySelector('#addModelModal .modal-header h3').textContent = '➕ 添加模型配置';
        document.getElementById('confirmModelBtn').textContent = '确认添加';
        addModelModal.style.display = 'flex';
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
                        <button class="test-btn" onclick="testModel(${model.id})" title="测试连通性">🔌 测试</button>
                        <button class="edit-btn" onclick="editModel(${model.id})" title="编辑">✏️ 编辑</button>
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

async function testModel(id) {
    try {
        showToast('正在测试连接...');
        const response = await fetch(`${API_BASE}/api/models/${id}/test`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.code === 0) {
            showToast('✅ 连接成功: ' + result.message);
        } else {
            showToast('❌ 连接失败: ' + result.message);
        }
    } catch (error) {
        showToast('❌ 测试失败: ' + error.message);
    }
}

let editingModelId = null;

async function editModel(id) {
    try {
        const response = await fetch(`${API_BASE}/api/models/${id}`);
        const result = await response.json();
        
        if (result.code !== 0) {
            showToast('获取模型信息失败');
            return;
        }
        
        const model = result.data;
        if (!model) {
            showToast('模型不存在');
            return;
        }
        
        // 填充表单
        document.getElementById('modelVendor').value = model.vendor;
        document.getElementById('modelName').value = model.name;
        document.getElementById('modelApiUrl').value = model.api_url;
        document.getElementById('modelApiKey').value = '';
        document.getElementById('modelPriority').value = model.priority;
        document.getElementById('modelScene').value = model.scene || '';
        
        editingModelId = id;
        
        // 修改弹窗标题
        document.querySelector('#addModelModal .modal-header h3').textContent = '✏️ 编辑模型配置';
        document.getElementById('confirmModelBtn').textContent = '确认更新';
        
        // 显示弹窗
        document.getElementById('addModelModal').style.display = 'flex';
    } catch (error) {
        showToast('加载模型信息失败: ' + error.message);
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
window.testModel = testModel;
window.editModel = editModel;

// ============================================================
// V2 新增：调整工具栏与 Agent 链路
// ============================================================

// 全局状态
let currentSessionId = null;
let currentVariants = [];
let currentFinalPrompt = "";

// DOM 加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initAdjustToolbar();
    initVariantsModal();
    initChainDetailModal();
});

// 初始化调整工具栏
function initAdjustToolbar() {
    const copyBtn = document.getElementById('copyPromptBtn');
    const favoriteBtn = document.getElementById('favoritePromptBtn');
    const submitBtn = document.getElementById('submitAdjustBtn');

    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(currentFinalPrompt);
            showToast('已复制到剪贴板');
        });
    }

    if (favoriteBtn) {
        favoriteBtn.addEventListener('click', () => {
            if (!currentFinalPrompt) return;
            fetch(`${API_BASE}/api/favorite`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: currentFinalPrompt, category: '海报_科技风' })
            })
            .then(r => r.json())
            .then(result => {
                if (result.code === 0) showToast('收藏成功');
                else showToast('收藏失败: ' + result.message);
            })
            .catch(err => showToast('收藏失败: ' + err.message));
        });
    }

    if (submitBtn) {
        submitBtn.addEventListener('click', submitAdjustment);
    }
}

// 提交调整请求
async function submitAdjustment() {
    const submitBtn = document.getElementById('submitAdjustBtn');
    const targetAgent = document.getElementById('targetAgentSelect').value;
    const instruction = document.getElementById('adjustInstruction').value.trim();

    if (!instruction) {
        showToast('请输入调整说明');
        return;
    }

    if (!currentSessionId) {
        showToast('会话ID不存在，请重新生成');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ 调整中...';

    try {
        const response = await fetch(`${API_BASE}/api/adjust`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                target_agent: targetAgent,
                user_instruction: instruction
            })
        });

        const result = await response.json();

        if (result.code === 0) {
            // 更新提示词展示
            currentFinalPrompt = result.data.final_prompt;
            document.getElementById('promptDisplay').innerHTML =
                `<div class="prompt-text">${escapeHtml(result.data.final_prompt)}</div>`;

            // 更新链路
            if (result.data.agent_chain) {
                renderAgentChain(result.data.agent_chain);
            }

            // 如果 S4 返回了变体，显示变体弹窗
            if (result.data.variants && result.data.variants.length > 0) {
                showVariantsModal(result.data.variants);
            }

            // 同时更新聊天区的消息
            addMessage(result.data.final_prompt, false);

            showToast('调整成功');
            document.getElementById('adjustInstruction').value = '';
        } else {
            showToast('调整失败: ' + result.message);
        }
    } catch (error) {
        showToast('调整失败: ' + error.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '🚀 提交调整';
    }
}

// 渲染 Agent 链路图
function renderAgentChain(chain) {
    const container = document.getElementById('agentChain');
    if (!container || !chain) return;

    const chainSteps = {
        'S1': '图片理解',
        'S2': '构图生成',
        'S3': '整理优化',
        'S4': '风格延展',
        'S5': '视频空镜'
    };

    container.innerHTML = chain.map((agentId, index) => {
        const name = chainSteps[agentId] || agentId;
        return `<div class="chain-node" onclick="showChainDetail('${agentId}')">
            <span class="chain-number">${index + 1}</span>
            <span class="chain-name">${name}</span>
            <span class="chain-status">✓</span>
        </div>`;
    }).join('<span class="chain-arrow">→</span>');
}

// 显示链路节点详情
window.showChainDetail = async function(agentId) {
    if (!currentSessionId) return;

    const modal = document.getElementById('chainDetailModal');
    const titleEl = document.getElementById('chainDetailTitle');
    const inputEl = document.getElementById('chainDetailInput');
    const outputEl = document.getElementById('chainDetailOutput');

    const chainSteps = { 'S1': '图片理解', 'S2': '构图生成', 'S3': '整理优化', 'S4': '风格延展', 'S5': '视频空镜' };
    titleEl.textContent = `${chainSteps[agentId] || agentId} (${agentId}) - 详情`;

    try {
        const response = await fetch(`${API_BASE}/api/sessions/${currentSessionId}`);
        const result = await response.json();

        if (result.code !== 0 || !result.data) {
            showToast('获取详情失败');
            return;
        }

        const sessionData = result.data;
        inputEl.textContent = getAgentInputText(sessionData, agentId);
        outputEl.textContent = getAgentOutputText(sessionData, agentId);

        modal.style.display = 'flex';
    } catch (error) {
        showToast('获取详情失败: ' + error.message);
    }
};

function getAgentInputText(sessionData, agentId) {
    const map = {
        'S1': sessionData.image_path ? `图片路径: ${sessionData.image_path}` : '（无图片）',
        'S2': `用户需求: ${sessionData.user_input || ''}\n图片描述: ${sessionData.s1_image_description || '（无）'}`,
        'S3': `来源: ${sessionData.s2_draft_prompt ? 'S2 构图生成' : 'S4 风格延展'}\n内容: ${sessionData.s2_draft_prompt || ''}`,
        'S4': `用户调整说明: （需查看上下文）\n原始提示词: ${sessionData.s3_final_prompt || ''}`,
        'S5': `用户需求: ${sessionData.user_input || ''}`,
    };
    return map[agentId] || '（无数据）';
}

function getAgentOutputText(sessionData, agentId) {
    const map = {
        'S1': sessionData.s1_image_description || '（无）',
        'S2': sessionData.s2_draft_prompt || '（无）',
        'S3': sessionData.s3_final_prompt || '（无）',
        'S4': JSON.stringify(sessionData.s4_variants || [], null, 2),
        'S5': sessionData.s2_draft_prompt || '（无）',
    };
    return map[agentId] || '（无数据）';
}

// 选择变体
function selectVariant(index) {
    const variant = currentVariants[index];
    if (!variant) return;

    const finalContent = variant.final || variant.content;
    currentFinalPrompt = finalContent;

    document.getElementById('promptDisplay').innerHTML =
        `<div class="prompt-text">${escapeHtml(finalContent)}</div>`;

    document.getElementById('variantsModal').style.display = 'none';

    // 高亮选中项
    document.querySelectorAll('.variant-item').forEach((el, i) => {
        el.classList.toggle('selected', i === index);
    });

    showToast('已选择变体: ' + variant.style);
}

window.selectVariant = selectVariant;

// 初始化链路详情弹窗
function initChainDetailModal() {
    const closeBtn = document.getElementById('closeChainDetailBtn');
    const modal = document.getElementById('chainDetailModal');

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
}

// 变体选择弹窗
function initVariantsModal() {
    const closeBtn = document.getElementById('closeVariantsBtn');
    const modal = document.getElementById('variantsModal');

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
}

// 显示变体选择弹窗
function showVariantsModal(variants) {
    const modal = document.getElementById('variantsModal');
    const list = document.getElementById('variantsList');

    list.innerHTML = variants.map((v, i) => `
        <div class="variant-item" id="variantItem${i}" onclick="selectVariant(${i})">
            <div class="variant-header">
                <strong>${v.style}</strong>
            </div>
            <div class="variant-content">${escapeHtml(v.final || v.content)}</div>
        </div>
    `).join('');

    modal.style.display = 'flex';
    currentVariants = variants;
}

// HTML 转义（防止 XSS）
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// V2 新增：显示调整工具栏
function showAdjustToolbar(data) {
    const toolbar = document.getElementById('adjustToolbar');
    const promptDisplay = document.getElementById('promptDisplay');

    if (!toolbar) return;

    // 设置提示词内容
    if (promptDisplay) {
        promptDisplay.innerHTML = `<div class="prompt-text">${escapeHtml(data.final_prompt || '')}</div>`;
    }

    // 渲染 Agent 链路图
    if (data.agent_chain) {
        renderAgentChain(data.agent_chain);
    }

    // 显示工具栏
    toolbar.style.display = 'block';
}
