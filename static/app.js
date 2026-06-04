const socket = io();

const chat = document.getElementById("chat");
const textInput = document.getElementById("text");
const onlinePanel = document.getElementById("onlinePanel");
const onlineUsers = document.getElementById("onlineUsers");
const adminPanel = document.getElementById("adminPanel");
const adminUsers = document.getElementById("adminUsers");
const adminChannels = document.getElementById("adminChannels");
const adminLogs = document.getElementById("adminLogs");
const roomTitle = document.getElementById("roomTitle");
const channelList = document.getElementById("channelList");
const newChannelName = document.getElementById("newChannelName");
const newChannelAdminOnly = document.getElementById("newChannelAdminOnly");
const motdBox = document.getElementById("motdBox");
const motdText = document.getElementById("motdText");
const dailyMessage = document.getElementById("dailyMessage");

let currentChannel = window.START_CHANNEL || "allgemein";

async function loadMotd() {
    if (!motdBox || !motdText) return;

    if (currentChannel !== "allgemein") {
        motdBox.classList.add("hidden");
        return;
    }

    const res = await fetch("/motd");
    if (!res.ok) return;

    const data = await res.json();
    const text = data.text || "";

    if (!text.trim()) {
        motdBox.classList.add("hidden");
        return;
    }

    motdText.textContent = text;
    motdBox.classList.remove("hidden");

    if (dailyMessage) {
        dailyMessage.value = text;
    }
}

async function saveMotd() {
    if (!window.IS_ADMIN || !dailyMessage) return;

    const text = dailyMessage.value.trim();

    const res = await fetch("/admin/motd", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ text })
    });

    if (!res.ok) {
        alert("Nachricht des Tages konnte nicht gespeichert werden");
        return;
    }

    loadMotd();
}

async function loadChannels() {
    const res = await fetch("/channels");

    if (!res.ok) return;

    const channels = await res.json();

    channelList.innerHTML = "";

    if (!channels.some(c => c.name === currentChannel)) {
        currentChannel = channels.length ? channels[0].name : "allgemein";
    }

    channels.forEach(channel => {
        const btn = document.createElement("button");
        btn.className = "channel-btn";
        btn.dataset.channel = channel.name;
        btn.textContent = "# " + channel.name + (channel.admin_only ? " 🔒" : "");
        btn.onclick = () => switchChannel(channel.name);
        btn.classList.toggle("active", channel.name === currentChannel);
        channelList.appendChild(btn);
    });

    roomTitle.textContent = "# " + currentChannel;
    loadMotd();
    loadMessages();
}

async function loadAdminChannels() {
    if (!window.IS_ADMIN || !adminChannels) return;

    const res = await fetch("/admin/channels");

    if (!res.ok) return;

    const channels = await res.json();

    adminChannels.innerHTML = "";

    channels.forEach(channel => {
        const div = document.createElement("div");
        div.className = "admin-user";

        div.innerHTML = `
            <div>
                <b># ${escapeHtml(channel.name)}</b>
                <span>${channel.admin_only ? "ADMIN-RAUM" : "ÖFFENTLICH"}${channel.protected ? " · GESCHÜTZT" : ""}</span>
            </div>
            ${!channel.protected ? `<button onclick="deleteChannel('${escapeHtml(channel.name)}')">löschen</button>` : ""}
        `;

        adminChannels.appendChild(div);
    });
}

function switchChannel(channel) {
    currentChannel = channel;
    roomTitle.textContent = "# " + channel;

    document.querySelectorAll(".channel-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.channel === channel);
    });

    loadMotd();
    loadMessages();
}

async function loadMessages() {
    const res = await fetch(`/messages?channel=${encodeURIComponent(currentChannel)}`);

    if (!res.ok) return;

    const data = await res.json();

    chat.innerHTML = "";

    data.forEach(addMessage);

    chat.scrollTop = chat.scrollHeight;
}

function avatarHtml(m) {
    if (m.profile_picture) {
        return `<img class="avatar-img" src="${escapeHtml(m.profile_picture)}" alt="">`;
    }

    return `<span class="avatar-bubble">${escapeHtml(m.avatar || "✊")}</span>`;
}

