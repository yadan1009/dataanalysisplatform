// 全局变量
let currentSessionId = null;
let currentMode = 'normal';
let uploadedFiles = [];

// 初始化应用
async function init() {
    await loadSessions();
    updateModeDisplay();
    setupEventListeners();
}

// 设置事件监听器
function setupEventListeners() {
    // 消息发送
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });

    // 视图切换
    const chatView = document.getElementById('chatView');
    const excelView = document.getElementById('excelView');
    const dataAnalysisView = document.getElementById('dataAnalysisView');
    const excelToolBtn = document.getElementById('excelToolBtn');
    const dataAnalysisBtn = document.getElementById('dataAnalysisBtn');

    // 点击logo回到聊天界面
    document.querySelector('.sidebar-header').addEventListener('click', () => {
        chatView.style.display = 'flex';
        excelView.style.display = 'none';
        dataAnalysisView.style.display = 'none';
        excelToolBtn.classList.remove('active');
        dataAnalysisBtn.classList.remove('active');
    });

    excelToolBtn.addEventListener('click', () => {
        chatView.style.display = 'none';
        excelView.style.display = 'flex';
        dataAnalysisView.style.display = 'none';
        excelToolBtn.classList.add('active');
        dataAnalysisBtn.classList.remove('active');
    });

    dataAnalysisBtn.addEventListener('click', () => {
        chatView.style.display = 'none';
        excelView.style.display = 'none';
        dataAnalysisView.style.display = 'flex';
        excelToolBtn.classList.remove('active');
        dataAnalysisBtn.classList.add('active');
    });

    // 设置面板外部点击关闭
    document.addEventListener('click', function(event) {
        const panel = document.getElementById('settingsPanel');
        const settingsBtn = document.querySelector('.settings-btn');
        if (!panel.contains(event.target) && !settingsBtn.contains(event.target)) {
            panel.classList.remove('active');
        }
    });

    // 模式切换事件
    document.querySelectorAll('input[name="mode"]').forEach(radio => {
        radio.addEventListener('change', function(e) {
            if (currentSessionId && currentSessionId !== 'new') {
                e.preventDefault();
                document.querySelector(`input[name="mode"][value="${currentMode}"]`).checked = true;
                return;
            }
            const newMode = this.value;
            if (newMode !== currentMode) {
                currentMode = newMode;
                updateModeDisplay();
            }
        });
    });

    // 文件上传（知识库）
    document.getElementById('fileInput').addEventListener('change', async function(e) {
        const file = e.target.files[0];
        if (!file) return;

        const uploadStatus = document.getElementById('uploadStatus');
        uploadStatus.textContent = '正在上传和处理文件...';
        uploadStatus.style.color = '#3b82f6';

        const formData = new FormData();
        formData.append('file', file);
        formData.append('session_id', currentSessionId || 'temp');

        try {
            const response = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await response.json();
            
            if (response.ok) {
                uploadedFiles.push({ name: data.filename, size: data.content_length || 0 });
                updateFileList();
                uploadStatus.textContent = `文件上传成功！已读取 ${data.content_length || 0} 个字符`;
                uploadStatus.style.color = '#10b981';
            } else {
                uploadStatus.textContent = '上传失败: ' + data.error;
                uploadStatus.style.color = '#ef4444';
            }
        } catch (error) {
            uploadStatus.textContent = '上传失败: ' + error.message;
            uploadStatus.style.color = '#ef4444';
        }
        this.value = '';
    });

    // Excel工具事件
    setupExcelToolEvents();
    
    // 数据分析事件
    setupDataAnalysisEvents();
}

// 消息相关函数
function addMessage(content, isUser) {
    const chatMessages = document.getElementById('chatMessages');
    const welcomeMessage = chatMessages.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = isUser ? '我' : 'AI';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 50);
}

