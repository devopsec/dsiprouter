$(document).ready(function() {
    const apiBase = '/api/numbers/v1'; // Adjust if needed
    
    // Load carriers for dropdown
    function loadCarriers() {
        fetch(`${apiBase}/number`)
            .then(response => response.json())
            .then(data => {
                const carriers = [...new Set(data.data.map(n => n.carrier).filter(c => c))];
                const select = $('#carrier');
                select.empty();
                select.append('<option value="">Select Carrier</option>');
                carriers.forEach(c => select.append(`<option value="${c}">${c}</option>`));
            });
    }
    
    // Load numbers
    function loadNumbers() {
        fetch(`${apiBase}/number`)
            .then(response => response.json())
            .then(data => {
                const tbody = $('#numbers-table tbody');
                tbody.empty();
                data.data.forEach(n => {
                    tbody.append(`
                        <tr>
                            <td>${n.id}</td>
                            <td>${n.did}</td>
                            <td>${n.status}</td>
                            <td>${n.carrier}</td>
                            <td>${n.pool}</td>
                            <td>${n.assigned_length}</td>
                            <td>${n.assigned_reference_id}</td>
                            <td>${n.assigned_date}</td>
                            <td>
                                <button onclick="editNumber(${n.id})">Edit</button>
                                <button onclick="deleteNumber(${n.id})">Delete</button>
                            </td>
                        </tr>
                    `);
                });
            });
    }
    
    // Handle status change to show/hide assigned fields
    $('#status').change(function() {
        const form = $('#number-form');
        if ($(this).val() === 'assigned') {
            form.addClass('status-assigned');
        } else {
            form.removeClass('status-assigned');
        }
    });
    
    // Submit form
    $('#number-form').submit(function(e) {
        e.preventDefault();
        const id = $('#number-id').val();
        const data = {
            did: $('#did').val(),
            status: $('#status').val(),
            carrier: $('#carrier').val(),
            pool: $('#pool').val(),
            assigned_length: $('#assigned_length').val(),
            assigned_reference_id: $('#assigned_reference_id').val(),
            assigned_date: $('#assigned_date').val()
        };
        const method = id ? 'PUT' : 'POST';
        const url = id ? `${apiBase}/number/${id}` : `${apiBase}/number`;
        fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        }).then(() => {
            loadNumbers();
            resetForm();
        });
    });
    
    // Edit number
    window.editNumber = function(id) {
        fetch(`${apiBase}/number/${id}`)
            .then(response => response.json())
            .then(data => {
                $('#number-id').val(data.id);
                $('#did').val(data.did);
                $('#status').val(data.status).trigger('change');
                $('#carrier').val(data.carrier);
                $('#pool').val(data.pool);
                $('#assigned_length').val(data.assigned_length);
                $('#assigned_reference_id').val(data.assigned_reference_id);
                $('#assigned_date').val(data.assigned_date ? data.assigned_date.split('T')[0] : '');
            });
    };
    
    // Delete number
    window.deleteNumber = function(id) {
        if (confirm('Delete this number?')) {
            fetch(`${apiBase}/number/${id}`, { method: 'DELETE' })
                .then(() => loadNumbers());
        }
    };
    
    // Bulk upload
    $('#bulk-upload-form').submit(function(e) {
        e.preventDefault();
        const formData = new FormData();
        formData.append('file', $('#csv-file')[0].files[0]);
        fetch(`${apiBase}/number/bulk`, { // Assume bulk endpoint exists
            method: 'POST',
            body: formData
        }).then(() => {
            loadNumbers();
            $('#csv-file').val('');
        });
    });
    
    // Cancel edit
    $('#cancel-edit').click(resetForm);
    
    function resetForm() {
        $('#number-form')[0].reset();
        $('#number-id').val('');
        $('#number-form').removeClass('status-assigned');
    }
    
    // Initial load
    loadCarriers();
    loadNumbers();
});