// static/main.js

// Socket & DOM elements
const socket           = io();
const roomSelect       = document.getElementById('roomSelect');
const joinBtn          = document.getElementById('joinBtn');
const taskInput        = document.getElementById('taskInput');
const dueDateInput     = document.getElementById('dueDateInput');
const addBtn           = document.getElementById('addBtn');
const tasksList        = document.getElementById('tasks');
const toastContainer   = document.getElementById('toastContainer');
const typingIndicator  = document.getElementById('typingIndicator');
const editModal        = document.getElementById('editModal');
const editInput        = document.getElementById('editInput');
const editDueDate      = document.getElementById('editDueDate');
const cancelEdit       = document.getElementById('cancelEdit');
const saveEdit         = document.getElementById('saveEdit');

let currentRoom   = null;
let editingTaskId = null;
let typingTimeout = null;

// Utility: show a temporary toast
function showToast(message) {
  const div = document.createElement('div');
  div.className = 'bg-white p-3 rounded shadow-lg animate-fade-in-out transition-opacity duration-700 opacity-100';
  div.textContent = message;
  toastContainer.appendChild(div);
  setTimeout(() => div.classList.add('opacity-0'), 2500);
  setTimeout(() => div.remove(), 3000);
}

// Get color class based on due date
function getDueDateColor(dueDate) {
  if (!dueDate) return '';
  const today = new Date();
  const due = new Date(dueDate);
  today.setHours(0, 0, 0, 0);
  due.setHours(0, 0, 0, 0);
  if (due < today) return 'bg-red-100 border-l-4 border-red-400';
  if (due.getTime() === today.getTime()) return 'bg-yellow-100 border-l-4 border-yellow-400';
  return 'bg-green-100 border-l-4 border-green-400';
}

// Build a task <li> element with due-date and author meta
function createTaskElement(task) {
  const li = document.createElement('li');
  li.dataset.id = task.id;
  li.className = `flex flex-col p-3 rounded shadow mb-2 animate-fade-in ${getDueDateColor(task.due_date)}`;

  // Top row: checkbox, text, remove button
  const topRow = document.createElement('div');
  topRow.className = 'flex items-center justify-between';

  const left = document.createElement('div');
  left.className = 'flex items-center';

  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.className = 'toggle-done mr-2';
  checkbox.checked = task.done;
  left.appendChild(checkbox);

  const span = document.createElement('span');
  span.textContent = task.text;
  span.classList.add('task-text', 'cursor-pointer');
  if (task.done) span.classList.add('line-through', 'text-gray-500');
  span.onclick = () => openEditModal(task.id, task.text, task.due_date);
  left.appendChild(span);

  topRow.appendChild(left);

  const removeBtn = document.createElement('button');
  removeBtn.className = 'remove-btn text-red-500';
  removeBtn.textContent = '✕';
  topRow.appendChild(removeBtn);

  li.appendChild(topRow);

  // Due date display
  if (task.due_date) {
    const due = document.createElement('div');
    due.className = 'text-xs text-gray-600 mt-1';
    due.textContent = `Due: ${task.due_date}`;
    li.appendChild(due);
  }

  // Creator / editor metadata
  const meta = document.createElement('div');
  meta.className = 'text-xs text-gray-500 mt-1';
  if (task.last_modified_by && task.last_modified_by !== task.created_by) {
    meta.textContent = `Created by ${task.created_by}, last edited by ${task.last_modified_by}`;
  } else {
    meta.textContent = `Created by ${task.created_by}`;
  }
  li.appendChild(meta);

  return li;
}

// Open the edit modal and populate fields
function openEditModal(id, text, dueDate) {
  editingTaskId = id;
  editInput.value     = text;
  editDueDate.value   = dueDate || '';
  editModal.classList.remove('hidden');
  editInput.focus();
}

// Modal button handlers
cancelEdit.onclick = () => {
  editModal.classList.add('hidden');
  taskInput.focus();
};
saveEdit.onclick = () => {
  const newText = editInput.value.trim();
  const newDue  = editDueDate.value || null;
  if (!newText) return;
  socket.emit('edit_task', {
    room:     currentRoom,
    id:       editingTaskId,
    text:     newText,
    due_date: newDue,
    username: CURRENT_USER
  });
  editModal.classList.add('hidden');
  taskInput.focus();
};