function addMessageWithTypingEffect(content, isUser) {
    const chatMessages = document.getElementById('chatMessages');
    const welcomeMessage = chatMessages.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = isUser ? '我' : 'AI';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = '';
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    let i = 0;
    const typingSpeed = 20;
    
    function typeNextChar() {
        if (i < content.length) {
            contentDiv.textContent += content.charAt(i);
            i++;
            chatMessages.scrollTop = chatMessages.scrollHeight;
            setTimeout(typeNextChar, typingSpeed);
        }
    }
    
    typeNextChar();
}

async function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const message = messageInput.value.trim();
    if (!message) return;

    addMessage(message, true);
    messageInput.value = '';
    sendButton.disabled = true;
    sendButton.innerHTML = '<span class="btn-loading"></span>';
    
    const chatMessages = document.getElementById('chatMessages');
    const placeholderDiv = document.createElement('div');
    placeholderDiv.className = 'message ai-message';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = 'AI';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content typing';
    contentDiv.textContent = '思考中...';
    
    placeholderDiv.appendChild(avatar);
    placeholderDiv.appendChild(contentDiv);
    chatMessages.appendChild(placeholderDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: message,
                mode: currentMode,
                session_id: currentSessionId || 'new'
            })
        });

        const data = await response.json();
        
        chatMessages.removeChild(placeholderDiv);
        
        if (response.ok) {
            addMessageWithTypingEffect(data.reply, false);
            if (data.session_id && data.session_id !== currentSessionId) {
                currentSessionId = data.session_id;
                await loadSessions();
                updateModeDisplay();
            }
        } else {
            addMessage(`错误: ${data.error}`, false);
        }
    } catch (error) {
        chatMessages.removeChild(placeholderDiv);
        addMessage(`网络错误: ${error.message}`, false);
    }

    sendButton.disabled = false;
    sendButton.innerHTML = '<span class="send-icon">📤</span>';
}

// 会话管理函数
async function loadSessions() {
    try {
        const response = await fetch('/api/sessions');
        const sessions = await response.json();
        renderSessionList(sessions);
    } catch (error) {
        console.error('加载会话列表失败:', error);
    }
}

function renderSessionList(sessions) {
    const sessionList = document.getElementById('sessionList');
    sessionList.innerHTML = sessions.map(session => {
        const date = new Date(session.updated_at);
        const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
        let modeText = session.mode === 'knowledge' ? '知识库模式' : '普通模式';
        return `
            <div class="session-item ${session.id === currentSessionId ? 'active' : ''}" 
                 onclick="switchSession('${session.id}')">
                <div class="session-title">${session.title}</div>
                <div class="session-info">${modeText} · ${dateStr}</div>
                <button class="session-delete" onclick="deleteSession(event, '${session.id}')">×</button>
            </div>
        `;
    }).join('');
}

async function createNewSession() {
    currentSessionId = null;
    clearChat();
    uploadedFiles = [];
    updateFileList();
    updateModeDisplay();
    
    // 切换回聊天界面
    const chatView = document.getElementById('chatView');
    const excelView = document.getElementById('excelView');
    const dataAnalysisView = document.getElementById('dataAnalysisView');
    
    chatView.style.display = 'flex';
    excelView.style.display = 'none';
    dataAnalysisView.style.display = 'none';
    
    // 重置工具按钮状态
    document.getElementById('excelToolBtn').classList.remove('active');
    document.getElementById('dataAnalysisBtn').classList.remove('active');
}

async function switchSession(sessionId) {
    try {
        const response = await fetch(`/api/sessions/${sessionId}`);
        const session = await response.json();
        currentSessionId = sessionId;
        currentMode = session.mode;
        
        document.querySelector(`input[name="mode"][value="${currentMode}"]`).checked = true;
        updateModeDisplay();
        
        clearChat();
        session.messages.forEach(msg => {
            addMessage(msg.content, msg.role === 'user');
        });
        
        await loadSessions();
        updateModeDisplay();
        
        // 切换回聊天界面
        const chatView = document.getElementById('chatView');
        const excelView = document.getElementById('excelView');
        const dataAnalysisView = document.getElementById('dataAnalysisView');
        
        chatView.style.display = 'flex';
        excelView.style.display = 'none';
        dataAnalysisView.style.display = 'none';
        
        document.getElementById('excelToolBtn').classList.remove('active');
        document.getElementById('dataAnalysisBtn').classList.remove('active');
    } catch (error) {
        console.error('切换会话失败:', error);
    }
}

