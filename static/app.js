let lastId = 0;

async function loadMessages() {
    const res = await fetch("/messages");
    const data = await res.json();

    const chat = document.getElementById("chat");

    // nur neue Nachrichten anhängen
    const newMessages = data.filter(m => m.id > lastId);

    newMessages.forEach(m => {
        const div = document.createElement("div");
        div.className = "msg";

        div.innerHTML = `
            <b>${escapeHtml(m.user)}</b><br>
            ${escapeHtml(m.text)}
        `;

        chat.appendChild(div);

        lastId = Math.max(lastId, m.id);
    });

    if (newMessages.length > 0) {
        chat.scrollTop = chat.scrollHeight;
    }
}

async function sendMsg() {
    const user = document.getElementById("user").value || "anon";
    const text = document.getElementById("text").value;

    if (!text) return;

    await fetch("/send", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ user, text })
    });

    document.getElementById("text").value = "";
}

function escapeHtml(str) {
    return str.replaceAll("&", "&amp;")
              .replaceAll("<", "&lt;")
              .replaceAll(">", "&gt;");
}

// initial load + loop
loadMessages();
setInterval(loadMessages, 1500);