function onlineAvatarHtml(user) {
    if (user.profile_picture) {
        return `<img class="online-avatar-img" src="${escapeHtml(user.profile_picture)}" alt="">`;
    }

    return `<span class="online-emoji">${escapeHtml(user.avatar || "✊")}</span>`;
}

function addMessage(m) {
    if (m.channel !== currentChannel) return;

    const div = document.createElement("div");

    const mine = m.user === window.CURRENT_USER;

    div.className = mine ? "msg mine" : "msg";
    div.dataset.id = m.id;

    div.innerHTML = `
        <div class="msg-top">
            <span class="msg-userline">
                ${avatarHtml(m)}
                <b>${escapeHtml(m.user)}</b>
                <em>${escapeHtml(m.role || "user")}</em>
            </span>
            <span>${timeAgo(m.created)}</span>
        </div>
        <div class="msg-text">${escapeHtml(m.text)}</div>
        ${window.CAN_MODERATE ? `<button class="msg-delete" onclick="deleteMessage(${m.id})">löschen</button>` : ""}
    `;

    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

function sendMsg() {
    const text = textInput.value.trim();

    if (!text) return;

    socket.emit("send_message", {
        text: text,
        channel: currentChannel
    });

    textInput.value = "";
}

textInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        sendMsg();
    }
});

socket.on("connect", () => {
    socket.emit("ping_presence");
});

socket.on("new_message", (msg) => {
    addMessage(msg);
});

socket.on("message_deleted", (data) => {
    const el = document.querySelector(`.msg[data-id="${data.id}"]`);
    if (el) el.remove();
});

socket.on("chat_cleared", (data) => {
    if (data.channel === currentChannel) {
        chat.innerHTML = "";
    }
});

socket.on("channels_changed", () => {
    loadChannels();
    loadAdminChannels();
});

socket.on("motd_changed", (data) => {
    if (data.channel === "allgemein") {
        loadMotd();
    }
});

socket.on("online_users", (users) => {
    onlineUsers.innerHTML = "";

    if (users.length === 0) {
        onlineUsers.innerHTML = `<div class="empty-online">Niemand sichtbar online</div>`;
        return;
    }

    users.forEach(user => {
        const div = document.createElement("div");
        div.className = "online-user";
        div.innerHTML = `${onlineAvatarHtml(user)} ${escapeHtml(user.username)} <small>${escapeHtml(user.role)}</small>`;
        onlineUsers.appendChild(div);
    });
});

socket.on("send_error", (data) => {
    alert(data.error || "Nachricht konnte nicht gesendet werden");
});

socket.on("admin_users_changed", () => {
    loadAdminUsers();
    loadAdminLogs();
});

function toggleOnline() {
    onlinePanel.classList.toggle("hidden");
}

function toggleAdmin() {
    if (!adminPanel) return;
    adminPanel.classList.toggle("hidden");
    loadAdminUsers();
    loadAdminChannels();
    loadAdminLogs();
    loadMotd();
}

async function createChannel() {
    if (!newChannelName) return;

    const name = newChannelName.value.trim();
    const adminOnly = newChannelAdminOnly.checked;

    if (!name) return;

    const res = await fetch("/admin/create-channel", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            name: name,
            admin_only: adminOnly
        })
    });

    if (!res.ok) {
        alert("Raum konnte nicht erstellt werden");
        return;
    }

    newChannelName.value = "";
    newChannelAdminOnly.checked = false;

    loadChannels();
    loadAdminChannels();
    loadAdminLogs();
}

async function deleteChannel(name) {
    const sure = confirm(`#${name} wirklich löschen? Alle Nachrichten darin werden gelöscht.`);

    if (!sure) return;

    const res = await fetch("/admin/delete-channel", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ name })
    });

    if (!res.ok) {
        alert("Raum konnte nicht gelöscht werden");
        return;
    }

    loadChannels();
    loadAdminChannels();
    loadAdminLogs();
}