async function deleteSession(event, sessionId) {
    event.stopPropagation();
    if (!confirm('确定要删除这个会话吗？')) return;
    
    try {
        const response = await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
        
        if (response.ok) {
            if (sessionId === currentSessionId) {
                currentSessionId = null;
                clearChat();
                uploadedFiles = [];
                updateFileList();
                updateModeDisplay();
            }
            await loadSessions();
        }
    } catch (error) {
        console.error('删除会话失败:', error);
    }
}

function clearChat() {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon">👋</div>
            <h3>欢迎使用智析平台</h3>
            <p>我是您的AI助手，可以帮您进行数据分析、文档问答等任务</p>
        </div>
    `;
}

// 界面更新函数
function updateFileList() {
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = uploadedFiles.map(file => {
         const fileName = typeof file === 'string' ? file : file.name;
         const fileSize = typeof file === 'object' && file.size ? ` (${file.size} 字符)` : '';
         return `<div class="file-item">${fileName}${fileSize}</div>`;
    }).join('');
}

function toggleSettings() {
    document.getElementById('settingsPanel').classList.toggle('active');
}

function updateModeDisplay() {
    const modeText = currentMode === 'normal' ? '普通模式' : '知识库模式';
    document.getElementById('currentModeText').textContent = modeText;
    
    document.getElementById('normalSettings').style.display = currentMode === 'normal' ? 'block' : 'none';
    document.getElementById('knowledgeSettings').style.display = currentMode === 'knowledge' ? 'block' : 'none';
        
    const hasActiveSession = currentSessionId && currentSessionId !== 'new';
    document.getElementById('modeLockTip').style.display = hasActiveSession ? 'block' : 'none';
    
    document.querySelectorAll('.mode-option').forEach(option => {
        if (hasActiveSession) {
            option.style.opacity = '0.6';
            option.style.pointerEvents = 'none';
        } else {
            option.style.opacity = '1';
            option.style.pointerEvents = 'auto';
        }
    });
}

async function savePrompt() {
    const prompt = document.getElementById('initialPrompt').value;
    try {
        const response = await fetch('/api/set_prompt', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: currentSessionId || 'temp',
                prompt: prompt
            })
        });
        
        if (response.ok) {
            showNotification('设置已保存', 'success');
        } else {
            showNotification('保存失败', 'error');
        }
    } catch (error) {
        showNotification('保存失败: ' + error.message, 'error');
    }
}

async function clearKnowledge() {
    if (currentSessionId && currentSessionId !== 'new') {
        showNotification('会话进行中，无法清空知识库。请新建对话后再试。', 'warning');
        return;
    }
    
    if (!confirm('确定要清空知识库吗？')) return;
    
    try {
        const response = await fetch('/api/clear_knowledge', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: currentSessionId || 'temp'
            })
        });
        
        if (response.ok) {
            uploadedFiles = [];
            updateFileList();
            showNotification('知识库已清空', 'success');
        } else {
            showNotification('清空失败', 'error');
        }
    } catch (error) {
        showNotification('清空失败: ' + error.message, 'error');
    }
}

// 通知函数
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 20px;
        border-radius: 12px;
        color: white;
        font-size: 14px;
        font-weight: 500;
        z-index: 9999;
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.2);
    `;
    
    if (type === 'success') {
        notification.style.background = 'rgba(16, 185, 129, 0.9)';
    } else if (type === 'error') {
        notification.style.background = 'rgba(239, 68, 68, 0.9)';
    } else if (type === 'warning') {
        notification.style.background = 'rgba(245, 158, 11, 0.9)';
    } else {
        notification.style.background = 'rgba(59, 130, 246, 0.9)';
    }
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// Excel工具相关函数
function setupExcelToolEvents() {
    const excelFileInput = document.getElementById('excelFileInput');
    const excelUploadArea = document.getElementById('excelUploadArea');
    const excelFileName = document.getElementById('excelFileName');
    const processExcelBtn = document.getElementById('processExcelBtn');
    
    excelUploadArea.onclick = () => excelFileInput.click();
    
    // 拖拽上传
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        excelUploadArea.addEventListener(eventName, e => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
        
        if (eventName === 'dragenter' || eventName === 'dragover') {
            excelUploadArea.addEventListener(eventName, () => {
                excelUploadArea.style.borderColor = 'var(--secondary)';
                excelUploadArea.style.background = 'rgba(255, 255, 255, 0.2)';
            }, false);
        }
        
        if (eventName === 'dragleave' || eventName === 'drop') {
             excelUploadArea.addEventListener(eventName, () => {
                excelUploadArea.style.borderColor = 'var(--glass-border)';
                excelUploadArea.style.background = 'var(--glass-bg)';
            }, false);
        }
    });
    
    excelUploadArea.addEventListener('drop', e => {
        excelFileInput.files = e.dataTransfer.files;
        handleExcelFileSelect();
    }, false);

    excelFileInput.onchange = handleExcelFileSelect;

    function handleExcelFileSelect() {
        const file = excelFileInput.files[0];
        if (file) {
            excelFileName.textContent = `已选择文件: ${file.name}`;
            processExcelBtn.disabled = false;
        }
    }

    processExcelBtn.onclick = async () => {
        const file = excelFileInput.files[0];
        if (!file) return;

        processExcelBtn.disabled = true;
        processExcelBtn.innerHTML = '<span class="btn-loading"></span> 处理中...';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/process_excel', { method: 'POST', body: formData });
            const data = await response.json();

            if (response.ok) {
                displayExcelResults(data);
            } else {
                showNotification(`错误: ${data.error}`, 'error');
            }
        } catch (err) {
            showNotification(`发生网络错误: ${err}`, 'error');
        } finally {
            processExcelBtn.disabled = false;
            processExcelBtn.innerHTML = '<span class="btn-icon">🚀</span> 开始处理';
        }
    };
    
    // AI命令处理
    const processAiCommandBtn = document.getElementById('processAiCommandBtn');
    if (processAiCommandBtn) {
        processAiCommandBtn.addEventListener('click', processAiCommand);
    }
    
    const aiCommandInput = document.getElementById('aiCommandInput');
    if (aiCommandInput) {
        aiCommandInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') processAiCommand();
        });
    }
}

