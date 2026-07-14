// QuestTube AI Client Application Controller

// API Base URLs
const API_AUTH = '/api/auth/';
const API_VIDEOS = '/api/videos/';
const API_PLAYLISTS = '/api/playlists/';
const API_CHAT = '/api/chat/';
const API_RESEARCH = '/api/research/';
const API_ANALYTICS = '/api/analytics/';

// State Management
let currentUser = null;
let videosList = [];
let pollingTimer = null;
let currentConversationId = null;
let currentQuizData = null;
let currentQuizIndex = 0;
let currentQuizScore = 0;

// YouTube Player Instance
let ytPlayer = null;
let playerReady = false;

// 1. JWT API Client Helpers
function getHeaders() {
    const token = localStorage.getItem('access_token');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}

async function request(url, method = 'GET', body = null) {
    const options = {
        method,
        headers: getHeaders()
    };
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    let response = await fetch(url, options);
    
    // Handle Token Expiry and Refresh automatically
    if (response.status === 401 && localStorage.getItem('refresh_token')) {
        const refreshSuccess = await refreshToken();
        if (refreshSuccess) {
            options.headers = getHeaders();
            response = await fetch(url, options);
        } else {
            logout();
            throw new Error("Session expired. Please log in again.");
        }
    }
    
    return response;
}

