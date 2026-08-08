// TaskFlow Pro - Application Logic
document.addEventListener('DOMContentLoaded', () => {
    // API Configuration (Relative paths for same-origin single-process, fallback to host)
    const API_BASE = '';

    // Local Storage Cache Key
    const CACHE_KEY = 'taskflow_tasks_cache';

    // State Variables
    let users = [];
    let projects = [];
    let tasks = [];
    let selectedUserId = null;
    let selectedProjectId = null;
    let editingTaskId = null;
    let activeModalType = null; // 'user' or 'project'

    // DOM Elements
    const userSelect = document.getElementById('userSelect');
    const projectSelect = document.getElementById('projectSelect');
    const addUserBtn = document.getElementById('addUserBtn');
    const addProjectBtn = document.getElementById('addProjectBtn');

    const taskForm = document.getElementById('taskForm');
    const formTitle = document.getElementById('formTitle');
    const taskIdInput = document.getElementById('taskIdInput');
    const taskTitleInput = document.getElementById('taskTitleInput');
    const taskDueDateInput = document.getElementById('taskDueDateInput');
    const taskPriorityInput = document.getElementById('taskPriorityInput');
    const taskStatusInput = document.getElementById('taskStatusInput');
    const submitTaskBtn = document.getElementById('submitTaskBtn');
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    const titleError = document.getElementById('titleError');

    const taskListContainer = document.getElementById('taskListContainer');
    const filterStatusSelect = document.getElementById('filterStatus');
    const cacheNotice = document.getElementById('cacheNotice');

    const validationBanner = document.getElementById('validationBanner');
    const validationMessage = document.getElementById('validationMessage');
    const closeBannerBtn = document.getElementById('closeBannerBtn');

    // Stats Elements
    const statTotal = document.getElementById('statTotal');
    const statHigh = document.getElementById('statHigh');
    const statMedium = document.getElementById('statMedium');
    const statLow = document.getElementById('statLow');
    const statCompleted = document.getElementById('statCompleted');
    const statPending = document.getElementById('statPending');

    // Modal Elements
    const inputModal = document.getElementById('inputModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalInputLabel = document.getElementById('modalInputLabel');
    const modalInputField = document.getElementById('modalInputField');
    const modalError = document.getElementById('modalError');
    const modalSaveBtn = document.getElementById('modalSaveBtn');
    const modalCancelBtn = document.getElementById('modalCancelBtn');

    // ---------------------------------------------------------
    // INITIALIZATION & LOCALSTORAGE CACHING
    // ---------------------------------------------------------
    function init() {
        // Step 1: Render cached task list immediately on page load
        loadFromCache();

        // Step 2: Wire static Event Listeners (No inline onclick!)
        setupEventListeners();

        // Step 3: Fetch fresh data from real backend API
        loadInitialData();
    }

    // Load and render cached tasks from localStorage
    function loadFromCache() {
        try {
            const cachedData = localStorage.getItem(CACHE_KEY);
            if (cachedData) {
                const cachedTasks = JSON.parse(cachedData);
                if (Array.isArray(cachedTasks) && cachedTasks.length > 0) {
                    tasks = cachedTasks;
                    renderTaskList(tasks);
                    showCacheNotice(true);
                }
            }
        } catch (err) {
            console.warn('Failed to parse cached tasks:', err);
        }
    }

    // Save tasks array to localStorage
    function updateCache(newTasks) {
        try {
            localStorage.setItem(CACHE_KEY, JSON.stringify(newTasks));
        } catch (err) {
            console.warn('Failed to write tasks to localStorage:', err);
        }
    }

    function showCacheNotice(visible) {
        if (visible) {
            cacheNotice.classList.remove('hidden');
        } else {
            cacheNotice.classList.add('hidden');
        }
    }

    // ---------------------------------------------------------
    // EVENT LISTENERS SETUP
    // ---------------------------------------------------------
    function setupEventListeners() {
        // Form submission (Add / Edit task)
        taskForm.addEventListener('submit', handleTaskFormSubmit);

        // Cancel Edit button
        cancelEditBtn.addEventListener('click', resetTaskForm);

        // User & Project Select changes
        userSelect.addEventListener('change', (e) => {
            selectedUserId = parseInt(e.target.value, 10);
            fetchProjects();
        });

        projectSelect.addEventListener('change', (e) => {
            selectedProjectId = parseInt(e.target.value, 10);
            fetchTasks();
            fetchProjectStats();
        });

        // Add User / Add Project buttons
        addUserBtn.addEventListener('click', () => openModal('user'));
        addProjectBtn.addEventListener('click', () => openModal('project'));

        // Modal Save & Cancel
        modalSaveBtn.addEventListener('click', handleModalSave);
        modalCancelBtn.addEventListener('click', closeModal);

        // Filter status change
        filterStatusSelect.addEventListener('change', () => {
            renderTaskList(tasks);
        });

        // Close validation banner
        closeBannerBtn.addEventListener('click', hideBanner);

        // Title input live validation clearing
        taskTitleInput.addEventListener('input', () => {
            if (taskTitleInput.value.trim() !== '') {
                clearTitleError();
            }
        });
    }

    // ---------------------------------------------------------
    // API FETCH OPERATORS
    // ---------------------------------------------------------
    async function loadInitialData() {
        await fetchUsers();
    }

    async function fetchUsers() {
        try {
            const res = await fetch(`${API_BASE}/users`);
            if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
            users = await res.json();

            // Populate user select
            populateUserDropdown();

            // Handle empty users case automatically
            if (users.length === 0) {
                await createDefaultUserAndProject();
            } else {
                if (!selectedUserId) selectedUserId = users[0].id;
                userSelect.value = selectedUserId;
                await fetchProjects();
            }
        } catch (err) {
            showBanner(`Failed to load users: ${err.message}`);
        }
    }

    async function createDefaultUserAndProject() {
        try {
            // Create default user
            const uRes = await fetch(`${API_BASE}/users`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: 'demo@example.com', name: 'Demo User' })
            });
            const newUser = await uRes.json();
            users.push(newUser);
            selectedUserId = newUser.id;
            populateUserDropdown();
            userSelect.value = selectedUserId;

            // Create default project
            const pRes = await fetch(`${API_BASE}/projects`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: 'General Tasks', owner_id: newUser.id })
            });
            const newProject = await pRes.json();
            projects.push(newProject);
            selectedProjectId = newProject.id;
            populateProjectDropdown();
            projectSelect.value = selectedProjectId;

            // Create a sample task
            await fetch(`${API_BASE}/tasks`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: 'Welcome to TaskFlow Pro!',
                    project_id: newProject.id,
                    priority: 'high',
                    due_date: 'next friday',
                    status: 'pending'
                })
            });

            await fetchTasks();
            await fetchProjectStats();
        } catch (err) {
            showBanner(`Error initializing demo data: ${err.message}`);
        }
    }

    async function fetchProjects() {
        try {
            const res = await fetch(`${API_BASE}/projects`);
            if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
            const allProjects = await res.json();
            
            // Filter projects owned by selected user
            projects = allProjects.filter(p => p.owner_id === selectedUserId);
            populateProjectDropdown();

            if (projects.length > 0) {
                selectedProjectId = projects[0].id;
                projectSelect.value = selectedProjectId;
                await fetchTasks();
                await fetchProjectStats();
            } else {
                selectedProjectId = null;
                tasks = [];
                renderTaskList([]);
                updateStatsUI({ total_tasks: 0, priority_counts: {}, status_counts: {} });
            }
        } catch (err) {
            showBanner(`Failed to load projects: ${err.message}`);
        }
    }

    async function fetchTasks() {
        if (!selectedProjectId) {
            tasks = [];
            renderTaskList([]);
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/tasks?project_id=${selectedProjectId}`);
            if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
            
            const liveTasks = await res.json();
            tasks = liveTasks;
            
            // Reconcile and render live tasks
            renderTaskList(tasks);
            
            // Update localStorage cache
            updateCache(tasks);
            
            // Hide cache notice after successful live fetch
            showCacheNotice(false);
        } catch (err) {
            showBanner(`Failed to sync tasks from backend: ${err.message}`);
        }
    }

    async function fetchProjectStats() {
        if (!selectedProjectId) return;

        try {
            const res = await fetch(`${API_BASE}/projects/${selectedProjectId}/stats`);
            if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
            
            const stats = await res.json();
            updateStatsUI(stats);
        } catch (err) {
            console.warn('Stats fetch error:', err);
        }
    }

    // ---------------------------------------------------------
    // FORM SUBMISSION & CLIENT-SIDE VALIDATION
    // ---------------------------------------------------------
    async function handleTaskFormSubmit(e) {
        e.preventDefault();

        const titleValue = taskTitleInput.value;
        const trimmedTitle = titleValue.trim();

        // Client-side Validation Requirement: block submission if trimmed title is empty
        if (trimmedTitle === '') {
            showTitleError('Task title is required and cannot be blank.');
            return;
        }
        clearTitleError();

        if (!selectedProjectId) {
            showBanner('Please select or create a project first.');
            return;
        }

        const taskData = {
            title: trimmedTitle,
            project_id: selectedProjectId,
            priority: taskPriorityInput.value,
            due_date: taskDueDateInput.value.trim() || null,
            status: taskStatusInput.value
        };

        try {
            let res;
            if (editingTaskId) {
                // PUT request for update
                res = await fetch(`${API_BASE}/tasks/${editingTaskId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(taskData)
                });
            } else {
                // POST request for create
                res = await fetch(`${API_BASE}/tasks`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(taskData)
                });
            }

            if (!res.ok) {
                const errorPayload = await res.json();
                const msg = errorPayload.detail || 'Validation or server error';
                showBanner(`Backend Error (${res.status}): ${typeof msg === 'object' ? JSON.stringify(msg) : msg}`);
                return;
            }

            // Success! Reset form and refresh list & stats
            resetTaskForm();
            await fetchTasks();
            await fetchProjectStats();
        } catch (err) {
            showBanner(`Network error: ${err.message}`);
        }
    }

    // ---------------------------------------------------------
    // JS DOM RENDERING (STRICT document.createElement & textContent)
    // ---------------------------------------------------------
    function renderTaskList(taskList) {
        // Clear container
        while (taskListContainer.firstChild) {
            taskListContainer.removeChild(taskListContainer.firstChild);
        }

        const currentFilter = filterStatusSelect.value;
        const filteredTasks = taskList.filter(t => {
            if (currentFilter === 'all') return true;
            return t.status === currentFilter;
        });

        if (filteredTasks.length === 0) {
            const emptyDiv = document.createElement('div');
            emptyDiv.className = 'empty-state';
            emptyDiv.textContent = tasks.length === 0 ? 'No tasks in this project yet. Add one above!' : 'No tasks match the selected filter.';
            taskListContainer.appendChild(emptyDiv);
            return;
        }

        // Build each task item with document.createElement() and textContent ONLY
        filteredTasks.forEach(task => {
            const taskItem = document.createElement('div');
            taskItem.className = `task-item priority-${task.priority} ${task.status === 'completed' ? 'completed' : ''}`;
            taskItem.dataset.id = task.id;

            // Main Content Container
            const taskMain = document.createElement('div');
            taskMain.className = 'task-main';

            // Header line (Title + Priority badge)
            const headerLine = document.createElement('div');
            headerLine.className = 'task-header-line';

            const titleSpan = document.createElement('span');
            titleSpan.className = 'task-title';
            titleSpan.textContent = task.title; // STRICT textContent usage

            const priorityBadge = document.createElement('span');
            priorityBadge.className = `badge badge-${task.priority}`;
            priorityBadge.textContent = task.priority.toUpperCase(); // STRICT textContent usage

            headerLine.appendChild(titleSpan);
            headerLine.appendChild(priorityBadge);

            // Meta line (Due Date & Status)
            const metaLine = document.createElement('div');
            metaLine.className = 'task-meta';

            if (task.due_date) {
                const dueSpan = document.createElement('span');
                dueSpan.textContent = `📅 Due: ${task.due_date}`; // STRICT textContent usage
                metaLine.appendChild(dueSpan);
            }

            const statusBadge = document.createElement('span');
            statusBadge.className = `badge badge-status ${task.status === 'completed' ? 'completed' : ''}`;
            statusBadge.textContent = task.status === 'completed' ? '✓ Completed' : '⏳ Pending'; // STRICT textContent usage
            metaLine.appendChild(statusBadge);

            taskMain.appendChild(headerLine);
            taskMain.appendChild(metaLine);

            // Actions Container (Edit & Delete buttons with addEventListener)
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'task-actions';

            // Edit Button
            const editBtn = document.createElement('button');
            editBtn.type = 'button';
            editBtn.className = 'btn-icon edit';
            editBtn.title = 'Edit Task';
            editBtn.textContent = '✏️';
            // Wired with addEventListener (no inline onclick)
            editBtn.addEventListener('click', () => startEditingTask(task));

            // Delete Button
            const deleteBtn = document.createElement('button');
            deleteBtn.type = 'button';
            deleteBtn.className = 'btn-icon delete';
            deleteBtn.title = 'Delete Task';
            deleteBtn.textContent = '🗑️';
            // Wired with addEventListener (no inline onclick)
            deleteBtn.addEventListener('click', () => deleteTask(task.id));

            actionsDiv.appendChild(editBtn);
            actionsDiv.appendChild(deleteBtn);

            taskItem.appendChild(taskMain);
            taskItem.appendChild(actionsDiv);

            taskListContainer.appendChild(taskItem);
        });
    }

    // ---------------------------------------------------------
    // EDIT & DELETE ACTIONS
    // ---------------------------------------------------------
    function startEditingTask(task) {
        editingTaskId = task.id;
        taskIdInput.value = task.id;
        taskTitleInput.value = task.title;
        taskDueDateInput.value = task.due_date || '';
        taskPriorityInput.value = task.priority;
        taskStatusInput.value = task.status;

        formTitle.textContent = 'Edit Task';
        submitTaskBtn.textContent = 'Update Task';
        cancelEditBtn.classList.remove('hidden');
        clearTitleError();

        // Scroll form into view if needed
        taskForm.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function resetTaskForm() {
        editingTaskId = null;
        taskIdInput.value = '';
        taskTitleInput.value = '';
        taskDueDateInput.value = '';
        taskPriorityInput.value = 'medium';
        taskStatusInput.value = 'pending';

        formTitle.textContent = 'Create New Task';
        submitTaskBtn.textContent = 'Add Task';
        cancelEditBtn.classList.add('hidden');
        clearTitleError();
    }

    async function deleteTask(taskId) {
        if (!confirm('Are you sure you want to delete this task?')) return;

        try {
            const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
                method: 'DELETE'
            });

            if (!res.ok) {
                const errData = await res.json();
                showBanner(`Delete failed: ${errData.detail}`);
                return;
            }

            // Success! Refresh list and stats
            await fetchTasks();
            await fetchProjectStats();
        } catch (err) {
            showBanner(`Network error deleting task: ${err.message}`);
        }
    }

    // ---------------------------------------------------------
    // STATS UI RENDERING
    // ---------------------------------------------------------
    function updateStatsUI(stats) {
        statTotal.textContent = stats.total_tasks || 0;
        statHigh.textContent = stats.priority_counts?.high || 0;
        statMedium.textContent = stats.priority_counts?.medium || 0;
        statLow.textContent = stats.priority_counts?.low || 0;
        statCompleted.textContent = stats.status_counts?.completed || 0;
        statPending.textContent = stats.status_counts?.pending || 0;
    }

    // ---------------------------------------------------------
    // DROPDOWN HELPERS
    // ---------------------------------------------------------
    function populateUserDropdown() {
        userSelect.innerHTML = '';
        users.forEach(u => {
            const opt = document.createElement('option');
            opt.value = u.id;
            opt.textContent = `${u.name || u.email} (${u.email})`;
            userSelect.appendChild(opt);
        });
    }

    function populateProjectDropdown() {
        projectSelect.innerHTML = '';
        projects.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = p.name;
            projectSelect.appendChild(opt);
        });
    }

    // ---------------------------------------------------------
    // MODAL DIALOG HANDLERS (Add User / Add Project)
    // ---------------------------------------------------------
    function openModal(type) {
        activeModalType = type;
        modalInputField.value = '';
        modalError.classList.add('hidden');

        if (type === 'user') {
            modalTitle.textContent = 'Add New User';
            modalInputLabel.textContent = 'User Email Address';
            modalInputField.placeholder = 'e.g. user@example.com';
        } else {
            modalTitle.textContent = 'Add New Project';
            modalInputLabel.textContent = 'Project Name';
            modalInputField.placeholder = 'e.g. Mobile App Redesign';
        }

        inputModal.classList.remove('hidden');
        modalInputField.focus();
    }

    function closeModal() {
        inputModal.classList.add('hidden');
        activeModalType = null;
    }

    async function handleModalSave() {
        const value = modalInputField.value.trim();
        if (!value) {
            modalError.textContent = 'Field cannot be empty.';
            modalError.classList.remove('hidden');
            return;
        }

        try {
            if (activeModalType === 'user') {
                const res = await fetch(`${API_BASE}/users`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: value, name: value.split('@')[0] })
                });
                if (!res.ok) {
                    const err = await res.json();
                    modalError.textContent = err.detail || 'Error creating user';
                    modalError.classList.remove('hidden');
                    return;
                }
                const newUser = await res.json();
                users.push(newUser);
                selectedUserId = newUser.id;
                populateUserDropdown();
                userSelect.value = selectedUserId;
                await fetchProjects();
            } else if (activeModalType === 'project') {
                if (!selectedUserId) {
                    modalError.textContent = 'Select a user first.';
                    modalError.classList.remove('hidden');
                    return;
                }
                const res = await fetch(`${API_BASE}/projects`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: value, owner_id: selectedUserId })
                });
                if (!res.ok) {
                    const err = await res.json();
                    modalError.textContent = err.detail || 'Error creating project';
                    modalError.classList.remove('hidden');
                    return;
                }
                const newProject = await res.json();
                projects.push(newProject);
                selectedProjectId = newProject.id;
                populateProjectDropdown();
                projectSelect.value = selectedProjectId;
                await fetchTasks();
                await fetchProjectStats();
            }

            closeModal();
        } catch (err) {
            modalError.textContent = err.message;
            modalError.classList.remove('hidden');
        }
    }

    // ---------------------------------------------------------
    // ERROR & VALIDATION UI HELPERS
    // ---------------------------------------------------------
    function showTitleError(msg) {
        titleError.textContent = msg;
        titleError.classList.remove('hidden');
        taskTitleInput.style.borderColor = 'var(--accent-rose)';
    }

    function clearTitleError() {
        titleError.textContent = '';
        titleError.classList.add('hidden');
        taskTitleInput.style.borderColor = '';
    }

    function showBanner(msg) {
        validationMessage.textContent = msg;
        validationBanner.classList.remove('hidden');
    }

    function hideBanner() {
        validationBanner.classList.add('hidden');
    }

    // Kickoff App Initialization
    init();
});