function displayExcelResults(data) {
    document.getElementById('excelUploadContainer').style.display = 'none';
    document.getElementById('excelResultsContainer').style.display = 'block';

    const summary = data.summary;
    document.getElementById('excelSummary').innerHTML = `
        <p>✔️ 成功取消了 <strong>${summary.unmerged_cells}</strong> 个合并单元格。</p>
        <p>✔️ 识别并处理了 <strong>${summary.header_rows_detected}</strong> 行复杂表头。</p>
        <p>✔️ 清理后共 <strong>${summary.total_rows}</strong> 行, <strong>${summary.total_cols}</strong> 列数据。</p>
    `;

    document.getElementById('downloadExcelLink').href = `/api/download_processed/${data.download_filename}`;

    const previewData = JSON.parse(data.preview);
    const excelPreviewTable = document.getElementById('excelPreviewTable');
    let tableHTML = '<thead><tr>';
    previewData.columns.forEach(col => tableHTML += `<th>${col}</th>`);
    tableHTML += '</tr></thead><tbody>';
    previewData.data.forEach(row => {
        tableHTML += '<tr>';
        row.forEach(cell => tableHTML += `<td>${cell ? cell.toString().slice(0, 50) : ''}</td>`);
        tableHTML += '</tr>';
    });
    tableHTML += '</tbody>';
    excelPreviewTable.innerHTML = tableHTML;
    
    // 保存数据用于AI处理
    window.currentExcelData = {
        preview_data: data.preview,
        filename: data.download_filename
    };
    
    // 激活AI处理按钮
    document.getElementById('processAiCommandBtn').disabled = false;
}

