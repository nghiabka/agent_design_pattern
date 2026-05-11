document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatHistory = document.getElementById('chat-history');
    const refreshMemoryBtn = document.getElementById('refresh-memory');

    // Configure Marked.js
    marked.setOptions({
        breaks: true,
        gfm: true
    });

    // Auto-resize textarea
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // Handle Enter key (Shift+Enter for newline)
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    function appendUserMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message user';
        msgDiv.innerHTML = `
            <div class="avatar">👤</div>
            <div class="message-content">${text}</div>
        `;
        chatHistory.appendChild(msgDiv);
        scrollToBottom();
    }

    function createAIMessage() {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message ai';
        
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = '🤖';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Structure: Think Block (optional) + Main Content
        const thinkBlock = document.createElement('div');
        thinkBlock.className = 'think-block';
        
        const mainContent = document.createElement('div');
        mainContent.className = 'main-content';
        
        // Typing indicator
        const typing = document.createElement('div');
        typing.className = 'typing-indicator';
        typing.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
        mainContent.appendChild(typing);

        contentDiv.appendChild(thinkBlock);
        contentDiv.appendChild(mainContent);
        msgDiv.appendChild(avatar);
        msgDiv.appendChild(contentDiv);
        
        chatHistory.appendChild(msgDiv);
        scrollToBottom();
        
        return { msgDiv, thinkBlock, mainContent };
    }

    function scrollToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = messageInput.value.trim();
        if (!text) return;

        messageInput.value = '';
        messageInput.style.height = 'auto';
        
        appendUserMessage(text);
        
        const { thinkBlock, mainContent } = createAIMessage();
        
        // Connect to SSE API
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            
            let rawText = '';
            let isThinking = false;
            let thinkText = '';
            let mainText = '';
            
            // Remove typing indicator when first chunk arrives
            mainContent.innerHTML = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.slice(6);
                        if (!dataStr) continue;
                        
                        try {
                            const data = JSON.parse(dataStr);
                            if (data.done) {
                                // Update memory after chat finishes
                                setTimeout(fetchMemoryStatus, 1000);
                                continue;
                            }
                            
                            const content = data.content;
                            rawText += content;
                            
                            // Re-parse rawText completely to handle chunks splitting tags
                            let tText = '';
                            let mText = '';
                            
                            // Universal XML parsing for <response>...</response>
                            let responseStart = rawText.indexOf('<response>');
                            let responseEnd = rawText.indexOf('</response>');
                            
                            if (responseStart !== -1) {
                                let contentStart = responseStart + '<response>'.length;
                                if (responseEnd !== -1) {
                                    mText = rawText.substring(contentStart, responseEnd);
                                } else {
                                    mText = rawText.substring(contentStart);
                                }
                            } else {
                                // Fallback for models that ignore the XML prompt
                                if (rawText.includes('</think>')) {
                                    mText = rawText.split('</think>').pop();
                                } else if (rawText.includes('TRẢ LỜI:')) {
                                    mText = rawText.split('TRẢ LỜI:').pop();
                                } else if (rawText.includes('Trả lời:')) {
                                    mText = rawText.split('Trả lời:').pop();
                                } else {
                                    mText = "*(Đang suy nghĩ...)*";
                                }
                            }
                            
                            // Render (thinkBlock is hidden by CSS, so we don't need to populate it anymore)
                            if (mText) {
                                // Remove leading newlines or whitespace
                                mText = mText.trimStart();
                                // Clean up hallucinated suffix
                                if (mText.includes("User:")) {
                                    mText = mText.split("User:")[0];
                                }
                                mainContent.innerHTML = marked.parse(mText);
                            }
                            scrollToBottom();
                            
                        } catch (e) {
                            console.error("Error parsing SSE data", e);
                        }
                    }
                }
            }
        } catch (error) {
            console.error("Error connecting to chat API", error);
            mainContent.innerHTML = '<p style="color: #ef4444">Connection error. Please try again.</p>';
        }
    });

    // Memory Panel Logic
    async function fetchMemoryStatus() {
        try {
            const res = await fetch('/memory_status');
            const data = await res.json();
            
            // Update Short-term
            document.getElementById('short-term-stats').innerHTML = `
                <div class="stat-box">
                    <div class="stat-val">${data.short_term.message_count}</div>
                    <div class="stat-label">Messages</div>
                </div>
                <div class="stat-box">
                    <div class="stat-val">${data.short_term.turn_count}/${data.short_term.max_turns}</div>
                    <div class="stat-label">Turns</div>
                </div>
            `;
            
            // Update Profile
            const profileList = document.getElementById('profile-list');
            profileList.innerHTML = '';
            for (const [k, v] of Object.entries(data.long_term.profile)) {
                profileList.innerHTML += `<li><span class="kv-key">${k}</span><span class="kv-val">${v}</span></li>`;
            }
            if (!Object.keys(data.long_term.profile).length) {
                profileList.innerHTML = '<li><span class="kv-key" style="opacity: 0.5">No data yet</span></li>';
            }
            
            // Update Prefs
            const prefsList = document.getElementById('prefs-list');
            prefsList.innerHTML = '';
            for (const [k, v] of Object.entries(data.long_term.preferences)) {
                prefsList.innerHTML += `<li><span class="kv-key">${k}</span><span class="kv-val">${v}</span></li>`;
            }
            if (!Object.keys(data.long_term.preferences).length) {
                prefsList.innerHTML = '<li><span class="kv-key" style="opacity: 0.5">No data yet</span></li>';
            }
            
            // Update Stats
            const stats = data.long_term.stats;
            document.getElementById('long-term-stats').innerHTML = `
                <div class="stat-box">
                    <div class="stat-val">${stats.interactions}</div>
                    <div class="stat-label">Interactions</div>
                </div>
                <div class="stat-box">
                    <div class="stat-val">${stats.facts}</div>
                    <div class="stat-label">Saved Facts</div>
                </div>
                <div class="stat-box">
                    <div class="stat-val">${stats.issues}</div>
                    <div class="stat-label">Past Issues</div>
                </div>
                <div class="stat-box">
                    <div class="stat-val">${stats.summaries}</div>
                    <div class="stat-label">Summaries</div>
                </div>
            `;
            
        } catch (e) {
            console.error("Error fetching memory status", e);
        }
    }

    refreshMemoryBtn.addEventListener('click', () => {
        refreshMemoryBtn.style.transform = 'rotate(180deg)';
        setTimeout(() => refreshMemoryBtn.style.transform = 'none', 300);
        fetchMemoryStatus();
    });

    // Initial fetch
    fetchMemoryStatus();
});
