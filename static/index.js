document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    const progressContainer = document.getElementById('progressContainer');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const documentsList = document.getElementById('documentsList');
    const docCount = document.getElementById('docCount');
    const listEmpty = document.getElementById('listEmpty');
    
    const chatMessages = document.getElementById('chatMessages');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const clearBtn = document.getElementById('clearBtn');
    const welcomeMessage = document.getElementById('welcomeMessage');
    const toast = document.getElementById('toast');

    // State Variables
    let isUploading = false;
    let isQuerying = false;

    // --- Toast Notifications ---
    function showToast(message, type = 'success') {
        toast.textContent = message;
        toast.className = `toast show ${type}`;
        setTimeout(() => {
            toast.classList.remove('show');
        }, 4000);
    }

    // --- API Service Calls ---

    // Fetch and display all uploaded documents
    async function fetchDocuments() {
        try {
            const response = await fetch('/api/documents');
            if (!response.ok) throw new Error('Không thể tải danh sách tài liệu');
            const docs = await response.json();
            
            renderDocuments(docs);
        } catch (error) {
            console.error('Error fetching documents:', error);
            showToast('Lỗi khi tải danh sách tài liệu: ' + error.message, 'error');
        }
    }

    // Fetch and display chat history
    async function fetchChatHistory() {
        try {
            const response = await fetch('/api/chat-history');
            if (!response.ok) throw new Error('Không thể tải lịch sử chat');
            const history = await response.json();
            
            // history is returned sorted desc (newest first). Let's reverse it to show oldest first in chat
            const chronologicalHistory = [...history].reverse();
            if (chronologicalHistory.length > 0) {
                welcomeMessage.style.display = 'none';
                chronologicalHistory.forEach(item => {
                    appendMessageBubble('user', item.question);
                    appendMessageBubble('bot', item.answer);
                });
                scrollToBottom();
            }
        } catch (error) {
            console.error('Error fetching history:', error);
            showToast('Lỗi tải lịch sử chat: ' + error.message, 'error');
        }
    }

    // Upload a document via XMLHttpRequest to get progress updates
    function uploadDocumentFile(file) {
        if (isUploading) return;
        isUploading = true;

        const formData = new FormData();
        formData.append('file', file);

        // UI Reset
        progressContainer.style.display = 'flex';
        progressFill.style.style = '0%';
        progressText.textContent = 'Đang tải lên: 0%';

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/upload', true);

        // Upload progress tracking
        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                progressFill.style.width = percentComplete + '%';
                progressText.textContent = `Đang tải lên: ${percentComplete}%`;
            }
        };

        xhr.onload = function() {
            isUploading = false;
            progressContainer.style.display = 'none';

            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const result = JSON.parse(xhr.responseText);
                    showToast(`Tải lên thành công: ${result.filename}`);
                    fetchDocuments(); // Refresh list
                } catch (e) {
                    showToast('Đã có lỗi phân tích phản hồi từ máy chủ.', 'error');
                }
            } else {
                let errorMsg = 'Lỗi tải lên tài liệu.';
                try {
                    const errorObj = JSON.parse(xhr.responseText);
                    errorMsg = errorObj.detail || errorMsg;
                } catch (e) {}
                showToast(errorMsg, 'error');
            }
        };

        xhr.onerror = function() {
            isUploading = false;
            progressContainer.style.display = 'none';
            showToast('Kết nối thất bại đến máy chủ API.', 'error');
        };

        xhr.send(formData);
    }

    // Submit user question
    async function submitQuestion(question) {
        if (isQuerying) return;
        isQuerying = true;

        // Hide welcome on first message
        if (welcomeMessage.style.display !== 'none') {
            welcomeMessage.style.display = 'none';
        }

        // Add user message to UI
        appendMessageBubble('user', question);
        scrollToBottom();

        // Add dummy bot bubble with skeleton loader
        const botBubbleId = 'bot-response-' + Date.now();
        appendMessageBubble('bot', '', botBubbleId, true);
        scrollToBottom();

        try {
            const response = await fetch('/api/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Không có phản hồi từ RAG Service');
            }

            const data = await response.json();
            
            // Replace loader with real answer
            updateBotBubble(botBubbleId, data.answer, data.sources);
        } catch (error) {
            console.error('Query Error:', error);
            updateBotBubble(botBubbleId, `⚠️ **Lỗi:** ${error.message}. Vui lòng thử lại sau.`, []);
            showToast(error.message, 'error');
        } finally {
            isQuerying = false;
        }
    }

    // --- DOM Rendering Helpers ---

    // Render list of documents
    function renderDocuments(docs) {
        docCount.textContent = docs.length;

        if (docs.length === 0) {
            listEmpty.style.display = 'block';
            // Clear existing document items but keep empty state
            const items = documentsList.querySelectorAll('.doc-item');
            items.forEach(el => el.remove());
            return;
        }

        listEmpty.style.display = 'none';
        
        // Remove existing items to rebuild list
        const items = documentsList.querySelectorAll('.doc-item');
        items.forEach(el => el.remove());

        docs.forEach(doc => {
            const dateStr = new Date(doc.uploaded_at).toLocaleString('vi-VN', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });

            const docItem = document.createElement('div');
            docItem.className = 'doc-item';
            docItem.innerHTML = `
                <svg class="doc-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2ZM13 9V3.5L18.5 9H13Z" fill="currentColor"/>
                </svg>
                <div class="doc-info">
                    <div class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</div>
                    <div class="doc-meta">Tải lên: ${dateStr}</div>
                </div>
            `;
            documentsList.appendChild(docItem);
        });
    }

    // Create a message bubble inside chat history view
    function appendMessageBubble(sender, text, customId = null, isLoader = false) {
        const msgWrapper = document.createElement('div');
        msgWrapper.className = `msg-wrapper ${sender}`;
        if (customId) {
            msgWrapper.id = customId;
        }

        const avatar = sender === 'user' ? '👤' : '🤖';
        const contentHtml = isLoader 
            ? `<div class="skeleton-loader">
                <div class="skeleton-line"></div>
                <div class="skeleton-line"></div>
                <div class="skeleton-line"></div>
               </div>` 
            : parseMarkdown(text);

        msgWrapper.innerHTML = `
            <div class="msg-avatar">${avatar}</div>
            <div class="msg-bubble">${contentHtml}</div>
        `;

        chatMessages.appendChild(msgWrapper);
    }

    // Update bot reply bubble content (removing skeleton)
    function updateBotBubble(id, text, sources) {
        const bubbleWrapper = document.getElementById(id);
        if (!bubbleWrapper) return;

        const bubble = bubbleWrapper.querySelector('.msg-bubble');
        if (!bubble) return;

        // Clear contents
        bubble.innerHTML = parseMarkdown(text);

        // If sources are present, create references accordion
        if (sources && sources.length > 0) {
            const sourcesContainer = document.createElement('div');
            sourcesContainer.className = 'sources-container';

            const toggleBtn = document.createElement('button');
            toggleBtn.className = 'sources-toggle';
            toggleBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="12" height="12">
                    <path d="M8.59 16.59L13.17 12L8.59 7.41L10 6L16 12L10 18L8.59 16.59Z" fill="currentColor"/>
                </svg>
                Nguồn trích dẫn (${sources.length})
            `;

            const contentDiv = document.createElement('div');
            contentDiv.className = 'sources-content';

            sources.forEach((source, index) => {
                const sourceItem = document.createElement('div');
                sourceItem.className = 'source-item';
                sourceItem.innerHTML = `
                    <div class="source-title">[${index + 1}] ${escapeHtml(source.filename)} (Đoạn #${source.chunk_id})</div>
                    <div class="source-snippet">${escapeHtml(source.content)}</div>
                `;
                contentDiv.appendChild(sourceItem);
            });

            // Toggle logic
            toggleBtn.addEventListener('click', () => {
                const isOpened = contentDiv.classList.toggle('show');
                toggleBtn.classList.toggle('active', isOpened);
                scrollToBottom();
            });

            sourcesContainer.appendChild(toggleBtn);
            sourcesContainer.appendChild(contentDiv);
            bubble.appendChild(sourcesContainer);
        }

        scrollToBottom();
    }

    // Simple parser for basic markdown elements
    function parseMarkdown(text) {
        // Escape HTML tags to prevent XSS
        let html = escapeHtml(text);

        // Code Blocks: ```code```
        html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

        // Inline Code: `code`
        html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');

        // Bold: **text**
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // Convert double newlines to paragraphs
        let paragraphs = html.split(/\n{2,}/g);
        let formatted = paragraphs.map(p => {
            // Replace single newlines within paragraph with <br>
            let lineBreaks = p.replace(/\n/g, '<br>');
            return `<p>${lineBreaks}</p>`;
        }).join('');

        return formatted;
    }

    // Escape HTML special characters
    function escapeHtml(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Scroll chat area to the bottom
    function scrollToBottom() {
        chatMessages.scrollTo({
            top: chatMessages.scrollHeight,
            behavior: 'smooth'
        });
    }

    // Auto resize input textarea
    function adjustTextareaHeight() {
        chatInput.style.height = 'auto';
        chatInput.style.height = (chatInput.scrollHeight) + 'px';
    }

    // --- Event Listeners ---

    // Drag-and-drop Events for Upload Zone
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadZone.classList.remove('dragover');
        }, false);
    });

    uploadZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            uploadDocumentFile(files[0]);
        }
    });

    // Clicking zone opens input selector
    uploadZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            uploadDocumentFile(fileInput.files[0]);
        }
    });

    // Chat Input Interaction
    chatInput.addEventListener('input', () => {
        adjustTextareaHeight();
        sendBtn.disabled = chatInput.value.trim() === '';
    });

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            const text = chatInput.value.trim();
            if (text !== '' && !isQuerying) {
                submitQuestion(text);
                chatInput.value = '';
                adjustTextareaHeight();
                sendBtn.disabled = true;
            }
        }
    });

    sendBtn.addEventListener('click', () => {
        const text = chatInput.value.trim();
        if (text !== '' && !isQuerying) {
            submitQuestion(text);
            chatInput.value = '';
            adjustTextareaHeight();
            sendBtn.disabled = true;
        }
    });

    // Clear Screen display (since there is no endpoint to delete chat history database entries,
    // we clear current DOM nodes to clean user's viewport)
    clearBtn.addEventListener('click', () => {
        // Clear all except welcome message
        const messages = chatMessages.querySelectorAll('.msg-wrapper');
        messages.forEach(el => el.remove());
        welcomeMessage.style.display = 'block';
        showToast('Đã dọn dẹp màn hình trò chuyện.');
    });

    // --- Initial Load ---
    fetchDocuments();
    fetchChatHistory();
});