// AI处理Excel数据
async function processAiCommand() {
    const aiCommandInput = document.getElementById('aiCommandInput');
    const instruction = aiCommandInput.value.trim();
    
    if (!instruction) {
        showNotification('请输入处理指令', 'warning');
        return;
    }
    
    if (!window.currentExcelData) {
        showNotification('请先处理Excel文件', 'warning');
        return;
    }
    
    const processBtn = document.getElementById('processAiCommandBtn');
    processBtn.disabled = true;
    processBtn.innerHTML = '<span class="btn-loading"></span> AI处理中...';
    
    try {
        const response = await fetch('/api/excel_ai_process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                instruction: instruction,
                preview_data: window.currentExcelData.preview_data,
                filename: window.currentExcelData.filename
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayAiResults(data);
        } else {
            showNotification(`处理失败: ${data.error}`, 'error');
            console.error('AI处理失败:', data);
        }
    } catch (error) {
        showNotification(`发生错误: ${error.message}`, 'error');
        console.error('AI处理错误:', error);
    } finally {
        processBtn.disabled = false;
        processBtn.innerHTML = '<span class="btn-icon">✨</span> 提交指令';
    }
}

function displayAiResults(data) {
    const resultContainer = document.getElementById('aiResultContainer');
    resultContainer.style.display = 'block';
    
    // 显示结果摘要
    const summary = data.summary;
    let summaryHTML = `<div style="padding: 20px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px;">`;
    summaryHTML += `<p>✅ AI已处理指令: <strong>${summary.instruction}</strong></p>`;
    
    if (summary.new_columns && summary.new_columns.length > 0) {
        summaryHTML += `<p>✅ <strong>新增了 ${summary.new_columns.length} 列</strong>: ${summary.new_columns.join(', ')}</p>`;
    }
    
    if (summary.removed_columns && summary.removed_columns.length > 0) {
        summaryHTML += `<p>✅ <strong>移除了 ${summary.removed_columns.length} 列</strong>: ${summary.removed_columns.join(', ')}</p>`;
    }
    
    if (summary.modified_columns && summary.modified_columns.length > 0) {
        summaryHTML += `<p>✅ <strong>修改了 ${summary.modified_columns.length}${summary.modified_columns.length > 10 ? '+' : ''} 列</strong>: ${summary.modified_columns.join(', ')}${summary.modified_columns.length > 10 ? '...' : ''}</p>`;
    }
    
    summaryHTML += `<p>✅ 处理后共 <strong>${summary.total_rows}</strong> 行, <strong>${summary.total_cols}</strong> 列数据。</p>`;
    
    if (data.ai_explanation && data.ai_explanation.trim() !== '') {
        summaryHTML += `<div style="margin-top: 15px; padding: 12px; background-color: rgba(255, 255, 255, 0.1); border-radius: 8px; border-left: 3px solid var(--secondary);">
            <h4 style="margin-top: 0; color: var(--white);">AI处理说明</h4>
            <p style="white-space: pre-line; margin-bottom: 0;">${data.ai_explanation}</p>
        </div>`;
    }
    
    summaryHTML += `</div>`;
    
    document.getElementById('aiResultSummary').innerHTML = summaryHTML;
    
    // 设置下载链接
    document.getElementById('downloadAiProcessedLink').href = `/api/download_processed/${data.download_filename}`;
    
    // 显示处理后的数据预览
    const previewData = JSON.parse(data.preview);
    const aiProcessedTable = document.getElementById('aiProcessedTable');
    let tableHTML = '<thead><tr>';
    
    previewData.columns.forEach(col => {
        let headerStyle = '';
        let headerTitle = '';
        
        if (summary.new_columns && summary.new_columns.includes(col)) {
            headerStyle = 'background-color: var(--success); color: white;';
            headerTitle = '新增列';
        } else if (summary.modified_columns && summary.modified_columns.includes(col)) {
            headerStyle = 'background-color: var(--info); color: white;';
            headerTitle = '已修改列';
        }
        
        tableHTML += `<th style="${headerStyle}" title="${headerTitle}">${col}</th>`;
    });
    
    tableHTML += '</tr></thead><tbody>';
    
    previewData.data.forEach(row => {
        tableHTML += '<tr>';
        row.forEach(cell => {
            let displayValue = '';
            if (cell !== null && cell !== undefined) {
                if (!isNaN(parseFloat(cell)) && isFinite(cell)) {
                    const numValue = parseFloat(cell);
                    if (numValue > 10000 || numValue < 0.01) {
                        displayValue = numValue.toLocaleString('zh-CN');
                    } else if (Number.isInteger(numValue)) {
                        displayValue = numValue.toString();
                    } else {
                        displayValue = numValue.toFixed(2);
                    }
                } else {
                    const strValue = cell.toString();
                    displayValue = strValue.length > 50 ? strValue.slice(0, 47) + '...' : strValue;
                }
            }
            tableHTML += `<td title="${displayValue}">${displayValue}</td>`;
        });
        tableHTML += '</tr>';
    });
    
    tableHTML += '</tbody>';
    aiProcessedTable.innerHTML = tableHTML;
    
    // 更新当前数据
    window.currentExcelData.preview_data = data.preview;
    window.currentExcelData.filename = data.download_filename;
    
    // 清空输入框以便下次处理
    document.getElementById('aiCommandInput').value = '';
}

