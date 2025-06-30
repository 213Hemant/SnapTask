// static/main.js
const socket = io();
const roomSelect = document.getElementById('roomSelect');
const joinBtn    = document.getElementById('joinBtn');
const taskInput  = document.getElementById('taskInput');
const addBtn     = document.getElementById('addBtn');
const tasksList  = document.getElementById('tasks');
const toastContainer = document.getElementById('toastContainer');
const editModal  = document.getElementById('editModal');
const editInput  = document.getElementById('editInput');
const cancelEdit = document.getElementById('cancelEdit');
const saveEdit   = document.getElementById('saveEdit');

let currentRoom   = null;
let editingTaskId = null;

// Show temp toast
function showToast(message) {
  const div = document.createElement('div');
  div.className = 'bg-white p-3 rounded shadow-lg animate-fade-in-out';
  div.textContent = message;
  toastContainer.appendChild(div);
  setTimeout(() => div.remove(), 3000);
}

// Build a task element
function createTaskElement(task) {
  const li = document.createElement('li');
  li.dataset.id = task.id;
  li.className = 'flex items-center justify-between bg-white p-3 rounded shadow';

  const left = document.createElement('div');
  const cb = document.createElement('input');
  cb.type = 'checkbox'; cb.className = 'toggle-done mr-2'; cb.checked = task.done;
  left.appendChild(cb);

  const span = document.createElement('span');
  span.textContent = task.text;
  span.classList.add('task-text', 'cursor-pointer');
  if (task.done) span.classList.add('line-through', 'text-gray-500');
  span.onclick = () => openEditModal(task.id, task.text);
  left.appendChild(span);

  li.appendChild(left);

  const removeBtn = document.createElement('button');
  removeBtn.className = 'remove-btn text-red-500'; removeBtn.textContent = '✕';
  li.appendChild(removeBtn);

  return li;
}

// Modal
function openEditModal(id, text) {
  editingTaskId = id;
  editInput.value = text;
  editModal.classList.remove('hidden');
}
cancelEdit.onclick = () => editModal.classList.add('hidden');
saveEdit.onclick = () => {
  const newText = editInput.value.trim();
  if (!newText) return;
  socket.emit('edit_task', { room: currentRoom, id: editingTaskId, text: newText, username: CURRENT_USER });
  editModal.classList.add('hidden');
};

// Join room
joinBtn.onclick = () => {
  const room = roomSelect.value;
  if (!room) return;
  currentRoom = room;
  socket.emit('join_room', { room, username: CURRENT_USER });
  taskInput.disabled = false;
  addBtn.disabled = false;
  tasksList.innerHTML = '';
};

// Socket listeners
socket.on('room_data', ({ tasks }) =>
  tasks.forEach(t => tasksList.appendChild(createTaskElement(t)))
);

socket.on('notification', ({ message, username }) =>
  showToast(`${username || 'Someone'}: ${message}`)
);

// Add task
addBtn.onclick = () => {
  const text = taskInput.value.trim();
  if (!text) return;
  socket.emit('add_task', { room: currentRoom, text, username: CURRENT_USER });
  taskInput.value = '';
};

// Task events
socket.on('task_added', task =>
  tasksList.appendChild(createTaskElement(task))
);

socket.on('task_removed', ({ id }) => {
  const el = tasksList.querySelector(`li[data-id='${id}']`);
  if (el) el.remove();
});

socket.on('task_toggled', ({ id, done }) => {
  const el = tasksList.querySelector(`li[data-id='${id}']`);
  if (!el) return;
  const cb   = el.querySelector('.toggle-done');
  const span = el.querySelector('.task-text');
  cb.checked = done;
  span.classList.toggle('line-through', done);
  span.classList.toggle('text-gray-500', done);
});

socket.on('task_edited', ({ id, text }) => {
  const el = tasksList.querySelector(`li[data-id='${id}'] .task-text`);
  if (el) el.textContent = text;
});

// Delegate remove/toggle
tasksList.addEventListener('click', e => {
  if (!currentRoom) return;
  if (e.target.matches('.remove-btn')) {
    const id = +e.target.closest('li').dataset.id;
    socket.emit('remove_task', { room: currentRoom, id, username: CURRENT_USER });
  } else if (e.target.matches('.toggle-done')) {
    const id = +e.target.closest('li').dataset.id;
    socket.emit('toggle_done', { room: currentRoom, id, username: CURRENT_USER });
  }
});
