let tasks = []; // in-memory task list


const taskForm = document.getElementById("taskForm");
const taskTitleInput = document.getElementById("taskTitle");
const taskDueDateInput = document.getElementById("taskDueDate");
const taskEstimatedHoursInput = document.getElementById("taskEstimatedHours");
const taskImportanceInput = document.getElementById("taskImportance");
const taskDependenciesInput = document.getElementById("taskDependencies");

const addTaskBtn = document.getElementById("addTaskBtn");
const clearTasksBtn = document.getElementById("clearTasksBtn");

const bulkJsonTextarea = document.getElementById("bulkJson");
const loadJsonBtn = document.getElementById("loadJsonBtn");

const taskPreviewList = document.getElementById("taskPreviewList");

const strategySelect = document.getElementById("strategySelect");
const analyzeBtn = document.getElementById("analyzeBtn");

const statusMessage = document.getElementById("statusMessage");
const resultsBody = document.getElementById("resultsBody");

function setStatus(message, type = "") {
  statusMessage.textContent = message || "";
  statusMessage.className = "status-message"; // reset
  if (type) {
    statusMessage.classList.add(type);
  }
}

function parseDependencies(raw) {
  if (!raw || !raw.trim()) return [];
  return raw
    .split(",")
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => !Number.isNaN(n));
}

// Task management input
function addTaskFromForm() {
  const title = taskTitleInput.value.trim();
  const dueDate = taskDueDateInput.value; // YYYY-MM-DD
  const estimatedHours = parseFloat(taskEstimatedHoursInput.value);
  const importance = parseInt(taskImportanceInput.value, 10);
  const deps = parseDependencies(taskDependenciesInput.value);

  if (!title || !dueDate || Number.isNaN(estimatedHours) || Number.isNaN(importance)) {
    setStatus("Please fill all required fields correctly.", "error");
    return;
  }

  if (importance < 1 || importance > 10) {
    setStatus("Importance must be between 1 and 10.", "error");
    return;
  }

  const id = tasks.length + 1; // auto ID

  const task = {
    id,
    title,
    due_date: dueDate,
    estimated_hours: estimatedHours,
    importance,
    dependencies: deps,
  };

  tasks.push(task);
  renderTaskPreview();
  taskForm.reset();
  setStatus("");
}

function clearAllTasks() {
  tasks = [];
  renderTaskPreview();
  clearResults();
  setStatus("All tasks cleared.", "success");
}

function renderTaskPreview() {
  taskPreviewList.innerHTML = "";

  if (!tasks.length) {
    const li = document.createElement("li");
    li.textContent = "No tasks added yet.";
    li.style.color = "#9ca3af";
    taskPreviewList.appendChild(li);
    return;
  }

  tasks.forEach((t) => {
    const li = document.createElement("li");
    li.textContent = `ID ${t.id}: ${t.title} (due: ${t.due_date}, hours: ${t.estimated_hours}, importance: ${t.importance}, deps: [${t.dependencies.join(
      ", "
    )}])`;
    taskPreviewList.appendChild(li);
  });
}

// Bulk JSON loading
function loadTasksFromJson() {
  const raw = bulkJsonTextarea.value.trim();
  if (!raw) {
    setStatus("Please paste a JSON array of tasks first.", "error");
    return;
  }

  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (e) {
    console.error(e);
    setStatus("Invalid JSON. Please check the format.", "error");
    return;
  }

  if (!Array.isArray(parsed)) {
    setStatus("JSON must be an array of task objects.", "error");
    return;
  }

  // Continue IDs from current length
  let currentId = tasks.length;

  parsed.forEach((t) => {
    if (!t.title || !t.due_date) {
      return;
    }

    currentId += 1;
    tasks.push({
      id: currentId,
      title: t.title,
      due_date: t.due_date,
      estimated_hours:
        typeof t.estimated_hours === "number" ? t.estimated_hours : null,
      importance:
        typeof t.importance === "number" ? t.importance : 5,
      dependencies: Array.isArray(t.dependencies) ? t.dependencies : [],
    });
  });

  renderTaskPreview();
  setStatus("Tasks loaded from JSON.", "success");
}

// Results rendering
function clearResults() {
  resultsBody.innerHTML = "";
}

function getPriorityClass(score) {
  if (score >= 0.7) return "priority-high";
  if (score >= 0.5) return "priority-medium";
  return "priority-low";
}

function renderResults(scoredTasks) {
  clearResults();

  if (!scoredTasks || !scoredTasks.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 7;
    td.textContent = "No results to display.";
    td.style.textAlign = "center";
    tr.appendChild(td);
    resultsBody.appendChild(tr);
    return;
  }

  scoredTasks.forEach((t, index) => {
    const tr = document.createElement("tr");
    tr.classList.add(getPriorityClass(t.score));

    const deps = Array.isArray(t.dependencies)
      ? t.dependencies.join(", ")
      : "";

    tr.innerHTML = `
      <td>${index + 1}</td>
      <td>${t.title}</td>
      <td>${t.due_date || "-"}</td>
      <td>${t.estimated_hours ?? "-"}</td>
      <td>${t.importance ?? "-"}</td>
      <td>${t.score.toFixed ? t.score.toFixed(3) : t.score}</td>
      <td>${t.explanation || ""}</td>
    `;

    resultsBody.appendChild(tr);
  });
}

// API call
async function analyzeTasks() {
  if (!tasks.length) {
    setStatus("Please add at least one task before analyzing.", "error");
    return;
  }

  const strategy = strategySelect.value;
  const payload = {
    strategy,
    tasks,
  };

  setStatus("Analyzing tasks...", "");
  clearResults();

  try {
    const response = await fetch("/api/tasks/analyze/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("API error:", errorText);
      setStatus("Error from server while analyzing tasks.", "error");
      return;
    }

    const data = await response.json();
    renderResults(data.tasks);
    setStatus(`Analysis completed using strategy: ${data.strategy}`, "success");
  } catch (error) {
    console.error(error);
    setStatus("Network error while calling the API.", "error");
  }
}

// Event listeners
addTaskBtn.addEventListener("click", addTaskFromForm);
clearTasksBtn.addEventListener("click", clearAllTasks);
loadJsonBtn.addEventListener("click", loadTasksFromJson);
analyzeBtn.addEventListener("click", analyzeTasks);

// Prevent default form submit navigation
taskForm.addEventListener("submit", (e) => e.preventDefault());

// Initial render
renderTaskPreview();
setStatus("");