async function refreshToken() {
    const refresh = localStorage.getItem('refresh_token');
    try {
        const res = await fetch(`${API_AUTH}refresh/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh })
        });
        if (res.ok) {
            const data = await res.json();
            localStorage.setItem('access_token', data.access);
            return true;
        }
    } catch (e) {
        console.error("Token refresh failed", e);
    }
    return false;
}

// 2. Authentication Logic
async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const feedback = document.getElementById('authFeedback');
    
    feedback.className = 'feedback-msg info';
    feedback.innerText = "Signing in...";

    try {
        const res = await fetch(`${API_AUTH}login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        if (res.ok) {
            const data = await res.json();
            localStorage.setItem('access_token', data.access);
            localStorage.setItem('refresh_token', data.refresh);
            feedback.className = 'feedback-msg success';
            feedback.innerText = "Success! Loading workspace...";
            setTimeout(initApp, 1000);
        } else {
            const data = await res.json();
            feedback.className = 'feedback-msg error';
            feedback.innerText = data.detail || "Invalid username or password.";
        }
    } catch (err) {
        feedback.className = 'feedback-msg error';
        feedback.innerText = "Connection error.";
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('registerUsername').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    const feedback = document.getElementById('authFeedback');
    
    feedback.className = 'feedback-msg info';
    feedback.innerText = "Registering...";

    try {
        const res = await fetch(`${API_AUTH}register/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });
        if (res.ok) {
            feedback.className = 'feedback-msg success';
            feedback.innerText = "Account created! Logging in...";
            
            // Auto login after register
            const loginRes = await fetch(`${API_AUTH}login/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            if (loginRes.ok) {
                const loginData = await loginRes.json();
                localStorage.setItem('access_token', loginData.access);
                localStorage.setItem('refresh_token', loginData.refresh);
                setTimeout(initApp, 1000);
            } else {
                showAuthForm('login');
            }
        } else {
            const data = await res.json();
            feedback.className = 'feedback-msg error';
            feedback.innerText = Object.values(data).join(" ") || "Registration failed.";
        }
    } catch (err) {
        feedback.className = 'feedback-msg error';
        feedback.innerText = "Connection error.";
    }
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    currentUser = null;
    document.getElementById('appLayout').style.display = 'none';
    document.getElementById('authOverlay').style.display = 'flex';
    if (pollingTimer) clearInterval(pollingTimer);
    showAuthForm('login');
}

function showAuthForm(type) {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const subtitle = document.getElementById('authSubtitle');
    document.getElementById('authFeedback').innerText = "";

    if (type === 'login') {
        loginForm.classList.add('active');
        registerForm.classList.remove('active');
        subtitle.innerText = "Login to access your RAG Research Workspace";
    } else {
        registerForm.classList.add('active');
        loginForm.classList.remove('active');
        subtitle.innerText = "Create an account to start analyzing YouTube videos";
    }
}

// 3. App Initialization
async function initApp() {
    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) {
        logout();
        return;
    }
    
    try {
        const res = await request(`${API_AUTH}profile/`);
        if (res.ok) {
            currentUser = await res.json();
            document.getElementById('usernameDisplay').innerText = currentUser.username;
            document.getElementById('userAvatar').innerText = currentUser.username[0];
            
            // Render limit bar
            const limit = currentUser.profile.usage_limit;
            const used = currentUser.profile.tokens_used;
            document.getElementById('totalVideosCount').innerText = "0"; // Will update on video fetch
            document.getElementById('tokensUsedCount').innerText = used.toLocaleString();
            
            const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
            document.getElementById('tokenLimitPercentage').innerText = `${pct}%`;
            document.getElementById('tokenProgressBar').style.width = `${pct}%`;

            // Hide auth show workspace
            document.getElementById('authOverlay').style.display = 'none';
            document.getElementById('appLayout').style.display = 'flex';
            
            // Load dashboard
            switchPanel('dashboard');
        } else {
            logout();
        }
    } catch (e) {
        logout();
    }
}

// 4. Panel Swapping & Navigation
function switchPanel(panelName) {
    // Highlight sidebar items
    document.querySelectorAll('.menu-item').forEach(item => {
        if (item.getAttribute('data-target') === panelName) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // Toggle panels
    document.querySelectorAll('.page-panel').forEach(panel => {
        if (panel.id === `panel-${panelName}`) {
            panel.classList.add('active');
        } else {
            panel.classList.remove('active');
        }
    });

    // Page title
    const titles = {
        'dashboard': 'Dashboard',
        'chat': 'AI Chat (RAG)',
        'research': 'Research Lab',
        'learning': 'Learning Hub',
        'analytics': 'Usage & Analytics'
    };
    document.getElementById('pageTitle').innerText = titles[panelName] || 'QuestTube';

    // Page-specific trigger actions
    if (panelName === 'dashboard') {
        loadVideosDatabase();
    } else if (panelName === 'chat') {
        loadChatVideosList();
    } else if (panelName === 'research') {
        loadResearchVideosList();
    } else if (panelName === 'learning') {
        loadLearningVideoOptions();
    } else if (panelName === 'analytics') {
        loadAnalyticsData();
    }
}

// 5. Videos Database Management (Dashboard)
async function loadVideosDatabase() {
    const feedback = document.getElementById('dashboardFeedback');
    try {
        const res = await request(API_VIDEOS);
        if (res.ok) {
            videosList = await res.json();
            renderVideosTable(videosList);
            document.getElementById('totalVideosCount').innerText = videosList.length;
            document.getElementById('videoDatabaseCount').innerText = `${videosList.length} videos`;
            
            // Check if we need to set up background status polling
            const needsPolling = videosList.some(v => v.status === 'pending' || v.status === 'processing');
            if (needsPolling && !pollingTimer) {
                startStatusPolling();
            } else if (!needsPolling && pollingTimer) {
                stopStatusPolling();
            }
        }
    } catch (e) {
        console.error("Failed to load videos list", e);
    }
}

function renderVideosTable(videos) {
    const tbody = document.getElementById('videoTableBody');
    if (videos.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="table-empty">No videos found. Submit a URL above to start!</td></tr>`;
        return;
    }

    tbody.innerHTML = videos.map(video => {
        let statusBadge = '';
        if (video.status === 'completed') {
            statusBadge = `<span class="badge status-completed">Completed</span>`;
        } else if (video.status === 'processing') {
            statusBadge = `<span class="badge status-processing">Processing...</span>`;
        } else if (video.status === 'failed') {
            statusBadge = `<span class="badge status-failed">Failed</span>`;
        } else {
            statusBadge = `<span class="badge status-pending">Pending</span>`;
        }

        const date = new Date(video.created_at).toLocaleDateString(undefined, {
            month: 'short', day: 'numeric', year: 'numeric'
        });

        return `
            <tr>
                <td>
                    <div class="video-db-title">${escapeHTML(video.title)}</div>
                    <div class="video-db-url">${escapeHTML(video.url)}</div>
                </td>
                <td>${escapeHTML(video.channel_name || 'YouTube')}</td>
                <td>${statusBadge}</td>
                <td>${date}</td>
                <td>
                    <button class="action-btn-danger" onclick="deleteVideo(${video.id})">Delete</button>
                </td>
            </tr>
        `;
    }).join('');
}

async function addSingleVideo(e) {
    e.preventDefault();
    const urlInput = document.getElementById('videoUrl');
    const feedback = document.getElementById('dashboardFeedback');
    
    feedback.className = "feedback-msg info";
    feedback.innerText = "Submitting YouTube video...";

    try {
        const res = await request(API_VIDEOS, 'POST', { url: urlInput.value });
        if (res.ok) {
            feedback.className = "feedback-msg success";
            feedback.innerText = "Video successfully added! Fetching transcript in background...";
            urlInput.value = "";
            loadVideosDatabase();
        } else {
            const data = await res.json();
            feedback.className = "feedback-msg error";
            feedback.innerText = data.error || "Failed to add video.";
        }
    } catch (e) {
        feedback.className = "feedback-msg error";
        feedback.innerText = e.message;
    }
}

async function importPlaylist(e) {
    e.preventDefault();
    const urlInput = document.getElementById('playlistUrl');
    const feedback = document.getElementById('dashboardFeedback');
    
    feedback.className = "feedback-msg info";
    feedback.innerText = "Importing playlist video links...";

    try {
        const res = await request(API_PLAYLISTS + 'import/', 'POST', { playlist_url: urlInput.value });
        if (res.ok) {
            feedback.className = "feedback-msg success";
            feedback.innerText = "Playlist successfully imported! Processing multiple videos in background...";
            urlInput.value = "";
            loadVideosDatabase();
        } else {
            const data = await res.json();
            feedback.className = "feedback-msg error";
            feedback.innerText = data.error || "Failed to import playlist.";
        }
    } catch (e) {
        feedback.className = "feedback-msg error";
        feedback.innerText = e.message;
    }
}

async function deleteVideo(id) {
    if (!confirm("Are you sure you want to delete this video? This deletes all associated transcripts, chunks, and embeddings.")) {
        return;
    }
    try {
        const res = await request(`${API_VIDEOS}${id}/`, 'DELETE');
        if (res.ok) {
            loadVideosDatabase();
        }
    } catch (e) {
        console.error("Delete failed", e);
    }
}

function startStatusPolling() {
    pollingTimer = setInterval(async () => {
        try {
            const res = await request(API_VIDEOS);
            if (res.ok) {
                const videos = await res.json();
                videosList = videos;
                renderVideosTable(videosList);
                const stillProcessing = videos.some(v => v.status === 'pending' || v.status === 'processing');
                if (!stillProcessing) {
                    stopStatusPolling();
                    // Update header limit summary too
                    initApp();
                }
            }
        } catch (e) {
            console.error("Polling error", e);
        }
    }, 3000);
}

function stopStatusPolling() {
    if (pollingTimer) {
        clearInterval(pollingTimer);
        pollingTimer = null;
    }
}

// 6. RAG Chat Hub
async function loadChatVideosList() {
    const list = document.getElementById('chatVideosChecklist');
    try {
        const res = await request(API_VIDEOS);
        if (res.ok) {
            const videos = await res.json();
            const completed = videos.filter(v => v.status === 'completed');
            if (completed.length === 0) {
                list.innerHTML = `<p class="list-empty">No completed videos. Process some in the Dashboard first!</p>`;
                return;
            }
            list.innerHTML = completed.map(v => `
                <label class="checkbox-wrapper">
                    <input type="checkbox" name="chat_video" value="${v.id}" checked>
                    <div class="checkbox-label">
                        <span class="checkbox-title">${escapeHTML(v.title)}</span>
                        <span class="checkbox-meta">${escapeHTML(v.channel_name)}</span>
                    </div>
                </label>
            `).join('');
        }
    } catch (e) {
        console.error("Failed to load select checklist", e);
    }
}

async function handleChatSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text) return;

    // Get checked video IDs
    const checked = Array.from(document.querySelectorAll('input[name="chat_video"]:checked')).map(cb => parseInt(cb.value));
    if (checked.length === 0) {
        alert("Please select at least one reference video in the left pane.");
        return;
    }

    // Render User message bubble
    appendMessage("user", text);
    input.value = "";

    // Render placeholder loader bubble for Assistant
    const loaderId = appendMessage("assistant", "AI is conducting semantic vector search & synthesizing context...");

    try {
        const res = await request(API_CHAT, 'POST', {
            question: text,
            video_ids: checked,
            conversation_id: currentConversationId
        });
        
        if (res.ok) {
            const data = await res.json();
            currentConversationId = data.conversation_id;
            
            // Format answer text to support Markdown & Timestamp Citations
            const formatted = formatMarkdown(data.answer, data.sources);
            
            // Replace loader bubble with final response
            updateMessage(loaderId, formatted, data.sources);
        } else {
            const data = await res.json();
            updateMessage(loaderId, `<span style="color:var(--accent-red)">Error: ${data.error || "RAG engine timeout."}</span>`);
        }
    } catch (err) {
        updateMessage(loaderId, `<span style="color:var(--accent-red)">Error: ${err.message}</span>`);
    }
}

function appendMessage(role, text) {
    const body = document.getElementById('chatBody');
    const msgId = 'msg-' + Date.now();
    
    // Hide welcome card if present
    const welcome = body.querySelector('.assistant-welcome');
    if (welcome) welcome.style.display = 'none';

    const msg = document.createElement('div');
    msg.className = `chat-msg ${role}`;
    msg.id = msgId;
    
    msg.innerHTML = `
        <div class="msg-header">${role === 'user' ? 'You' : 'QuestTube AI'}</div>
        <div class="msg-bubble">${escapeHTML(text)}</div>
    `;
    
    body.appendChild(msg);
    body.scrollTop = body.scrollHeight;
    return msgId;
}

function updateMessage(id, formattedHtml, sources = null) {
    const msg = document.getElementById(id);
    if (!msg) return;
    
    const bubble = msg.querySelector('.msg-bubble');
    bubble.innerHTML = formattedHtml;
    
    if (sources && sources.length > 0) {
        const sourcesBlock = document.createElement('div');
        sourcesBlock.className = 'sources-pane';
        sourcesBlock.innerHTML = `
            <div class="sources-title">Verified Sources</div>
            <div class="sources-list">
                ${sources.map(src => `
                    <button class="citation-tag" onclick="seekVideo('${escapeHTML(getYouTubeIdFromTitle(src.title, src.video_id))}', ${src.timestamp})">
                        ${escapeHTML(src.title)} - ${src.timestamp_formatted}
                    </button>
                `).join('')}
            </div>
        `;
        bubble.appendChild(sourcesBlock);
    }
    
    const body = document.getElementById('chatBody');
    body.scrollTop = body.scrollHeight;
}

// 7. Seeking Video Player (Iframe Embed)
function seekVideo(youtubeId, seconds) {
    // Show player panel
    document.getElementById('videoPreviewPane').style.display = 'flex';
    document.getElementById('previewTimestampInfo').innerText = `Playing from timestamp: ${seconds} seconds.`;

    if (!ytPlayer) {
        // Create YouTube Player iframe API element
        ytPlayer = new YT.Player('youtubePlayerPlaceholder', {
            height: '100%',
            width: '100%',
            videoId: youtubeId,
            playerVars: {
                'playsinline': 1,
                'autoplay': 1,
                'start': seconds
            },
            events: {
                'onReady': () => { playerReady = true; }
            }
        });
    } else {
        // Load the new video and seek
        ytPlayer.cueVideoById({
            videoId: youtubeId,
            startSeconds: seconds
        });
        setTimeout(() => {
            ytPlayer.playVideo();
        }, 500);
    }
}

// Helper to look up YouTube Video ID from title/ID
function getYouTubeIdFromTitle(title, videoId) {
    const match = videosList.find(v => v.id === videoId || v.title === title);
    return match ? match.youtube_id : '';
}

// 8. Research Lab
async function loadResearchVideosList() {
    const list = document.getElementById('researchVideosChecklist');
    try {
        const res = await request(API_VIDEOS);
        if (res.ok) {
            const videos = await res.json();
            const completed = videos.filter(v => v.status === 'completed');
            if (completed.length === 0) {
                list.innerHTML = `<p class="list-empty">No completed videos found.</p>`;
                return;
            }
            list.innerHTML = completed.map(v => `
                <label class="checkbox-wrapper">
                    <input type="checkbox" name="research_video" value="${v.id}" checked>
                    <div class="checkbox-label">
                        <span class="checkbox-title">${escapeHTML(v.title)}</span>
                    </div>
                </label>
            `).join('');
        }
    } catch (e) {
        console.error(e);
    }
}

async function runResearch(type) {
    const checked = Array.from(document.querySelectorAll('input[name="research_video"]:checked')).map(cb => parseInt(cb.value));
    const topic = document.getElementById('researchTopic').value.trim();
    const outputArea = document.getElementById('researchOutputArea');
    const subtitle = document.getElementById('researchOutputSubtitle');

    if (checked.length === 0) {
        alert("Please select reference videos.");
        return;
    }
    if ((type === 'compare' || type === 'report') && !topic) {
        alert("Please define a research topic/concept.");
        return;
    }

    outputArea.innerHTML = `
        <div class="empty-output-state">
            <svg viewBox="0 0 24 24" width="48" height="48" class="empty-icon"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
            <p>AI is processing RAG pipelines across selected transcripts... Please wait (10-15s).</p>
        </div>
    `;

    try {
        let res;
        if (type === 'compare') {
            subtitle.innerText = `Side-by-Side Video Comparison on '${topic}'`;
            res = await request(`${API_RESEARCH}compare/`, 'POST', { video_ids: checked, topic });
        } else if (type === 'contradictions') {
            subtitle.innerText = "Contradiction & Conflict Detection Analysis";
            res = await request(`${API_RESEARCH}contradictions/`, 'POST', { video_ids: checked });
        } else {
            subtitle.innerText = `Synthesizing Markdown Research Report: '${topic}'`;
            res = await request(`${API_RESEARCH}report/`, 'POST', { video_ids: checked, topic });
        }

        if (res.ok) {
            const data = await res.json();
            const content = data.comparison || data.analysis || data.report;
            outputArea.innerHTML = formatMarkdown(content);
        } else {
            const data = await res.json();
            outputArea.innerHTML = `<p style="color:var(--accent-red)">Failed: ${data.error}</p>`;
        }
    } catch (e) {
        outputArea.innerHTML = `<p style="color:var(--accent-red)">Connection error: ${e.message}</p>`;
    }
}

// 9. Learning Hub Panel
async function loadLearningVideoOptions() {
    const select = document.getElementById('learningVideoSelect');
    try {
        const res = await request(API_VIDEOS);
        if (res.ok) {
            const videos = await res.json();
            const completed = videos.filter(v => v.status === 'completed');
            
            // Save options
            select.innerHTML = `<option value="">-- Choose a Video --</option>` + 
                completed.map(v => `<option value="${v.id}">${escapeHTML(v.title)}</option>`).join('');
        }
    } catch (e) {
        console.error(e);
    }
}

async function loadSummary() {
    const select = document.getElementById('learningVideoSelect');
    const vidId = select.value;
    const output = document.getElementById('summaryOutput');
    const activeChip = document.querySelector('.summary-controls .chip-btn.active');
    const type = activeChip ? activeChip.getAttribute('data-summary-type') : 'detailed';

    if (!vidId) {
        output.innerHTML = `<p class="select-video-prompt">Please select a video from the drop-down menu above.</p>`;
        return;
    }

    output.innerHTML = `<p class="select-video-prompt">Generating ${type} summary... Please wait.</p>`;

    try {
        const res = await request(`${API_VIDEOS}${vidId}/summary/`, 'POST', { summary_type: type });
        if (res.ok) {
            const data = await res.json();
            output.innerHTML = formatMarkdown(data.summary);
        } else {
            const data = await res.json();
            output.innerHTML = `<p style="color:var(--accent-red)">Error: ${data.error}</p>`;
        }
    } catch (e) {
        output.innerHTML = `<p style="color:var(--accent-red)">Error: ${e.message}</p>`;
    }
}

async function generateQuiz() {
    const select = document.getElementById('learningVideoSelect');
    const vidId = select.value;
    const output = document.getElementById('quizOutput');
    const activeChip = document.querySelector('.quiz-controls .chip-btn.active');
    const diff = activeChip ? activeChip.getAttribute('data-quiz-diff') : 'intermediate';

    if (!vidId) {
        alert("Please select a video.");
        return;
    }

    output.innerHTML = `<p class="select-video-prompt">Creating MCQ quiz from video transcript... Please wait.</p>`;

    try {
        const res = await request(`${API_VIDEOS}${vidId}/quiz/`, 'POST', { difficulty: diff, questions: 5 });
        if (res.ok) {
            currentQuizData = await res.json();
            currentQuizIndex = 0;
            currentQuizScore = 0;
            renderQuizQuestion();
        } else {
            const data = await res.json();
            output.innerHTML = `<p style="color:var(--accent-red)">Error: ${data.error || "Failed to generate quiz JSON."}</p>`;
        }
    } catch (e) {
        output.innerHTML = `<p style="color:var(--accent-red)">Error: ${e.message}</p>`;
    }
}

function renderQuizQuestion() {
    const output = document.getElementById('quizOutput');
    if (!currentQuizData || currentQuizData.length === 0) {
        output.innerHTML = `<p class="select-video-prompt">Quiz could not be rendered.</p>`;
        return;
    }

    if (currentQuizIndex >= currentQuizData.length) {
        // Show final score card
        output.innerHTML = `
            <div class="quiz-results-card glass-card">
                <h2>Quiz Complete!</h2>
                <div class="quiz-score-val">${currentQuizScore} / ${currentQuizData.length}</div>
                <p>Great job! You achieved a score of ${Math.round((currentQuizScore/currentQuizData.length)*100)}% on this video content quiz.</p>
                <button class="btn btn-primary" onclick="generateQuiz()">Try Again</button>
            </div>
        `;
        return;
    }

    const q = currentQuizData[currentQuizIndex];
    output.innerHTML = `
        <div class="quiz-game">
            <div class="quiz-progress">
                <span>Question ${currentQuizIndex + 1} of ${currentQuizData.length}</span>
                <span>Score: ${currentQuizScore}</span>
            </div>
            <div class="quiz-question-card">${escapeHTML(q.question)}</div>
            <div class="quiz-options-list">
                ${q.options.map(opt => {
                    // Extract letter
                    const letter = opt.substring(0, 1).toUpperCase();
                    return `
                        <button class="quiz-opt-btn" onclick="submitQuizAnswer(this, '${letter}', '${q.answer}')">
                            ${escapeHTML(opt)}
                        </button>
                    `;
                }).join('')}
            </div>
            <div id="quizNextBtnContainer" style="display:none; text-align:right; margin-top:1rem;">
                <button class="btn btn-secondary" onclick="nextQuizQuestion()">Next Question →</button>
            </div>
        </div>
    `;
}

function submitQuizAnswer(button, chosenLetter, correctLetter) {
    const list = button.parentElement;
    const buttons = list.querySelectorAll('.quiz-opt-btn');
    
    // Disable all options
    buttons.forEach(btn => btn.disabled = true);
    
    if (chosenLetter === correctLetter) {
        button.classList.add('correct');
        currentQuizScore++;
    } else {
        button.classList.add('incorrect');
        // Highlight correct option
        buttons.forEach(btn => {
            if (btn.innerText.startsWith(correctLetter)) {
                btn.classList.add('correct');
            }
        });
    }

    document.getElementById('quizNextBtnContainer').style.display = 'block';
}

function nextQuizQuestion() {
    currentQuizIndex++;
    renderQuizQuestion();
}

async function generateFlashcards() {
    const select = document.getElementById('learningVideoSelect');
    const vidId = select.value;
    const output = document.getElementById('flashcardsOutput');

    if (!vidId) {
        alert("Please select a video.");
        return;
    }

    output.innerHTML = `<p class="select-video-prompt">Creating flashcards... Please wait.</p>`;

    try {
        const res = await request(`${API_VIDEOS}${vidId}/flashcards/`, 'POST');
        if (res.ok) {
            const flashcards = await res.json();
            if (flashcards.length === 0) {
                output.innerHTML = `<p class="select-video-prompt">No flashcards were generated.</p>`;
                return;
            }
            output.innerHTML = `
                <div class="flashcards-grid">
                    ${flashcards.map(fc => `
                        <div class="flashcard-perspective" onclick="this.querySelector('.flashcard-inner').classList.toggle('flipped')">
                            <div class="flashcard-inner">
                                <div class="flashcard-front">
                                    ${escapeHTML(fc.front)}
                                </div>
                                <div class="flashcard-back">
                                    ${escapeHTML(fc.back)}
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } else {
            const data = await res.json();
            output.innerHTML = `<p style="color:var(--accent-red)">Error: ${data.error}</p>`;
        }
    } catch (e) {
        output.innerHTML = `<p style="color:var(--accent-red)">Error: ${e.message}</p>`;
    }
}

async function generateNotes() {
    const select = document.getElementById('learningVideoSelect');
    const vidId = select.value;
    const output = document.getElementById('notesOutput');

    if (!vidId) {
        alert("Please select a video.");
        return;
    }

    output.innerHTML = `<p class="select-video-prompt">Creating detailed study guide notes... Please wait.</p>`;

    try {
        const res = await request(`${API_VIDEOS}${vidId}/notes/`, 'POST');
        if (res.ok) {
            const data = await res.json();
            output.innerHTML = formatMarkdown(data.notes);
        } else {
            const data = await res.json();
            output.innerHTML = `<p style="color:var(--accent-red)">Error: ${data.error}</p>`;
        }
    } catch (e) {
        output.innerHTML = `<p style="color:var(--accent-red)">Error: ${e.message}</p>`;
    }
}

// 10. Analytics Dashboard Renders (SVG graphs)
async function loadAnalyticsData() {
    try {
        const res = await request(API_ANALYTICS + 'summary/');
        if (res.ok) {
            const data = await res.json();
            
            // Set summary numbers
            document.getElementById('analyticsApiCalls').innerText = data.total_calls.toLocaleString();
            document.getElementById('analyticsTotalTokens').innerText = data.total_tokens_used.toLocaleString();
            
            // Estimate cost: gemini embedding is cheap ($0.025 / 1M tokens), gemini flash is ($0.075 / 1M input)
            // We just do a mock cost allocation based on tokens
            const cost = (data.total_tokens_used * 0.00000015).toFixed(4);
            document.getElementById('analyticsEstCost').innerText = `$${cost}`;

            // Render SVG dynamic graph of provider usage
            renderUsageChart(data.provider_breakdown);
            
            // Query history summaries
            loadQueryLogsList();
        }
    } catch (e) {
        console.error(e);
    }
}

function renderUsageChart(breakdown) {
    const chartArea = document.getElementById('analyticsChartArea');
    if (!breakdown || breakdown.length === 0) {
        chartArea.innerHTML = `<div class="chart-empty">No usage logs available yet. Ask RAG questions to populate.</div>`;
        return;
    }

    // Build bar chart
    const maxVal = Math.max(...breakdown.map(b => b.total_tokens));
    const chartHeight = 180;
    const chartWidth = 350;
    const padLeft = 80;
    const padBottom = 30;

    let svgContent = `
        <svg viewBox="0 0 ${chartWidth} ${chartHeight}" style="width:100%; height:100%;">
            <!-- Grid Lines -->
            <line x1="${padLeft}" y1="20" x2="${chartWidth - 20}" y2="20" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            <line x1="${padLeft}" y1="${(chartHeight-padBottom)/2}" x2="${chartWidth-20}" y2="${(chartHeight-padBottom)/2}" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            <line x1="${padLeft}" y1="${chartHeight-padBottom}" x2="${chartWidth-20}" y2="${chartHeight-padBottom}" stroke="rgba(255,255,255,0.2)" stroke-width="1.5"/>
    `;

    const barWidth = 35;
    const barSpacing = 40;
    
    breakdown.forEach((b, i) => {
        const x = padLeft + (i * (barWidth + barSpacing)) + 20;
        const valPct = maxVal > 0 ? (b.total_tokens / maxVal) : 0;
        const barHeight = valPct * (chartHeight - padBottom - 30);
        const y = chartHeight - padBottom - barHeight;

        // Draw bar
        svgContent += `
            <rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="4" fill="url(#purpleGrad)" />
            <!-- Label -->
            <text x="${x + barWidth/2}" y="${chartHeight - 10}" fill="var(--text-secondary)" font-size="10" text-anchor="middle">
                ${b.provider.toUpperCase()}
            </text>
            <!-- Token value inside/above bar -->
            <text x="${x + barWidth/2}" y="${y - 8}" fill="white" font-size="9" font-weight="600" text-anchor="middle">
                ${b.total_tokens.toLocaleString()}
            </text>
        `;
    });

    // Gradients defs
    svgContent += `
            <defs>
                <linearGradient id="purpleGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stop-color="#8f00ff" />
                    <stop offset="100%" stop-color="#ff007f" />
                </linearGradient>
            </defs>
        </svg>
    `;

    chartArea.innerHTML = svgContent;
}

async function loadQueryLogsList() {
    const list = document.getElementById('analyticsQueryList');
    try {
        const res = await request(API_CHAT + 'conversations/');
        if (res.ok) {
            const convs = await res.json();
            if (convs.length === 0) {
                list.innerHTML = `<p class="list-empty">No recent RAG query logs.</p>`;
                return;
            }
            list.innerHTML = convs.slice(0, 4).map(c => {
                const date = new Date(c.created_at).toLocaleTimeString(undefined, {
                    hour: '2-digit', minute: '2-digit'
                }) + ' ' + new Date(c.created_at).toLocaleDateString();
                return `
                    <div class="query-log-item">
                        <div class="query-log-text">${escapeHTML(c.title)}</div>
                        <div class="query-log-meta">
                            <span>ID: #${c.id}</span>
                            <span>${date}</span>
                        </div>
                    </div>
                `;
            }).join('');
        }
    } catch (e) {
        console.error(e);
    }
}

// 11. Custom Markdown & Citations formatter
function formatMarkdown(text, sources = null) {
    if (!text) return "";
    
    // Safely escape HTML first to prevent XSS
    let escaped = escapeHTML(text);

    // 1. Process Citations
    // We match references like: [Video Title - MM:SS] or [Video Title - HH:MM:SS]
    // Or citations like: [1] or [Video Title - 10:20]
    // Let's rewrite them into seek buttons
    escaped = escaped.replace(/\[([^\]]+?)\s*-\s*([0-9:]+)\]/g, (match, title, timestamp) => {
        const seconds = parseTimestampToSeconds(timestamp);
        const youtubeId = getYouTubeIdFromTitle(title.trim());
        if (youtubeId) {
            return `<a class="citation-tag" onclick="seekVideo('${escapeHTML(youtubeId)}', ${seconds})">${escapeHTML(title)} - ${timestamp}</a>`;
        }
        return match;
    });

    // 2. Headings
    escaped = escaped.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    escaped = escaped.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    escaped = escaped.replace(/^# (.*?)$/gm, '<h1>$1</h1>');

    // 3. Bold & Italic
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // 4. Bullet lists
    escaped = escaped.replace(/^\s*-\s*(.*?)$/gm, '<li>$1</li>');
    escaped = escaped.replace(/^\s*\*\s*(.*?)$/gm, '<li>$1</li>');

    // 5. Line breaks
    escaped = escaped.replace(/\n/g, '<br>');

    return `<div class="markdown-body">${escaped}</div>`;
}

function parseTimestampToSeconds(timeStr) {
    const parts = timeStr.split(':').map(Number);
    if (parts.length === 3) {
        return (parts[0] * 3600) + (parts[1] * 60) + parts[2];
    } else if (parts.length === 2) {
        return (parts[0] * 60) + parts[1];
    }
    return parseFloat(timeStr) || 0;
}

// Escapes special HTML characters
function escapeHTML(str) {
    if (!str) return "";
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// 12. Register Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Auth Forms swap
    document.getElementById('toggleToRegister').addEventListener('click', (e) => {
        e.preventDefault();
        showAuthForm('register');
    });
    document.getElementById('toggleToLogin').addEventListener('click', (e) => {
        e.preventDefault();
        showAuthForm('login');
    });

    // Forms Submit
    // Dashboard Tab switching (Single Video vs Playlist Import)
    document.querySelectorAll('.tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tabs .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const targetTab = btn.getAttribute('data-tab');
            document.querySelectorAll('#panel-dashboard .tab-content').forEach(content => {
                if (content.id === `tab-${targetTab}`) {
                    content.classList.add('active');
                } else {
                    content.classList.remove('active');
                }
            });
        });
    });

    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('registerForm').addEventListener('submit', handleRegister);
    document.getElementById('addVideoForm').addEventListener('submit', addSingleVideo);
    document.getElementById('importPlaylistForm').addEventListener('submit', importPlaylist);
    document.getElementById('chatForm').addEventListener('submit', handleChatSubmit);

    // Logout
    document.getElementById('logoutBtn').addEventListener('click', logout);

    // Sidebar menu clicks
    document.querySelectorAll('.menu-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const target = item.getAttribute('data-target');
            switchPanel(target);
        });
    });

    // Refresh btn
    document.getElementById('refreshBtn').addEventListener('click', () => {
        const activeItem = document.querySelector('.menu-item.active');
        if (activeItem) {
            const target = activeItem.getAttribute('data-target');
            switchPanel(target);
        }
    });

    // Research Buttons
    document.getElementById('btnCompare').addEventListener('click', () => runResearch('compare'));
    document.getElementById('btnContradictions').addEventListener('click', () => runResearch('contradictions'));
    document.getElementById('btnReport').addEventListener('click', () => runResearch('report'));

    // Learning Tab selection
    document.querySelectorAll('.learning-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.learning-tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const targetTab = btn.getAttribute('data-tab');
            document.querySelectorAll('.learning-content-tab').forEach(tab => {
                if (tab.id === `learn-${targetTab}`) {
                    tab.classList.add('active');
                } else {
                    tab.classList.remove('active');
                }
            });

            // Trigger fetch
            if (targetTab === 'summary') loadSummary();
        });
    });

    // Summary sub-chips
    document.querySelectorAll('.summary-controls .chip-btn').forEach(chip => {
        chip.addEventListener('click', () => {
            document.querySelectorAll('.summary-controls .chip-btn').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            loadSummary();
        });
    });

    // Quiz difficulty chips
    document.querySelectorAll('.quiz-controls .chip-btn').forEach(chip => {
        chip.addEventListener('click', () => {
            document.querySelectorAll('.quiz-controls .chip-btn').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
        });
    });

    // Learning trigger buttons
    document.getElementById('btnGenerateQuiz').addEventListener('click', generateQuiz);
    document.getElementById('btnGenerateFlashcards').addEventListener('click', generateFlashcards);
    document.getElementById('btnGenerateNotes').addEventListener('click', generateNotes);
    
    // Auto load when video select changes
    document.getElementById('learningVideoSelect').addEventListener('change', () => {
        const activeTab = document.querySelector('.learning-tab-btn.active').getAttribute('data-tab');
        if (activeTab === 'summary') loadSummary();
        else if (activeTab === 'quiz') {
            document.getElementById('quizOutput').innerHTML = `<p class="select-video-prompt">Click "Generate Quiz" to load multiple-choice study questions.</p>`;
        } else if (activeTab === 'flashcards') {
            document.getElementById('flashcardsOutput').innerHTML = `<p class="select-video-prompt">Select a video and click "Generate Flashcards".</p>`;
        } else if (activeTab === 'notes') {
            document.getElementById('notesOutput').innerHTML = `<p class="select-video-prompt">Select a video and click "Create Study Guide".</p>`;
        }
    });

    // Run auth check
    initApp();
});