// Allow Enter key to add a task
[taskInput, dueDateInput].forEach(el =>
  el.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addBtn.click();
    }
  })
);

// Close modal on Escape
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && !editModal.classList.contains('hidden')) {
    editModal.classList.add('hidden');
    taskInput.focus();
  }
});

// Emit typing / stop_typing events
function emitTyping() {
  if (!currentRoom) return;
  socket.emit('typing', { room: currentRoom, username: CURRENT_USER });
  clearTimeout(typingTimeout);
  typingTimeout = setTimeout(() => {
    socket.emit('stop_typing', { room: currentRoom });
  }, 1500);
}

// Join a room
joinBtn.onclick = () => {
  const room = roomSelect.value;
  if (!room) return;
  currentRoom = room;
  typingIndicator.textContent = '';
  socket.emit('join_room', { room, username: CURRENT_USER });
  taskInput.disabled    = false;
  dueDateInput.disabled = false;
  addBtn.disabled       = false;
  tasksList.innerHTML   = '';
};

// Add a new task (with optional due date)
addBtn.onclick = () => {
  const text = taskInput.value.trim();
  const due  = dueDateInput.value || null;
  if (!text) return;
  socket.emit('add_task', {
    room:     currentRoom,
    text:     text,
    due_date: due,
    username: CURRENT_USER
  });
  taskInput.value    = '';
  dueDateInput.value = '';
};

// Socket.IO listeners

// Initial load of tasks (sorted by due date)
socket.on('room_data', ({ tasks }) => {
  tasksList.innerHTML = '';
  tasks
    .sort((a, b) => {
      if (!a.due_date) return 1;
      if (!b.due_date) return -1;
      return new Date(a.due_date) - new Date(b.due_date);
    })
    .forEach(t => tasksList.appendChild(createTaskElement(t)));
});

// Task added
socket.on('task_added', task => {
  const el = createTaskElement(task);
  tasksList.appendChild(el);
});

// Task removed
socket.on('task_removed', ({ id }) => {
  const el = tasksList.querySelector(`li[data-id='${id}']`);
  if (el) el.remove();
});

// Task toggled
socket.on('task_toggled', ({ id, done }) => {
  const el = tasksList.querySelector(`li[data-id='${id}']`);
  if (!el) return;
  const cb = el.querySelector('.toggle-done');
  const span = el.querySelector('.task-text');
  cb.checked = done;
  span.classList.toggle('line-through', done);
  span.classList.toggle('text-gray-500', done);
});

// Task edited
socket.on('task_edited', ({ id, text, due_date }) => {
  const el = tasksList.querySelector(`li[data-id='${id}']`);
  if (!el) return;
  el.querySelector('.task-text').textContent = text;

  let dueEl = el.querySelector('.text-gray-600');
  if (due_date) {
    if (!dueEl) {
      dueEl = document.createElement('div');
      dueEl.className = 'text-xs text-gray-600 mt-1';
      el.appendChild(dueEl);
    }
    dueEl.textContent = `Due: ${due_date}`;
  } else if (dueEl) {
    dueEl.remove();
  }

  // Recalculate and apply due-date color
  el.className = `flex flex-col p-3 rounded shadow mb-2 animate-fade-in ${getDueDateColor(due_date)}`;
});

// Notifications
socket.on('notification', ({ message, username }) =>
  showToast(`${username || 'Someone'}: ${message}`)
);

// Typing indicators
socket.on('user_typing', ({ username }) => {
  typingIndicator.textContent = `${username} is typing...`;
});
socket.on('user_stop_typing', () => {
  typingIndicator.textContent = '';
});

// Delegate remove & toggle events
tasksList.addEventListener('click', e => {
  if (!currentRoom) return;

  if (e.target.matches('.remove-btn')) {
    const id = Number(e.target.closest('li').dataset.id);
    socket.emit('remove_task', { room: currentRoom, id, username: CURRENT_USER });
  } else if (e.target.matches('.toggle-done')) {
    const id = Number(e.target.closest('li').dataset.id);
    socket.emit('toggle_done', { room: currentRoom, id, username: CURRENT_USER });
  }
});

// Attach typing listeners
taskInput.addEventListener('input', emitTyping);
dueDateInput.addEventListener('input', emitTyping);
