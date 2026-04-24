/**
 * AI Job Application Agent – Frontend JavaScript
 * Handles UI interactions, API calls, and dynamic updates.
 */

// ── Toast Notification System ───────────────────────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${message}</span>`;
    
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease reverse forwards';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

// ── Loading Overlay ─────────────────────────────────────────────────
function showLoading(message = 'Processing...') {
    const overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="spinner"></div>
        <p style="color: var(--text-secondary); font-size: 0.95rem;">${message}</p>
    `;
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.remove();
}

// ── API Helper ──────────────────────────────────────────────────────
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (data) options.body = JSON.stringify(data);

    try {
        const response = await fetch(endpoint, options);
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || `HTTP ${response.status}`);
        }
        return result;
    } catch (error) {
        showToast(error.message, 'error');
        throw error;
    }
}

// ── Resume Upload ───────────────────────────────────────────────────
function initResumeUpload() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('resume-file');
    
    if (!uploadArea || !fileInput) return;

    // Drag and drop handlers
    ['dragenter', 'dragover'].forEach(event => {
        uploadArea.addEventListener(event, (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(event => {
        uploadArea.addEventListener(event, (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
        });
    });

    uploadArea.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) uploadResume(files[0]);
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) uploadResume(e.target.files[0]);
    });
}

async function uploadResume(file) {
    const formData = new FormData();
    formData.append('resume', file);

    showLoading('Parsing your resume...');

    try {
        const response = await fetch('/api/upload-resume', {
            method: 'POST',
            body: formData,
        });
        const result = await response.json();

        if (result.error) {
            showToast(result.error, 'error');
        } else {
            showToast(`Resume uploaded! Found ${result.skills_found.length} skills.`, 'success');
            setTimeout(() => location.reload(), 1500);
        }
    } catch (error) {
        showToast('Upload failed: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ── Job Scraping ────────────────────────────────────────────────────
async function scrapeJobs() {
    const query = document.getElementById('scrape-query')?.value;
    const location = document.getElementById('scrape-location')?.value || 'India';
    
    if (!query) {
        showToast('Please enter a search query', 'error');
        return;
    }

    // Get selected sources
    const sources = [];
    document.querySelectorAll('.source-checkbox:checked').forEach(cb => {
        sources.push(cb.value);
    });

    if (sources.length === 0) {
        showToast('Select at least one source', 'error');
        return;
    }

    showLoading('Scraping job listings... This may take a minute.');

    try {
        const result = await apiCall('/api/scrape', 'POST', { query, location, sources });
        
        let message = 'Scraping complete! ';
        for (const [source, data] of Object.entries(result.results)) {
            if (data.error) {
                message += `${source}: Error. `;
            } else {
                message += `${source}: ${data.new} new jobs. `;
            }
        }
        
        showToast(message, 'success');
        setTimeout(() => location.reload(), 2000);
    } catch (error) {
        showToast('Scraping failed', 'error');
    } finally {
        hideLoading();
    }
}

// ── AI Agent Pipeline ───────────────────────────────────────────────
async function runFullPipeline() {
    const query = document.getElementById('pipeline-query')?.value;
    const location = document.getElementById('pipeline-location')?.value || 'India';
    
    if (!query) {
        showToast('Please enter a job search query', 'error');
        return;
    }

    showLoading('Running AI pipeline: Scrape → Match → Generate Cover Letters...');

    try {
        const result = await apiCall('/api/scrape-and-match', 'POST', {
            query,
            location,
            sources: ['linkedin', 'internshala']
        });

        hideLoading();
        
        if (result.success) {
            showToast('Pipeline complete! Check your applications.', 'success');
            // Show the agent's response in a modal or redirect
            setTimeout(() => window.location.href = '/applications', 2000);
        } else {
            showToast(result.output || 'Pipeline failed', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('Pipeline error', 'error');
    }
}

async function runQuickMatch() {
    showLoading('Running AI matching on unprocessed jobs...');

    try {
        const result = await apiCall('/api/quick-match', 'POST');
        hideLoading();
        
        if (result.success) {
            showToast('Matching complete!', 'success');
            setTimeout(() => window.location.href = '/applications', 2000);
        } else {
            showToast(result.output || 'Matching failed', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('Match error', 'error');
    }
}

// ── Chat Interface ──────────────────────────────────────────────────
function initChat() {
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send');
    const messagesDiv = document.getElementById('chat-messages');
    
    if (!chatInput) return;

    // Handle Enter key
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });

    sendBtn?.addEventListener('click', sendChatMessage);

    // Quick action buttons in chat
    document.querySelectorAll('.chat-quick-action').forEach(btn => {
        btn.addEventListener('click', () => {
            chatInput.value = btn.dataset.prompt;
            sendChatMessage();
        });
    });
}

async function sendChatMessage() {
    const chatInput = document.getElementById('chat-input');
    const messagesDiv = document.getElementById('chat-messages');
    const message = chatInput.value.trim();
    
    if (!message) return;

    // Add user message to chat
    appendMessage('user', message);
    chatInput.value = '';
    chatInput.disabled = true;

    // Show thinking indicator
    const thinkingId = appendThinking();

    try {
        const result = await apiCall('/api/chat', 'POST', { message });
        
        // Remove thinking indicator
        document.getElementById(thinkingId)?.remove();

        // Add AI response
        appendMessage('ai', result.output, result.steps);
    } catch (error) {
        document.getElementById(thinkingId)?.remove();
        appendMessage('ai', 'Sorry, I encountered an error. Please check your API key and try again.');
    } finally {
        chatInput.disabled = false;
        chatInput.focus();
    }
}

function appendMessage(role, text, steps = []) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;

    const avatar = role === 'ai' ? '🤖' : '👤';
    
    let stepsHtml = '';
    if (steps && steps.length > 0) {
        stepsHtml = `
            <div class="agent-steps">
                <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 6px;">
                    🔧 Agent Actions:
                </div>
                ${steps.map(s => `
                    <div class="agent-step">
                        <span class="step-tool">▸ ${s.tool}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    // Convert newlines and basic markdown
    const formatted = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>')
        .replace(/- (.*?)(?=<br>|$)/g, '• $1');

    messageDiv.innerHTML = `
        <div class="chat-avatar">${avatar}</div>
        <div class="chat-bubble">
            ${formatted}
            ${stepsHtml}
        </div>
    `;

    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function appendThinking() {
    const messagesDiv = document.getElementById('chat-messages');
    const id = 'thinking-' + Date.now();
    const div = document.createElement('div');
    div.id = id;
    div.className = 'chat-message ai';
    div.innerHTML = `
        <div class="chat-avatar">🤖</div>
        <div class="chat-bubble">
            <div class="thinking-indicator">
                <span></span><span></span><span></span>
            </div>
            <span style="font-size: 0.8rem; color: var(--text-muted);">Thinking...</span>
        </div>
    `;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return id;
}

// ── Application Status Update ───────────────────────────────────────
async function updateAppStatus(appId, newStatus) {
    try {
        await apiCall(`/api/application/${appId}/status`, 'PUT', { status: newStatus });
        showToast(`Status updated to "${newStatus}"`, 'success');
        setTimeout(() => location.reload(), 1000);
    } catch (error) {
        showToast('Failed to update status', 'error');
    }
}

// ── Cover Letter Generation ─────────────────────────────────────────
async function generateCoverLetter(jobId) {
    showLoading('Generating tailored cover letter...');
    
    try {
        const result = await apiCall(`/api/generate-cover-letter/${jobId}`, 'POST', {
            tone: 'professional'
        });
        hideLoading();
        
        if (result.success) {
            showToast('Cover letter generated!', 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showToast(result.output || 'Generation failed', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('Cover letter generation failed', 'error');
    }
}

// ── Mobile Sidebar Toggle ───────────────────────────────────────────
function toggleSidebar() {
    document.querySelector('.sidebar')?.classList.toggle('open');
}

// ── Initialize ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initResumeUpload();
    initChat();
    
    // Mobile toggle
    document.querySelector('.mobile-toggle')?.addEventListener('click', toggleSidebar);
    
    // Add stagger animation to stat cards
    document.querySelectorAll('.stats-grid').forEach(grid => {
        grid.classList.add('stagger');
    });
});