// 数据分析相关函数  
function setupDataAnalysisEvents() {
    const analysisFileInput = document.getElementById('analysisFileInput');
    const analysisUploadArea = document.getElementById('analysisUploadArea');
    const analysisFileName = document.getElementById('analysisFileName');
    const startAnalysisBtn = document.getElementById('startAnalysisBtn');
    
    if (analysisUploadArea) {
        analysisUploadArea.onclick = () => analysisFileInput.click();
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            analysisUploadArea.addEventListener(eventName, e => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
            if (eventName === 'dragenter' || eventName === 'dragover') {
                analysisUploadArea.addEventListener(eventName, () => {
                    analysisUploadArea.style.borderColor = 'var(--secondary)';
                    analysisUploadArea.style.background = 'rgba(255, 255, 255, 0.2)';
                }, false);
            }
            if (eventName === 'dragleave' || eventName === 'drop') {
                analysisUploadArea.addEventListener(eventName, () => {
                    analysisUploadArea.style.borderColor = 'var(--glass-border)';
                    analysisUploadArea.style.background = 'var(--glass-bg)';
                }, false);
            }
        });
        
        analysisUploadArea.addEventListener('drop', e => {
            analysisFileInput.files = e.dataTransfer.files;
            handleAnalysisFileSelect();
        }, false);
    }
    
    if (analysisFileInput) {
        analysisFileInput.onchange = handleAnalysisFileSelect;
    }
    
    function handleAnalysisFileSelect() {
        const file = analysisFileInput.files[0];
        if (file) {
            analysisFileName.textContent = `已选择文件: ${file.name}`;
            startAnalysisBtn.disabled = false;
        }
    }
    
    if (startAnalysisBtn) {
        startAnalysisBtn.onclick = async () => {
            const file = analysisFileInput.files[0];
            if (!file) return;
            
            startAnalysisBtn.disabled = true;
            startAnalysisBtn.innerHTML = '<span class="btn-loading"></span> 分析中...';
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/api/data_analysis', { method: 'POST', body: formData });
                const data = await response.json();
                
                if (response.ok) {
                    displayAnalysisResults(data);
                } else {
                    showNotification(`错误: ${data.error}`, 'error');
                    console.error('数据分析错误:', data);
                }
            } catch (err) {
                showNotification(`发生网络错误: ${err}`, 'error');
                console.error('数据分析请求错误:', err);
            } finally {
                startAnalysisBtn.disabled = false;
                startAnalysisBtn.innerHTML = '<span class="btn-icon">🔍</span> 开始分析';
            }
        };
    }
}

