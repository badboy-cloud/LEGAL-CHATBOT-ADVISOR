// chat.js - Manages the global independent interactive case chat page

let globalChatHistory = [];

document.addEventListener('DOMContentLoaded', () => {
    if (!window.location.pathname.includes('chat.html')) return;

    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
        chatForm.addEventListener('submit', handleGlobalChatSubmit);
    }

    // Set up suggested chips click listeners
    const chips = document.querySelectorAll('.question-chip');
    const chatInput = document.getElementById('chat-input');
    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            if (chatInput) {
                chatInput.value = chip.textContent.trim().replace(/^"|"$/g, '');
                chatInput.focus();
            }
        });
    });
});

async function handleGlobalChatSubmit(e) {
    e.preventDefault();
    const chatInput = document.getElementById('chat-input');
    if (!chatInput || !chatInput.value.trim()) return;

    const question = chatInput.value.trim();
    chatInput.value = '';

    const chatMessages = document.getElementById('chat-messages');

    // User message bubble
    const userDiv = document.createElement('div');
    userDiv.className = 'message-bubble user';
    userDiv.textContent = question;
    chatMessages.appendChild(userDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Append to local history
    globalChatHistory.push({ role: 'user', content: question });

    // Renders assistant typing indicator bubble
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message-bubble assistant';
    loadingDiv.innerHTML = `
        <div class="typing-indicator">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        </div>
    `;
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        // Standalone chat context. Since we don't have a document context loaded in this view,
        // we use a general chat context, passing empty text.
        const data = await fetchWithAuth('/api/chat-fir', {
            method: 'POST',
            body: JSON.stringify({
                text: "General Indian Penal Code (IPC) and statutory rules reference.",
                question: question,
                history: globalChatHistory
            })
        });

        // Remove loading indicator
        chatMessages.removeChild(loadingDiv);

        // Renders assistant bubble
        const aiDiv = document.createElement('div');
        aiDiv.className = 'message-bubble assistant';
        aiDiv.innerHTML = parseMarkdown(data.response);
        chatMessages.appendChild(aiDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Append to history
        globalChatHistory.push({ role: 'assistant', content: data.response });

    } catch (err) {
        chatMessages.removeChild(loadingDiv);
        const errDiv = document.createElement('div');
        errDiv.className = 'message-bubble assistant text-danger';
        errDiv.textContent = `Error: ${err.message}`;
        chatMessages.appendChild(errDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}
