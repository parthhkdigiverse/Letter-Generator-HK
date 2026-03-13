import React, { useState, useEffect } from 'react';

const AdminPanel = ({ onBack }) => {
  const [prompts, setPrompts] = useState([]);
  const [password, setPassword] = useState('');
  const [isAuthorized, setIsAuthorized] = useState(false);
  const [newType, setNewType] = useState('');
  const [newPrompt, setNewPrompt] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthorized) {
      fetchPrompts();
    }
  }, [isAuthorized]);

  const fetchPrompts = async () => {
    try {
      const res = await fetch('/api/prompts');
      const data = await res.json();
      setPrompts(data);
    } catch (err) {
      console.error("Error fetching prompts:", err);
    }
  };

  const handleLogin = (e) => {
    e.preventDefault();
    if (password === 'admin123') {
      setIsAuthorized(true);
    } else {
      alert('Invalid Password');
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!newType || !newPrompt) return;
    setLoading(true);
    try {
      const res = await fetch('/api/prompts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          letter_type: newType.toLowerCase(),
          prompt_text: newPrompt,
          password: password
        })
      });
      if (res.ok) {
        alert('Saved successfully!');
        setNewType('');
        setNewPrompt('');
        fetchPrompts();
      } else {
          const data = await res.json();
          alert('Error: ' + data.detail);
      }
    } catch (err) {
      alert('Failed to save');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (type) => {
    if (!window.confirm(`Delete prompt for ${type}?`)) return;
    try {
      await fetch(`/api/prompts/${type}?password=${password}`, {
        method: 'DELETE'
      });
      fetchPrompts();
    } catch (err) {
      alert('Failed to delete');
    }
  };

  if (!isAuthorized) {
    return (
      <div style={{ padding: '50px', textAlign: 'center' }}>
        <h2>Admin Login</h2>
        <form onSubmit={handleLogin}>
          <input 
            type="password" 
            placeholder="Enter Admin Password" 
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ padding: '10px', borderRadius: '4px', border: '1px solid #ccc', marginRight: '10px' }}
          />
          <button type="submit" style={{ padding: '10px 20px', background: '#007bff', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
            Login
          </button>
        </form>
        <button onClick={onBack} style={{ marginTop: '20px', background: 'none', border: 'none', color: '#007bff', cursor: 'pointer' }}>
          Back to Generator
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Manage Prompts</h2>
        <button onClick={onBack} style={{ padding: '8px 16px', background: '#6c757d', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          Back to Generator
        </button>
      </div>

      <div style={{ background: '#f8f9fa', padding: '20px', borderRadius: '8px', marginBottom: '30px' }}>
        <h3>Add / Update Prompt</h3>
        <form onSubmit={handleSave}>
          <input 
            type="text" 
            placeholder="Letter Type (e.g. resignation)" 
            value={newType}
            onChange={(e) => setNewType(e.target.value)}
            style={{ width: '100%', padding: '10px', marginBottom: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
          />
          <textarea 
            placeholder="System Prompt / Instructions..." 
            value={newPrompt}
            onChange={(e) => setNewPrompt(e.target.value)}
            style={{ width: '100%', height: '100px', padding: '10px', marginBottom: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
          />
          <button type="submit" disabled={loading} style={{ width: '100%', padding: '12px', background: '#28a745', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
            {loading ? 'Saving...' : 'Save Prompt'}
          </button>
        </form>
      </div>

      <h3>Existing Prompts</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>
            <th style={{ padding: '12px' }}>Type</th>
            <th style={{ padding: '12px' }}>Action</th>
          </tr>
        </thead>
        <tbody>
          {prompts.map(p => (
            <tr key={p.letter_type} style={{ borderBottom: '1px solid #dee2e6' }}>
              <td style={{ padding: '12px' }}>{p.letter_type.toUpperCase()}</td>
              <td style={{ padding: '12px' }}>
                <button onClick={() => {setNewType(p.letter_type); setNewPrompt(p.prompt_text);}} style={{ marginRight: '10px', color: '#007bff', background: 'none', border: 'none', cursor: 'pointer' }}>Edit</button>
                <button onClick={() => handleDelete(p.letter_type)} style={{ color: '#dc3545', background: 'none', border: 'none', cursor: 'pointer' }}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AdminPanel;