function displayAnalysisResults(data) {
    document.getElementById('analysisUploadContainer').style.display = 'none';
    document.getElementById('analysisResultsContainer').style.display = 'block';
    
    // 设置下载链接
    document.getElementById('downloadAnalysisLink').href = `/api/download_analysis/${data.download_filename}`;
    
    // 显示基础统计信息
    const basicStats = data.basic_stats;
    let basicStatsHTML = `
        <div><strong>行数:</strong> ${basicStats.rows}</div>
        <div><strong>列数:</strong> ${basicStats.columns}</div>
        <div><strong>缺失值:</strong> ${Object.values(basicStats.missing_values).reduce((a, b) => a + b, 0)} 个</div>
    `;
    
    const topColumns = basicStats.column_names.slice(0, 5);
    basicStatsHTML += `<div><strong>部分列名:</strong> ${topColumns.join(', ')}</div>`;
    
    document.getElementById('basicStatsContent').innerHTML = basicStatsHTML;
    
    // 显示数值统计
    const numericStats = data.numeric_stats;
    let numericStatsHTML = '';
    
    if (Object.keys(numericStats).length > 0) {
        numericStatsHTML += '<table style="width: 100%; border-collapse: collapse; font-size: 14px;">';
        numericStatsHTML += '<tr><th style="text-align: left; padding: 4px;">列名</th><th style="text-align: right; padding: 4px;">均值</th><th style="text-align: right; padding: 4px;">中位数</th><th style="text-align: right; padding: 4px;">最小值</th><th style="text-align: right; padding: 4px;">最大值</th></tr>';
        
        Object.entries(numericStats).slice(0, 5).forEach(([col, stats]) => {
            numericStatsHTML += `<tr>
                <td style="padding: 4px;">${col}</td>
                <td style="text-align: right; padding: 4px;">${stats.mean ? stats.mean.toFixed(2) : 'N/A'}</td>
                <td style="text-align: right; padding: 4px;">${stats.median ? stats.median.toFixed(2) : 'N/A'}</td>
                <td style="text-align: right; padding: 4px;">${stats.min ? stats.min.toFixed(2) : 'N/A'}</td>
                <td style="text-align: right; padding: 4px;">${stats.max ? stats.max.toFixed(2) : 'N/A'}</td>
            </tr>`;
        });
        
        numericStatsHTML += '</table>';
    } else {
        numericStatsHTML = '<p>没有发现数值型列</p>';
    }
    
    document.getElementById('numericStatsContent').innerHTML = numericStatsHTML;
    
    // 显示分类统计
    const categoricalStats = data.categorical_stats;
    let categoricalStatsHTML = '';
    
    if (Object.keys(categoricalStats).length > 0) {
        Object.entries(categoricalStats).slice(0, 3).forEach(([col, stats]) => {
            categoricalStatsHTML += `<div style="margin-bottom: 10px;">
                <strong>${col}</strong> (${stats.unique_values} 个唯一值)
                <div style="margin-top: 5px;">主要类别: `;
            
            const topCategories = Object.entries(stats.top_categories).slice(0, 5);
            if (topCategories.length > 0) {
                categoricalStatsHTML += '<ul style="margin: 5px 0; padding-left: 20px;">';
                topCategories.forEach(([category, count]) => {
                    categoricalStatsHTML += `<li>${category}: ${count}次</li>`;
                });
                categoricalStatsHTML += '</ul>';
            } else {
                categoricalStatsHTML += '<span>无数据</span>';
            }
            
            categoricalStatsHTML += '</div></div>';
        });
    } else {
        categoricalStatsHTML = '<p>没有发现分类型列</p>';
    }
    
    document.getElementById('categoricalStatsContent').innerHTML = categoricalStatsHTML;
    
    // 显示数据预览
    const previewData = JSON.parse(data.preview);
    const analysisPreviewTable = document.getElementById('analysisPreviewTable');
    let tableHTML = '<thead><tr>';
    previewData.columns.forEach(col => tableHTML += `<th>${col}</th>`);
    tableHTML += '</tr></thead><tbody>';
    previewData.data.forEach(row => {
        tableHTML += '<tr>';
        row.forEach(cell => tableHTML += `<td>${cell !== null ? cell.toString().slice(0, 50) : ''}</td>`);
        tableHTML += '</tr>';
    });
    tableHTML += '</tbody>';
    analysisPreviewTable.innerHTML = tableHTML;
    
    // 显示AI分析报告
    const analysisContent = document.getElementById('aiAnalysisContent');
    let formattedReport = data.analysis_report
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/^# (.*?)$/gm, '<h3>$1</h3>')
        .replace(/^## (.*?)$/gm, '<h4>$1</h4>')
        .replace(/^- (.*?)$/gm, '<li>$1</li>');
    
    formattedReport = formattedReport.replace(/<li>(.*?)<\/li>/g, function(match) {
        return '<ul>' + match + '</ul>';
    }).replace(/<\/li><ul>/g, '</li>').replace(/<\/ul><li>/g, '<li>');
    
    analysisContent.innerHTML = formattedReport;
    
    // 处理可视化结果
    handleVisualizationResults(data);
}

function handleVisualizationResults(data) {
    const visualizationLoading = document.getElementById('visualizationLoading');
    const visualizationError = document.getElementById('visualizationError');
    const visualizationGallery = document.getElementById('visualizationGallery');
    
    if (!data.visualization) {
        visualizationLoading.style.display = 'none';
        visualizationError.style.display = 'block';
        document.getElementById('visualizationErrorMessage').textContent = '生成可视化时发生错误';
        return;
    }
    
    if (!data.visualization.success) {
        visualizationLoading.style.display = 'none';
        visualizationError.style.display = 'block';
        document.getElementById('visualizationErrorMessage').textContent = data.visualization.error || '生成可视化时发生错误';
        return;
    }
    
    visualizationLoading.style.display = 'none';
    visualizationGallery.style.display = 'block';
    
    visualizationGallery.innerHTML = '';
    
    data.visualization.images.forEach(image => {
        const chartItem = document.createElement('div');
        chartItem.className = 'chart-item';
        
        const img = document.createElement('img');
        img.src = `data:image/png;base64,${image.base64}`;
        img.alt = `可视化图表 ${image.index}`;
        
        const caption = document.createElement('div');
        caption.className = 'chart-caption';
        
        const title = document.createElement('span');
        title.textContent = `图表 ${image.index}`;
        
        const downloadLink = document.createElement('a');
        downloadLink.href = `/api/analysis_image/${data.analysis_id}/plot_${image.index}.png`;
        downloadLink.download = `plot_${image.index}.png`;
        downloadLink.textContent = '下载';
        downloadLink.className = 'download-btn';
        downloadLink.style.padding = '4px 8px';
        downloadLink.style.fontSize = '12px';
        downloadLink.style.textDecoration = 'none';
        
        caption.appendChild(title);
        caption.appendChild(downloadLink);
        
        chartItem.appendChild(img);
        chartItem.appendChild(caption);
        
        visualizationGallery.appendChild(chartItem);
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    init();
});

// 导出全局函数以便HTML调用
window.createNewSession = createNewSession;
window.switchSession = switchSession;
window.deleteSession = deleteSession;
window.toggleSettings = toggleSettings;
window.savePrompt = savePrompt;
window.clearKnowledge = clearKnowledge; 