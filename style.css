const socket = io();

const chat = document.getElementById("chat");

function addMsg(m) {
    const div = document.createElement("div");
    div.className = "msg";
    div.innerHTML = `<b>${m.user}</b>: ${m.text}`;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

// history load
fetch("/history")
    .then(r => r.json())
    .then(data => data.forEach(addMsg));

// live incoming
socket.on("new_message", (msg) => {
    addMsg(msg);
});

function sendMsg() {
    const user = document.getElementById("user").value || "anon";
    const text = document.getElementById("text").value;

    socket.emit("send_message", {user, text});

    document.getElementById("text").value = "";
}
