// Fetch and display workers
function loadWorkers() {
    fetch("/workers")
        .then((response) => response.json())
        .then((data) => {
            const tableBody = document.querySelector("#workers-table tbody");
            tableBody.innerHTML = "";

            if (data.workers && Array.isArray(data.workers)) {
                data.workers.forEach((worker) => {
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>${worker.id}</td>
                        <td>${worker.endpoint}</td>
                        <td><input readonly type="number" value="${worker.frequency}" ${worker.status === "running" ? "disabled" : ""} onchange="updateWorker('${worker.id}', 'frequency', this.value)"></td>
                        <td><input readonly type="number" value="${worker.total_calls}" ${worker.status === "running" ? "disabled" : ""} onchange="updateWorker('${worker.id}', 'total_calls', this.value)"></td>
                        <td>${worker.remaining_calls}</td>
                        <td>${worker.status}</td>
                        <td>
                            <button class="btn btn-sm ${worker.status === "running" ? "btn-warning" : "btn-success"}" onclick="toggleWorkerStatus('${worker.id}', '${worker.status}')">
                                ${worker.status === "running" ? "Stop" : "Start"}
                            </button>
                            <button class="btn btn-info btn-sm" ${worker.status === "running" ? "disabled" : ""} onclick="openEditModal('${worker.id}', '${worker.endpoint}', ${worker.frequency}, ${worker.total_calls})">Edit</button>
                            <button class="btn btn-danger btn-sm" ${worker.status === "running" ? "disabled" : ""} onclick="deleteWorker('${worker.id}')">Delete</button>
                            <button class="btn btn-secondary btn-sm" ${worker.status === "running" ? "disabled" : ""} onclick="viewResponses('${worker.id}')">View Responses</button>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });
            } else {
                console.error("Invalid data structure:", data);
            }
        })
        .catch((error) => {
            console.error("Error fetching workers:", error);
        });
}
// Validate endpoint
function validateEndpoint() {
    const endpoint = document.getElementById("endpoint").value;
    fetch("/workers/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ endpoint }),
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.is_valid) {
                alert("Endpoint is valid!");
                document.getElementById("add-worker-btn").disabled = false;
            } else {
                alert("Endpoint is invalid!");
            }
        });
}

// Add worker
document.getElementById("add-worker-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const endpoint = document.getElementById("endpoint").value;
    const frequency = parseInt(document.getElementById("frequency").value, 10);  // Ensure frequency is an integer
    const totalCalls = parseInt(document.getElementById("total-calls").value, 10);  // Ensure total_calls is an integer

    fetch("/workers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ endpoint, frequency, total_calls: totalCalls }),
    })
        .then((response) => response.json())
        .then(() => {
            loadWorkers();
            document.getElementById("add-worker-form").reset();
            document.getElementById("add-worker-btn").disabled = true;
        });
});

// Toggle worker status (start/stop)
function toggleWorkerStatus(workerId, currentStatus) {
    const action = currentStatus === "running" ? "stop" : "start";
    fetch(`/workers/${workerId}/${action}`, { method: "POST" })
        .then((response) => response.json())
        .then(() => loadWorkers());
}

// Open edit modal
function openEditModal(workerId, endpoint, frequency, totalCalls) {
    document.getElementById("edit-worker-id").value = workerId;
    document.getElementById("edit-endpoint").value = endpoint;
    document.getElementById("edit-frequency").value = frequency;
    document.getElementById("edit-total-calls").value = totalCalls;
    new bootstrap.Modal(document.getElementById("editWorkerModal")).show();
}

// Save edited worker
function saveEditedWorker() {
    const workerId = document.getElementById("edit-worker-id").value;
    const endpoint = document.getElementById("edit-endpoint").value;
    const frequency = parseInt(document.getElementById("edit-frequency").value, 10);  // Ensure frequency is an integer
    const totalCalls = parseInt(document.getElementById("edit-total-calls").value, 10);  // Ensure total_calls is an integer

    fetch(`/workers/${workerId}/edit`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ endpoint, frequency, total_calls: totalCalls }),
    })
        .then((response) => response.json())
        .then(() => {
            loadWorkers();
            bootstrap.Modal.getInstance(document.getElementById("editWorkerModal")).hide();
        });
}

// Export workers
function exportWorkers() {
    window.location.href = "/workers/export";
}

// Import workers
document.getElementById("import-file").addEventListener("change", (e) => {
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append("file", file);
    fetch("/workers/import", {
        method: "POST",
        body: formData,
    })
        .then((response) => response.json())
        .then(() => loadWorkers());
});

// Delete worker
function deleteWorker(workerId) {
    if (confirm("Are you sure you want to delete this worker?")) {
        fetch(`/workers/${workerId}`, {
            method: "DELETE",
        })
            .then((response) => response.json())
            .then(() => loadWorkers())
            .catch((error) => {
                console.error("Error deleting worker:", error);
            });
    }
}

function viewResponses(workerId) {
    fetch(`/workers/${workerId}/responses`)
        .then((response) => response.json())
        .then((data) => {
            const responsesContent = document.getElementById("responses-content");
            responsesContent.textContent = JSON.stringify(data.responses, null, 2);  // Pretty-print JSON

            // Update the download button's onclick event
            const downloadButton = document.querySelector("#viewResponsesModal .btn-primary");
            downloadButton.setAttribute("onclick", `downloadResponses('${workerId}')`);

            // Show the modal
            new bootstrap.Modal(document.getElementById("viewResponsesModal")).show();
        })
        .catch((error) => {
            console.error("Error fetching responses:", error);
        });
}

function downloadResponses(workerId) {
    window.location.href = `/workers/${workerId}/responses/download`;
}
// Load workers on page load
loadWorkers();