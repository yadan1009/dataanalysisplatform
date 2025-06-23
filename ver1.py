from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import json
import PyPDF2
import docx
import chardet
from datetime import datetime
import uuid

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 阿里云大模型 API 配置
API_KEY = "sk-98ab3de935d84bbd98da194d89ef97ea"
API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

# 文件上传配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'md'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 存储知识库内容和初始prompt
knowledge_base = {}
initial_prompt = {}
# 存储会话数据
sessions = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def detect_encoding(filepath):
    """检测文件编码"""
    with open(filepath, 'rb') as f:
        raw_data = f.read(10000)  # 读取前10000字节来检测编码
        result = chardet.detect(raw_data)
        return result['encoding']

def read_pdf_content(filepath):
    """读取PDF文件内容"""
    try:
        content = []
        with open(filepath, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                content.append(page.extract_text())
        return '\n'.join(content)
    except Exception as e:
        return f"PDF读取错误: {str(e)}"

def read_docx_content(filepath):
    """读取DOCX文件内容"""
    try:
        doc = docx.Document(filepath)
        content = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                content.append(paragraph.text)
        return '\n'.join(content)
    except Exception as e:
        return f"DOCX读取错误: {str(e)}"

def read_file_content(filepath):
    """读取文件内容，支持多种格式"""
    try:
        # 获取文件扩展名
        file_extension = filepath.rsplit('.', 1)[1].lower() if '.' in filepath else ''
        
        # 根据文件类型选择读取方法
        if file_extension == 'pdf':
            return read_pdf_content(filepath)
        elif file_extension == 'docx':
            return read_docx_content(filepath)
        elif file_extension == 'doc':
            # DOC格式较复杂，建议转换为DOCX
            return "DOC格式文件暂不支持，请转换为DOCX格式后上传"
        else:
            # 文本文件：尝试检测编码
            encoding = detect_encoding(filepath)
            if not encoding:
                encoding = 'utf-8'
            
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    return f.read()
            except:
                # 如果检测的编码失败，尝试常用编码
                for enc in ['utf-8', 'gbk', 'gb2312', 'utf-16', 'big5']:
                    try:
                        with open(filepath, 'r', encoding=enc) as f:
                            return f.read()
                    except:
                        continue
                return "无法读取文件内容：编码格式不支持"
    except Exception as e:
        return f"文件读取错误: {str(e)}"

def create_session(mode='normal', title=None):
    """创建新会话"""
    session_id = str(uuid.uuid4())
    now = datetime.now()
    sessions[session_id] = {
        'id': session_id,
        'mode': mode,
        'title': title or f"新对话",
        'messages': [],
        'created_at': now.isoformat(),
        'updated_at': now.isoformat()
    }
    return sessions[session_id]

def update_session_title(session_id, first_message):
    """根据第一条消息更新会话标题"""
    if session_id in sessions and sessions[session_id]['title'].startswith("新对话"):
        # 截取前30个字符作为标题
        title = first_message[:30] + "..." if len(first_message) > 30 else first_message
        sessions[session_id]['title'] = title

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        # 获取前端发送的消息和模式
        data = request.get_json()
        user_message = data.get('message', '')
        mode = data.get('mode', 'normal')
        session_id = data.get('session_id', 'default')
        
        if not user_message:
            return jsonify({'error': '消息不能为空'}), 400
        
        # 如果会话不存在或者是新会话，创建新会话
        if session_id == 'new' or session_id not in sessions:
            session = create_session(mode)
            session_id = session['id']
            
            # 迁移临时设置到新会话
            if 'temp' in initial_prompt:
                initial_prompt[session_id] = initial_prompt['temp']
                del initial_prompt['temp']
            if 'temp' in knowledge_base:
                knowledge_base[session_id] = knowledge_base['temp']
                del knowledge_base['temp']
        else:
            session = sessions[session_id]
        
        # 如果是第一条消息，更新标题
        if len(session['messages']) == 0:
            update_session_title(session_id, user_message)
        
        # 构造请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        # 构造消息列表
        messages = []
        
        # 根据模式添加系统消息
        if mode == 'normal' and session_id in initial_prompt:
            # 普通模式，使用初始prompt
            messages.append({
                "role": "system",
                "content": initial_prompt[session_id]
            })
        elif mode == 'knowledge' and session_id in knowledge_base:
            # 知识库模式，将知识库内容作为上下文
            kb_content = "\n\n".join(knowledge_base[session_id])
            system_message = f"你是一个智能助手。请基于以下知识库内容回答用户的问题。如果问题与知识库内容相关，请优先使用知识库中的信息进行回答。\n\n知识库内容：\n{kb_content}"
            messages.append({
                "role": "system",
                "content": system_message
            })
        
        # 添加历史消息（最多保留最近10轮对话）
        history_messages = session['messages'][-20:] if len(session['messages']) > 20 else session['messages']
        for msg in history_messages:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        # 添加用户消息
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # 构造请求体
        payload = {
            "model": "qwen-turbo",
            "input": {
                "messages": messages
            },
            "parameters": {
                "temperature": 0.7,
                "max_tokens": 1000
            }
        }
        
        # 调用阿里云大模型 API
        response = requests.post(API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            # 提取 AI 回复内容
            ai_reply = result.get('output', {}).get('text', '抱歉，我无法回答这个问题。')
            
            # 保存消息到会话历史
            session['messages'].append({
                'role': 'user',
                'content': user_message,
                'timestamp': datetime.now().isoformat()
            })
            session['messages'].append({
                'role': 'assistant',
                'content': ai_reply,
                'timestamp': datetime.now().isoformat()
            })
            session['updated_at'] = datetime.now().isoformat()
            
            return jsonify({
                'reply': ai_reply,
                'session_id': session_id
            })
        else:
            return jsonify({'error': 'API 调用失败'}), 500
            
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """获取所有会话列表"""
    try:
        # 只返回有消息的会话，按更新时间倒序排列
        session_list = [s for s in sessions.values() if len(s['messages']) > 0]
        session_list = sorted(session_list, 
                            key=lambda x: x['updated_at'], 
                            reverse=True)
        return jsonify(session_list)
    except Exception as e:
        return jsonify({'error': f'获取会话列表失败: {str(e)}'}), 500

@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """获取特定会话的详情"""
    try:
        if session_id in sessions:
            return jsonify(sessions[session_id])
        else:
            return jsonify({'error': '会话不存在'}), 404
    except Exception as e:
        return jsonify({'error': f'获取会话失败: {str(e)}'}), 500

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """删除会话"""
    try:
        if session_id in sessions:
            del sessions[session_id]
            # 同时删除相关的知识库和prompt
            if session_id in knowledge_base:
                del knowledge_base[session_id]
            if session_id in initial_prompt:
                del initial_prompt[session_id]
            return jsonify({'success': True})
        else:
            return jsonify({'error': '会话不存在'}), 404
    except Exception as e:
        return jsonify({'error': f'删除会话失败: {str(e)}'}), 500

@app.route('/api/sessions/new', methods=['POST'])
def new_session():
    """创建新会话"""
    try:
        data = request.get_json()
        mode = data.get('mode', 'normal')
        title = data.get('title', None)
        session = create_session(mode, title)
        return jsonify(session)
    except Exception as e:
        return jsonify({'error': f'创建会话失败: {str(e)}'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """处理文件上传"""
    try:
        session_id = request.form.get('session_id', 'default')
        
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
            file.save(filepath)
            
            # 读取文件内容并添加到知识库
            content = read_file_content(filepath)
            if session_id not in knowledge_base:
                knowledge_base[session_id] = []
            
            # 检查内容是否读取成功
            if "错误" in content or "不支持" in content:
                # 删除临时文件
                os.remove(filepath)
                return jsonify({'error': f'文件读取失败: {content}'}), 400
            
            # 添加到知识库，包含文件信息和内容长度
            file_info = f"文件：{filename}\n内容长度：{len(content)}字符\n内容：{content[:500]}..." if len(content) > 500 else f"文件：{filename}\n内容：{content}"
            knowledge_base[session_id].append(file_info)
            
            # 删除临时文件
            os.remove(filepath)
            
            return jsonify({'success': True, 'filename': filename, 'content_length': len(content)})
        else:
            return jsonify({'error': '不支持的文件类型'}), 400
            
    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@app.route('/api/set_prompt', methods=['POST'])
def set_prompt():
    """设置初始prompt"""
    try:
        data = request.get_json()
        session_id = data.get('session_id', 'default')
        prompt = data.get('prompt', '')
        
        initial_prompt[session_id] = prompt
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': f'设置失败: {str(e)}'}), 500

@app.route('/api/clear_knowledge', methods=['POST'])
def clear_knowledge():
    """清空知识库"""
    try:
        data = request.get_json()
        session_id = data.get('session_id', 'default')
        
        if session_id in knowledge_base:
            knowledge_base[session_id] = []
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': f'清空失败: {str(e)}'}), 500

@app.route('/')
def index():
    # 返回前端 HTML 页面
    return '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TongYiQianWenWeb</title>
        <style>
            * {
                box-sizing: border-box;
                transition: background-color 0.3s, border-color 0.3s, box-shadow 0.3s;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f8faf9;
                display: flex;
                height: 100vh;
                color: #2c3e50;
                overflow: hidden;
            }
            
            /* 页面加载动画 */
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            .fade-in {
                animation: fadeIn 0.5s ease-out;
            }
            
            /* 侧边栏动画 */
            .sidebar {
                width: 260px;
                background-color: #ffffff;
                border-right: 1px solid #e5e8e6;
                overflow-y: auto;
                flex-shrink: 0;
                transition: transform 0.3s ease-out;
                animation: slideInLeft 0.5s ease-out;
            }
            
            @keyframes slideInLeft {
                from { transform: translateX(-100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            
            .sidebar-header {
                padding: 20px;
                border-bottom: 1px solid #e5e8e6;
                background-color: #73BF00;
                color: white;
            }
            .sidebar-header h2 {
                margin: 0;
                font-size: 20px;
                font-weight: 500;
            }
            h3 {
                margin: 0 0 15px 0;
                font-size: 18px;
                font-weight: 500;
                color: #2c3e50;
            }
            h4 {
                margin: 15px 0 10px 0;
                font-size: 16px;
                font-weight: 500;
                color: #2c3e50;
            }
            .new-chat-btn {
                width: 90%;
                margin: 15px auto;
                padding: 12px;
                background-color: #73BF00;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 15px;
                display: block;
                transition: all 0.3s ease;
            }
            .new-chat-btn:hover {
                background-color: #5fa000;
                transform: translateY(-2px);
                box-shadow: 0 4px 10px rgba(115, 191, 0, 0.3);
            }
            .new-chat-btn:active {
                transform: translateY(0);
                box-shadow: 0 2px 5px rgba(115, 191, 0, 0.3);
            }
            .session-list {
                padding: 10px;
                animation: fadeIn 0.6s ease-out;
            }
            .session-item {
                padding: 12px 15px;
                margin: 0 10px 8px 10px;
                border-radius: 8px;
                cursor: pointer;
                position: relative;
                transition: all 0.3s ease;
                background-color: #f8faf9;
                border: 1px solid transparent;
                transform-origin: center;
            }
            .session-item:hover {
                background-color: #e8f5e0;
                border-color: #73BF00;
                transform: scale(1.02);
            }
            .session-item.active {
                background-color: #e8f5e0;
                border-color: #73BF00;
                box-shadow: 0 1px 3px rgba(115, 191, 0, 0.1);
                animation: pulseGreen 2s infinite;
            }
            
            @keyframes pulseGreen {
                0% { box-shadow: 0 0 0 0 rgba(115, 191, 0, 0.4); }
                70% { box-shadow: 0 0 0 6px rgba(115, 191, 0, 0); }
                100% { box-shadow: 0 0 0 0 rgba(115, 191, 0, 0); }
            }
            
            .session-title {
                font-size: 14px;
                margin-bottom: 4px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                color: #2c3e50;
                font-weight: 500;
            }
            .session-info {
                font-size: 12px;
                color: #7f8c8d;
            }
            .session-delete {
                position: absolute;
                right: 10px;
                top: 50%;
                transform: translateY(-50%);
                background: none;
                border: none;
                color: #e74c3c;
                cursor: pointer;
                opacity: 0;
                transition: all 0.3s ease;
                font-size: 18px;
                padding: 4px;
            }
            .session-item:hover .session-delete {
                opacity: 1;
                transform: translateY(-50%) rotate(0deg);
            }
            .session-delete:hover {
                color: #c0392b;
                transform: translateY(-50%) rotate(90deg);
            }
            .main-content {
                flex: 1;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                background-color: #ffffff;
                animation: fadeIn 0.5s ease-out;
            }
            .header {
                background: white;
                padding: 15px 20px;
                border-bottom: 1px solid #e5e8e6;
                display: flex;
                justify-content: space-between;
                align-items: center;
                animation: slideInDown 0.5s ease-out;
            }
            
            @keyframes slideInDown {
                from { transform: translateY(-50px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
            
            .mode-display {
                display: flex;
                align-items: center;
                gap: 15px;
            }
            .current-mode {
                font-size: 14px;
                color: #7f8c8d;
            }
            .current-mode span {
                color: #73BF00;
                font-weight: 500;
                position: relative;
                display: inline-block;
                transition: color 0.3s;
            }
            .current-mode span::after {
                content: '';
                position: absolute;
                width: 100%;
                height: 2px;
                bottom: -2px;
                left: 0;
                background-color: #73BF00;
                transform: scaleX(0);
                transform-origin: bottom right;
                transition: transform 0.3s;
            }
            .current-mode:hover span::after {
                transform: scaleX(1);
                transform-origin: bottom left;
            }
            .settings-btn {
                padding: 8px 16px;
                background-color: transparent;
                color: #73BF00;
                border: 1px solid #73BF00;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            .settings-btn::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: rgba(115, 191, 0, 0.2);
                transition: all 0.4s ease;
            }
            .settings-btn:hover {
                background-color: #73BF00;
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(115, 191, 0, 0.2);
            }
            .settings-btn:hover::before {
                left: 100%;
            }
            .settings-btn:active {
                transform: translateY(0);
                box-shadow: 0 2px 4px rgba(115, 191, 0, 0.2);
            }
            .settings-panel {
                position: absolute;
                top: 60px;
                right: 20px;
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.15);
                display: none;
                z-index: 1000;
                width: 350px;
                max-height: 80vh;
                overflow-y: auto;
                opacity: 0;
                transform: translateY(-20px) scale(0.95);
                transition: opacity 0.3s, transform 0.3s;
            }
            .settings-panel.active {
                display: block;
                opacity: 1;
                transform: translateY(0) scale(1);
                animation: settingsPanelIn 0.3s ease-out;
            }
            
            @keyframes settingsPanelIn {
                from { opacity: 0; transform: translateY(-20px) scale(0.95); }
                to { opacity: 1; transform: translateY(0) scale(1); }
            }
            
            .settings-close {
                position: absolute;
                top: 15px;
                right: 15px;
                background: none;
                border: none;
                font-size: 20px;
                cursor: pointer;
                color: #7f8c8d;
                transition: all 0.3s ease;
            }
            .settings-close:hover {
                color: #e74c3c;
                transform: rotate(90deg);
            }
            .mode-selector {
                margin-bottom: 20px;
            }
            .mode-option {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 10px;
                margin-bottom: 8px;
                border: 1px solid #e5e8e6;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .mode-option:hover {
                border-color: #73BF00;
                background-color: #f8faf9;
                transform: translateX(5px);
            }
            .mode-option input[type="radio"] {
                transition: all 0.3s ease;
            }
            .mode-option input[type="radio"]:checked + label {
                color: #73BF00;
                font-weight: 500;
            }
            .mode-option.locked {
                opacity: 0.6;
                pointer-events: none;
            }
            .mode-option.locked label::after {
                content: "🔒";
                margin-left: 5px;
            }
             
            .mode-lock-tip {
                color: #e67e22;
                font-size: 13px;
                margin-top: 10px;
                display: none;
                background-color: #fef5e7;
                padding: 10px 14px;
                border-radius: 6px;
                border-left: 3px solid #e67e22;
                animation: shake 0.5s ease-in-out;
            }
            
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
                20%, 40%, 60%, 80% { transform: translateX(5px); }
            }
            
            .chat-container {
                flex: 1;
                background: white;
                padding: 20px;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                animation: fadeIn 0.5s ease-out;
            }
            .chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                margin-bottom: 20px;
                background-color: #fafbfa;
                border-radius: 10px;
                scroll-behavior: smooth;
                position: relative;
            }
            
            /* 打字机效果 */
            .typing::after {
                content: '|';
                animation: typing 1s infinite;
                margin-left: 2px;
            }
            
            @keyframes typing {
                0%, 100% { opacity: 1; }
                50% { opacity: 0; }
            }
            .message {
                margin-bottom: 20px;
                display: flex;
                align-items: flex-start;
                gap: 12px;
                opacity: 0;
                transform: translateY(20px);
                animation: messageIn 0.5s forwards;
            }
            
            @keyframes messageIn {
                to { opacity: 1; transform: translateY(0); }
            }
            
            .message-avatar {
                width: 36px;
                height: 36px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
                flex-shrink: 0;
                transition: all 0.3s ease;
            }
            .message:hover .message-avatar {
                transform: scale(1.1);
            }
            .user-message {
                flex-direction: row-reverse;
                animation-delay: 0.1s;
            }
            .user-message .message-avatar {
                background-color: #73BF00;
                color: white;
            }
            .ai-message .message-avatar {
                background-color: #e5e8e6;
                color: #2c3e50;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0% { box-shadow: 0 0 0 0 rgba(115, 191, 0, 0.4); }
                70% { box-shadow: 0 0 0 8px rgba(115, 191, 0, 0); }
                100% { box-shadow: 0 0 0 0 rgba(115, 191, 0, 0); }
            }
            
            .message-content {
                max-width: 70%;
                padding: 12px 16px;
                border-radius: 12px;
                line-height: 1.5;
                transition: all 0.3s ease;
                transform-origin: left center;
            }
            .message:hover .message-content {
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            }
            .user-message .message-content {
                background-color: #73BF00;
                color: white;
                border-bottom-right-radius: 4px;
                transform-origin: right center;
            }
            .ai-message .message-content {
                background-color: white;
                color: #2c3e50;
                border: 1px solid #e5e8e6;
                border-bottom-left-radius: 4px;
                white-space: pre-wrap;
            }
            .input-container {
                display: flex;
                gap: 12px;
                padding: 20px;
                background-color: #f8faf9;
                border-radius: 12px;
                transition: all 0.3s ease;
                animation: slideInUp 0.5s ease-out;
            }
            
            @keyframes slideInUp {
                from { transform: translateY(50px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
            
            .input-container:focus-within {
                box-shadow: 0 5px 15px rgba(115, 191, 0, 0.1);
                transform: translateY(-2px);
            }
            #messageInput {
                flex: 1;
                padding: 14px 18px;
                border: 1px solid #e5e8e6;
                border-radius: 8px;
                font-size: 15px;
                outline: none;
                transition: all 0.3s ease;
            }
            #messageInput:focus {
                border-color: #73BF00;
                box-shadow: 0 0 0 3px rgba(115, 191, 0, 0.2);
            }
            #sendButton {
                padding: 14px 24px;
                background-color: #73BF00;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 15px;
                font-weight: 500;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            #sendButton::after {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                width: 5px;
                height: 5px;
                background: rgba(255, 255, 255, 0.5);
                opacity: 0;
                border-radius: 100%;
                transform: scale(1, 1) translate(-50%);
                transform-origin: 50% 50%;
            }
            #sendButton:hover {
                background-color: #5fa000;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(115, 191, 0, 0.3);
            }
            #sendButton:active::after {
                animation: ripple 0.6s ease-out;
            }
            
            @keyframes ripple {
                0% { transform: scale(0, 0); opacity: 1; }
                20% { transform: scale(25, 25); opacity: 0.8; }
                100% { transform: scale(50, 50); opacity: 0; }
            }
            
            #sendButton:disabled {
                background-color: #c8e6c9;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }
            .prompt-textarea {
                width: 100%;
                min-height: 100px;
                padding: 12px;
                border: 1px solid #e5e8e6;
                border-radius: 8px;
                resize: vertical;
                margin-bottom: 10px;
                font-size: 14px;
                outline: none;
                transition: all 0.3s ease;
            }
            .prompt-textarea:focus {
                border-color: #73BF00;
                box-shadow: 0 0 0 3px rgba(115, 191, 0, 0.1);
            }
            .file-upload-area {
                border: 2px dashed #73BF00;
                border-radius: 8px;
                padding: 30px;
                text-align: center;
                margin-bottom: 15px;
                background-color: #f8fdf6;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            .file-upload-area:hover {
                background-color: #e8f5e0;
                border-color: #5fa000;
                transform: translateY(-2px);
            }
            .file-upload-area::after {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
                transition: 0.3s;
            }
            .file-upload-area:hover::after {
                left: 100%;
            }
            .file-list {
                margin-top: 15px;
            }
            .file-item {
                background-color: #e8f5e0;
                color: #2c3e50;
                padding: 8px 12px;
                border-radius: 6px;
                margin-bottom: 8px;
                display: inline-block;
                margin-right: 8px;
                font-size: 14px;
                transition: all 0.3s ease;
                animation: fileItemIn 0.3s ease-out;
            }
            
            @keyframes fileItemIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .file-item:hover {
                background-color: #73BF00;
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .btn-secondary {
                padding: 10px 18px;
                background-color: transparent;
                color: #73BF00;
                border: 1px solid #73BF00;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            .btn-secondary::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: rgba(115, 191, 0, 0.2);
                transition: all 0.4s ease;
            }
            .btn-secondary:hover {
                background-color: #73BF00;
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 4px 10px rgba(115, 191, 0, 0.2);
            }
            .btn-secondary:hover::before {
                left: 100%;
            }
            .btn-secondary:active {
                transform: translateY(0);
                box-shadow: 0 2px 5px rgba(115, 191, 0, 0.2);
            }
             
            /* 滚动条美化 */
            ::-webkit-scrollbar {
                width: 8px;
                height: 8px;
            }
            
            ::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 10px;
            }
            
            ::-webkit-scrollbar-thumb {
                background: #c8e6c9;
                border-radius: 10px;
                transition: background 0.3s ease;
            }
            
            ::-webkit-scrollbar-thumb:hover {
                background: #73BF00;
            }
            
            /* 响应式设计 */
            @media (max-width: 768px) {
                .sidebar {
                    width: 200px;
                }
                .settings-panel {
                    width: 300px;
                    right: 10px;
                }
            }
            
            @media (max-width: 600px) {
                body {
                    flex-direction: column;
                }
                .sidebar {
                    width: 100%;
                    height: 200px;
                    order: 2;
                }
                .main-content {
                    order: 1;
                }
                .settings-panel {
                    width: calc(100% - 40px);
                    left: 20px;
                    right: 20px;
                }
            }

            /* 波纹效果 */
            button {
                position: relative;
                overflow: hidden;
            }
            .ripple {
                position: absolute;
                border-radius: 50%;
                background-color: rgba(255, 255, 255, 0.4);
                transform: scale(0);
                animation: ripple-effect 0.6s linear;
                pointer-events: none;
            }
            
            @keyframes ripple-effect {
                0% { transform: scale(0); opacity: 1; }
                80% { transform: scale(1.5); opacity: 0.5; }
                100% { transform: scale(2); opacity: 0; }
            }

            /* 按钮加载动画 */
            .btn-loading {
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                border-top-color: #fff;
                animation: spin 1s ease-in-out infinite;
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            /* 波纹效果 */
        </style>
    </head>
    <body>
        <!-- 侧边栏 -->
        <div class="sidebar">
            <div class="sidebar-header">
                <h2>通义千问Web</h2>
            </div>
            <div class="session-list">
                <button class="new-chat-btn" onclick="createNewSession()">
                    <span>+ 新建对话</span>
                </button>
                <div id="sessionList"></div>
            </div>
        </div>

        <!-- 主内容区 -->
        <div class="main-content fade-in">
            <div class="header">
                <div class="mode-display">
                    <div class="current-mode">当前模式：<span id="currentModeText">普通模式</span></div>
                </div>
                <button class="settings-btn" onclick="toggleSettings()">⚙️ 设置</button>
            </div>

            <!-- 设置面板（二级界面） -->
            <div id="settingsPanel" class="settings-panel">
                <button class="settings-close" onclick="toggleSettings()">×</button>
                <h3>对话设置</h3>
                
                <div class="mode-selector">
                    <h4>选择模式</h4>
                    <div class="mode-option">
                        <input type="radio" id="normalMode" name="mode" value="normal" checked>
                        <label for="normalMode">普通模式</label>
                    </div>
                    <div class="mode-option">
                        <input type="radio" id="knowledgeMode" name="mode" value="knowledge">
                        <label for="knowledgeMode">知识库模式</label>
                    </div>
                    <div class="mode-lock-tip" id="modeLockTip">会话进行中，模式已锁定。新建对话可切换模式。</div>
                </div>

                <!-- 普通模式设置 -->
                <div id="normalSettings" style="margin-top: 20px;">
                    <h4>普通模式设置</h4>
                    <p style="color: #7f8c8d; font-size: 14px;">在对话开始前设置AI的初始人设和行为：</p>
                    <textarea id="initialPrompt" class="prompt-textarea" 
                        placeholder="例如：你是一个友好的助手，请用简洁明了的方式回答问题。"></textarea>
                    <button onclick="savePrompt()" class="btn-secondary">保存设置</button>
                </div>

                <!-- 知识库模式设置 -->
                <div id="knowledgeSettings" style="display: none; margin-top: 20px;">
                    <h4>知识库模式设置</h4>
                    <p style="color: #7f8c8d; font-size: 14px;">支持上传 TXT、PDF、DOCX、MD 格式的文件</p>
                    <div class="file-upload-area">
                        <p>拖拽文件到此处或点击上传</p>
                        <input type="file" id="fileInput" style="display: none;" accept=".txt,.pdf,.doc,.docx,.md">
                        <button onclick="document.getElementById('fileInput').click()" class="btn-secondary">选择文件</button>
                    </div>
                    <div id="fileList" class="file-list"></div>
                    <div id="uploadStatus" style="margin-top: 10px; color: #7f8c8d; font-size: 14px;"></div>
                    <button onclick="clearKnowledge()" class="btn-secondary">清空知识库</button>
                </div>
            </div>

            <div class="chat-container">
                <div id="chatMessages" class="chat-messages"></div>
                <div class="input-container">
                    <input type="text" id="messageInput" placeholder="请输入您的问题..." />
                    <button id="sendButton">发送</button>
                </div>
            </div>
        </div>

        <script>
            const chatMessages = document.getElementById('chatMessages');
            const messageInput = document.getElementById('messageInput');
            const sendButton = document.getElementById('sendButton');
            const fileInput = document.getElementById('fileInput');
            let currentSessionId = null;
            let currentMode = 'normal';
            let uploadedFiles = [];

            // 初始化
            async function init() {
                await loadSessions();
                updateModeDisplay();
            }

            // 加载会话列表
            async function loadSessions() {
                try {
                    const response = await fetch('/api/sessions');
                    const sessions = await response.json();
                    renderSessionList(sessions);
                } catch (error) {
                    console.error('加载会话列表失败:', error);
                }
            }

            // 渲染会话列表
            function renderSessionList(sessions) {
                const sessionList = document.getElementById('sessionList');
                sessionList.innerHTML = sessions.map(session => {
                    const date = new Date(session.updated_at);
                    const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                    return `
                        <div class="session-item ${session.id === currentSessionId ? 'active' : ''}" 
                             onclick="switchSession('${session.id}')">
                            <div class="session-title">${session.title}</div>
                            <div class="session-info">${session.mode}模式 · ${dateStr}</div>
                            <button class="session-delete" onclick="deleteSession(event, '${session.id}')">×</button>
                        </div>
                    `;
                }).join('');
            }

            // 创建新会话（用于手动点击新建对话按钮）
            async function createNewSession() {
                currentSessionId = null;
                clearChat();
                uploadedFiles = [];
                updateFileList();
                updateModeDisplay(); // 更新模式选择器状态
                // 不实际创建会话，等待用户发送第一条消息
            }

            // 切换会话
            async function switchSession(sessionId) {
                try {
                    const response = await fetch(`/api/sessions/${sessionId}`);
                    const session = await response.json();
                    currentSessionId = sessionId;
                    currentMode = session.mode;
                    
                    // 更新模式选择器
                    document.querySelector(`input[name="mode"][value="${currentMode}"]`).checked = true;
                    updateModeDisplay();
                    
                    // 清空聊天区域并加载历史消息
                    clearChat();
                    session.messages.forEach(msg => {
                        addMessage(msg.content, msg.role === 'user');
                    });
                    
                    await loadSessions();
                    updateModeDisplay(); // 更新模式选择器状态
                } catch (error) {
                    console.error('切换会话失败:', error);
                }
            }

            // 删除会话
            async function deleteSession(event, sessionId) {
                event.stopPropagation();
                if (!confirm('确定要删除这个会话吗？')) return;
                
                try {
                    const response = await fetch(`/api/sessions/${sessionId}`, {
                        method: 'DELETE'
                    });
                    
                    if (response.ok) {
                        if (sessionId === currentSessionId) {
                            // 如果删除的是当前会话，重置状态但不创建新会话
                            currentSessionId = null;
                            clearChat();
                            uploadedFiles = [];
                            updateFileList();
                            updateModeDisplay(); // 更新模式选择器状态
                        }
                        await loadSessions();
                    }
                } catch (error) {
                    console.error('删除会话失败:', error);
                }
            }

            // 清空聊天区域
            function clearChat() {
                chatMessages.innerHTML = '';
                addMessage('您好！我有什么可以帮助您的吗？', false);
            }

            // 模式切换
            document.querySelectorAll('input[name="mode"]').forEach(radio => {
                radio.addEventListener('change', async function(e) {
                    // 如果已有会话，不允许切换模式
                    if (currentSessionId && currentSessionId !== 'new') {
                        e.preventDefault();
                        // 恢复原来的选择
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

            // 更新模式显示
            function updateModeDisplay() {
                // 更新当前模式文本
                const modeText = currentMode === 'normal' ? '普通模式' : '知识库模式';
                document.getElementById('currentModeText').textContent = modeText;
                
                // 更新设置面板内的模式设置区域
                document.getElementById('normalSettings').style.display = 
                    currentMode === 'normal' ? 'block' : 'none';
                document.getElementById('knowledgeSettings').style.display = 
                    currentMode === 'knowledge' ? 'block' : 'none';
                    
                // 更新模式选择器的状态
                const modeInputs = document.querySelectorAll('input[name="mode"]');
                const hasActiveSession = currentSessionId && currentSessionId !== 'new';
                const modeLockTip = document.getElementById('modeLockTip');
                const modeOptions = document.querySelectorAll('.mode-option');
                
                // 显示或隐藏锁定提示
                modeLockTip.style.display = hasActiveSession ? 'block' : 'none';
                
                // 更新模式选项的样式
                modeOptions.forEach(option => {
                    if (hasActiveSession) {
                        option.classList.add('locked');
                    } else {
                        option.classList.remove('locked');
                    }
                });
                
                modeInputs.forEach(input => {
                    input.disabled = hasActiveSession;
                    const label = input.nextElementSibling;
                    if (hasActiveSession) {
                        label.style.opacity = '0.6';
                        label.style.cursor = 'not-allowed';
                        label.title = '会话进行中，无法切换模式';
                    } else {
                        label.style.opacity = '1';
                        label.style.cursor = 'pointer';
                        label.title = '';
                    }
                });
            }

            // 切换设置面板
            function toggleSettings() {
                const panel = document.getElementById('settingsPanel');
                panel.classList.toggle('active');
            }

            // 点击外部关闭设置面板
            document.addEventListener('click', function(event) {
                const panel = document.getElementById('settingsPanel');
                const settingsBtn = document.querySelector('.settings-btn');
                if (!panel.contains(event.target) && !settingsBtn.contains(event.target)) {
                    panel.classList.remove('active');
                }
            });

            function addMessage(content, isUser) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
                
                // 设置动画延迟，使消息依次显示
                messageDiv.style.animationDelay = `${chatMessages.childElementCount * 0.1}s`;
                
                // 创建头像
                const avatar = document.createElement('div');
                avatar.className = 'message-avatar';
                avatar.textContent = isUser ? '我' : 'AI';
                
                // 创建消息内容
                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';
                contentDiv.textContent = content;
                
                messageDiv.appendChild(avatar);
                messageDiv.appendChild(contentDiv);
                chatMessages.appendChild(messageDiv);
                
                // 平滑滚动到底部
                setTimeout(() => {
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }, 50);
            }

            async function sendMessage() {
                const message = messageInput.value.trim();
                if (!message) return;

                // 显示用户消息
                addMessage(message, true);
                messageInput.value = '';
                sendButton.disabled = true;
                sendButton.innerHTML = '<span class="btn-loading"></span>';
                
                // 创建一个占位消息元素
                const placeholderDiv = document.createElement('div');
                placeholderDiv.className = 'message ai-message';
                
                const avatar = document.createElement('div');
                avatar.className = 'message-avatar';
                avatar.textContent = 'AI';
                
                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content typing';
                contentDiv.textContent = '思考中';
                
                placeholderDiv.appendChild(avatar);
                placeholderDiv.appendChild(contentDiv);
                chatMessages.appendChild(placeholderDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;

                try {
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ 
                            message: message,
                            mode: currentMode,
                            session_id: currentSessionId || 'new'
                        })
                    });

                    const data = await response.json();
                    
                    // 移除占位消息
                    chatMessages.removeChild(placeholderDiv);
                    
                    if (response.ok) {
                        // 添加实际消息（带有打字机效果）
                        addMessageWithTypingEffect(data.reply, false);
                        
                        // 更新session_id（如果是新会话）
                        if (data.session_id && data.session_id !== currentSessionId) {
                            currentSessionId = data.session_id;
                            await loadSessions();
                            updateModeDisplay(); // 更新模式选择器状态
                        }
                    } else {
                        addMessage(`错误: ${data.error}`, false);
                    }
                } catch (error) {
                    // 移除占位消息
                    chatMessages.removeChild(placeholderDiv);
                    addMessage(`网络错误: ${error.message}`, false);
                }

                sendButton.disabled = false;
                sendButton.innerHTML = '发送';
            }
            
            // 添加带打字机效果的消息
            function addMessageWithTypingEffect(content, isUser) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
                
                // 创建头像
                const avatar = document.createElement('div');
                avatar.className = 'message-avatar';
                avatar.textContent = isUser ? '我' : 'AI';
                
                // 创建消息内容
                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';
                contentDiv.textContent = '';
                
                messageDiv.appendChild(avatar);
                messageDiv.appendChild(contentDiv);
                chatMessages.appendChild(messageDiv);
                
                // 打字机效果
                let i = 0;
                const typingSpeed = 20; // 每个字符的延迟(ms)
                
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

            // 保存初始prompt
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
                        alert('设置已保存');
                    } else {
                        alert('保存失败');
                    }
                } catch (error) {
                    alert('保存失败: ' + error.message);
                }
            }

                         // 文件上传
             fileInput.addEventListener('change', async function(e) {
                 const file = e.target.files[0];
                 if (!file) return;

                 const uploadStatus = document.getElementById('uploadStatus');
                 uploadStatus.textContent = '正在上传和处理文件...';
                 uploadStatus.style.color = '#007bff';

                 const formData = new FormData();
                 formData.append('file', file);
                 formData.append('session_id', currentSessionId || 'temp');

                 try {
                     const response = await fetch('/api/upload', {
                         method: 'POST',
                         body: formData
                     });

                     const data = await response.json();
                     
                     if (response.ok) {
                         uploadedFiles.push({
                             name: data.filename,
                             size: data.content_length || 0
                         });
                         updateFileList();
                         uploadStatus.textContent = `文件上传成功！已读取 ${data.content_length || 0} 个字符`;
                         uploadStatus.style.color = '#28a745';
                     } else {
                         uploadStatus.textContent = '上传失败: ' + data.error;
                         uploadStatus.style.color = '#dc3545';
                     }
                 } catch (error) {
                     uploadStatus.textContent = '上传失败: ' + error.message;
                     uploadStatus.style.color = '#dc3545';
                 }
                 
                 fileInput.value = '';
             });

                         // 更新文件列表显示
             function updateFileList() {
                 const fileList = document.getElementById('fileList');
                 fileList.innerHTML = uploadedFiles.map(file => {
                     const fileName = typeof file === 'string' ? file : file.name;
                     const fileSize = typeof file === 'object' && file.size ? ` (${file.size} 字符)` : '';
                     return `<div class="file-item">${fileName}${fileSize}</div>`;
                 }).join('');
             }

            // 清空知识库
            async function clearKnowledge() {
                // 如果有活动会话，提示用户
                if (currentSessionId && currentSessionId !== 'new') {
                    alert('会话进行中，无法清空知识库。请新建对话后再试。');
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
                        alert('知识库已清空');
                    } else {
                        alert('清空失败');
                    }
                } catch (error) {
                    alert('清空失败: ' + error.message);
                }
            }

            sendButton.addEventListener('click', sendMessage);
            messageInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });

            // 添加波纹效果
            function createRipple(event, element) {
                const button = element || this;
                const circle = document.createElement('span');
                const diameter = Math.max(button.clientWidth, button.clientHeight);
                const radius = diameter / 2;
                
                const rect = button.getBoundingClientRect();
                
                circle.style.width = circle.style.height = `${diameter}px`;
                circle.style.left = `${event.clientX - rect.left - radius}px`;
                circle.style.top = `${event.clientY - rect.top - radius}px`;
                circle.classList.add('ripple');
                
                const ripple = button.querySelector('.ripple');
                if (ripple) {
                    ripple.remove();
                }
                
                button.appendChild(circle);
            }
            
            // 为按钮添加波纹效果
            document.querySelectorAll('button').forEach(button => {
                button.addEventListener('click', createRipple);
            });
            
            // 初始化应用
            document.addEventListener('DOMContentLoaded', function() {
                init();
                
                // 给body添加fade-in动画
                document.body.classList.add('fade-in');
            });
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
