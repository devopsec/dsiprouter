let settingsData = {};

// Load settings on page load
document.addEventListener('DOMContentLoaded', function() {
  loadSettings();
});

function loadSettings() {
  fetch('/api/v1/settings', {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    }
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      showMessage('Error loading settings: ' + data.msg, 'error');
      return;
    }
    
    settingsData = data.data && data.data.length > 0 ? data.data[0] : {};
    renderSettingsTable();
  })
  .catch(error => {
    showMessage('Error: ' + error.message, 'error');
  });
}

function renderSettingsTable() {
  const tbody = document.getElementById('settingsTableBody');
  tbody.innerHTML = '';
  
  // Sort keys alphabetically
  const keys = Object.keys(settingsData).sort();
  
  keys.forEach(key => {
    const value = settingsData[key];
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${escapeHtml(key)}</td>
      <td>
        <input type="text" class="setting-value" data-key="${key}" value="${escapeHtml(String(value || ''))}" />
      </td>
      <td>
        <div class="action-buttons">
          <button onclick="updateSettingValue('${key}')" class="btn btn-primary">Save</button>
          <button onclick="deleteSetting('${key}')" class="btn btn-danger">
          <span class="glyphicon glyphicon-trash"></span>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}

function addNewSetting() {
  const key = document.getElementById('newSettingKey').value.trim();
  const value = document.getElementById('newSettingValue').value.trim();
  
  if (!key) {
    showMessage('Please enter a setting key', 'error');
    return;
  }
  
  if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(key)) {
    showMessage('Invalid key format. Key must start with a letter or underscore and contain only letters, numbers, and underscores.', 'error');
    return;
  }
  
  fetch('/api/v1/settings', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ key: key, value: value })
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      showMessage('Error: ' + data.msg, 'error');
      return;
    }
    
    showMessage('Setting added successfully', 'success');
    document.getElementById('newSettingKey').value = '';
    document.getElementById('newSettingValue').value = '';
    loadSettings();
  })
  .catch(error => {
    showMessage('Error: ' + error.message, 'error');
  });
}

function updateSettingValue(key) {
  const inputElement = document.querySelector(`input[data-key="${key}"]`);
  if (!inputElement) return;
  
  const newValue = inputElement.value;
  
  fetch(`/api/v1/settings/${key}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ value: newValue })
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      showMessage('Error: ' + data.msg, 'error');
      return;
    }
    
    showMessage('Setting updated successfully', 'success');
    loadSettings();
  })
  .catch(error => {
    showMessage('Error: ' + error.message, 'error');
  });
}

function deleteSetting(key) {
  if (!confirm(`Are you sure you want to delete the setting "${key}"?`)) {
    return;
  }
  
  fetch(`/api/v1/settings/${key}`, {
    method: 'DELETE',
    headers: {
      'Accept': 'application/json',
    }
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      showMessage('Error: ' + data.msg, 'error');
      return;
    }
    
    showMessage('Setting deleted successfully', 'success');
    loadSettings();
  })
  .catch(error => {
    showMessage('Error: ' + error.message, 'error');
  });
}

function showMessage(message, type) {
  const container = document.getElementById('messageContainer');
  const alertDiv = document.createElement('div');
  alertDiv.className = `alert ${type}`;
  alertDiv.textContent = message;
  container.appendChild(alertDiv);
  
  // Auto-remove message after 5 seconds
  setTimeout(() => {
    alertDiv.remove();
  }, 5000);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}