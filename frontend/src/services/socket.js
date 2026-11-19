export function createInterviewSocket() {
  const address = new URL("/ws/interview", window.location.href);
  address.protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(address.toString());
  socket.binaryType = "arraybuffer";
  return socket;
}

export function sendSocketEvent(socket, event, data = {}) {
  if (!socket || socket.readyState !== WebSocket.OPEN) return false;
  socket.send(JSON.stringify({ event, ...data }));
  return true;
}