async function loadAdminUsers() {
    if (!window.IS_ADMIN || !adminUsers) return;

    const res = await fetch("/admin/users");

    if (!res.ok) return;

    const users = await res.json();

    adminUsers.innerHTML = "";

    users.forEach(u => {
        const div = document.createElement("div");
        div.className = "admin-user";

        const avatar = u.profile_picture
            ? `<img class="online-avatar-img" src="${escapeHtml(u.profile_picture)}" alt="">`
            : escapeHtml(u.avatar || "✊");

        div.innerHTML = `
            <div>
                <b>${avatar} ${escapeHtml(u.username)}</b>
                <span>${escapeHtml(u.role)}${u.banned ? " · GEBANNT" : ""}</span>
            </div>
            <div class="admin-user-actions">
                <button onclick="setRole('${escapeHtml(u.username)}', 'user')">User</button>
                <button onclick="setRole('${escapeHtml(u.username)}', 'mod')">Mod</button>
                <button onclick="setRole('${escapeHtml(u.username)}', 'admin')">Admin</button>
                ${u.role !== "admin" ? `<button onclick="toggleBan('${escapeHtml(u.username)}')">bannen</button>` : ""}
                ${u.role !== "admin" ? `<button onclick="resetPassword('${escapeHtml(u.username)}')">PW</button>` : ""}
                ${u.role !== "admin" ? `<button onclick="deleteUser('${escapeHtml(u.username)}')">löschen</button>` : ""}
            </div>
        `;

        adminUsers.appendChild(div);
    });
}

async function setRole(username, role) {
    await fetch("/admin/set-role", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ username, role })
    });

    loadAdminUsers();
    loadAdminLogs();
}

async function toggleBan(username) {
    await fetch("/admin/toggle-ban", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ username })
    });

    loadAdminUsers();
    loadAdminLogs();
}

async function resetPassword(username) {
    const newPassword = prompt(`Neues Passwort für ${username}:`);

    if (!newPassword) return;

    await fetch("/admin/reset-password", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            username: username,
            new_password: newPassword
        })
    });

    loadAdminLogs();
}

async function deleteUser(username) {
    const sure = confirm(`${username} wirklich löschen?`);

    if (!sure) return;

    await fetch("/admin/delete-user", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ username })
    });

    loadAdminUsers();
    loadAdminLogs();
}

async function deleteMessage(id) {
    await fetch("/admin/delete-message", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ id })
    });

    loadAdminLogs();
}

async function clearChat() {
    const sure = confirm(`Wirklich alle Nachrichten in #${currentChannel} löschen?`);

    if (!sure) return;

    await fetch("/admin/clear-chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ channel: currentChannel })
    });

    loadAdminLogs();
}

async function loadAdminLogs() {
    if (!window.IS_ADMIN || !adminLogs) return;

    const res = await fetch("/admin/logs");

    if (!res.ok) return;

    const logs = await res.json();

    adminLogs.innerHTML = "";

    logs.forEach(log => {
        const div = document.createElement("div");
        div.className = "log-row";

        div.innerHTML = `
            <b>${escapeHtml(log.actor)}</b>
            <span>${escapeHtml(log.action)}</span>
            <small>${escapeHtml(log.target || "")}</small>
        `;

        adminLogs.appendChild(div);
    });
}

function escapeHtml(str) {
    return String(str)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function timeAgo(value) {
    if (!value) return "";

    const date = new Date(value.replace(" ", "T") + "Z");
    const now = new Date();

    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 20) return "gerade eben";
    if (seconds < 60) return `vor ${seconds}s`;

    const minutes = Math.floor(seconds / 60);

    if (minutes < 60) return `vor ${minutes}m`;

    const hours = Math.floor(minutes / 60);

    return `vor ${hours}h`;
}

loadChannels();
loadMotd();

if (window.IS_ADMIN) {
    loadAdminUsers();
    loadAdminChannels();
    loadAdminLogs();
}

setInterval(() => {
    socket.emit("ping_presence");
}, 7000);

if (window.IS_ADMIN) {
    setInterval(loadAdminUsers, 5000);
    setInterval(loadAdminLogs, 7000);
}
