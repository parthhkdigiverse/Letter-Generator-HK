import React, { useState, useEffect } from 'react';
import AdminPanel from './AdminPanel';

const App = () => {
  const [prompts, setPrompts] = useState([]);
  const [chats, setChats] = useState({});
  const [activeTab, setActiveTab] = useState('');
  const [loading, setLoading] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);

  useEffect(() => {
    fetchPrompts();
  }, []);

  const fetchPrompts = async () => {
    try {
      const res = await fetch('/api/prompts');
      const data = await res.json();
      setPrompts(data);
      if (data.length > 0) {
        // Initialize chats and active tab if not set
        const newChats = {};
        data.forEach(p => {
          newChats[p.letter_type] = { input: '', output: '' };
        });
        setChats(newChats);
        setActiveTab(data[0].letter_type);
      }
    } catch (err) {
      console.error("Fetch prompts error:", err);
    }
  };

  const handleSend = async () => {
    if (!chats[activeTab]?.input) return;
    setLoading(true);
    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          letter_type: activeTab,
          description: chats[activeTab].input
        }),
      });
      if (res.ok) {
          const data = await res.json();
          if (data.error) {
            alert("Error from backend: " + data.error);
            return;
          }
          setChats(prev => ({
            ...prev,
            [activeTab]: { ...prev[activeTab], output: data.content }
          }));
      } else {
          let errorMsg = 'Unknown error';
          try {
              const data = await res.json();
              errorMsg = data.detail || JSON.stringify(data);
          } catch (e) {
              const text = await res.text();
              errorMsg = `Server error (${res.status}): ${text.slice(0, 100)}...`;
          }
          alert("Failed to generate: " + errorMsg);
      }
    } catch (err) {
      alert("Failed to connect to backend: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  if (showAdmin) {
    return <AdminPanel onBack={() => { setShowAdmin(false); fetchPrompts(); }} />;
  }

  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: 'sans-serif' }}>
      {/* Sidebar */}
      <div style={{ width: '250px', background: '#1a1a1b', color: '#fff', padding: '20px', display: 'flex', flexDirection: 'column' }}>
        <h2 style={{ fontSize: '1.2rem', marginBottom: '20px' }}>Letter Generator</h2>
        
        <div style={{ flex: 1 }}>
          {prompts.map(p => (
            <div 
              key={p.letter_type}
              onClick={() => setActiveTab(p.letter_type)}
              style={{ 
                padding: '12px', cursor: 'pointer', borderRadius: '4px', marginTop: '10px',
                background: activeTab === p.letter_type ? '#3d3d3d' : 'transparent',
                borderLeft: activeTab === p.letter_type ? '4px solid #007bff' : 'none'
              }}
            >
              {p.letter_type.charAt(0).toUpperCase() + p.letter_type.slice(1)} Letter
            </div>
          ))}
        </div>

        <button 
          onClick={() => setShowAdmin(true)}
          style={{ padding: '10px', background: '#444', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', marginTop: '20px' }}
        >
          Admin Panel
        </button>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '20px' }}>
        {activeTab ? (
          <>
            <div style={{ flex: 1, background: '#fff', borderRadius: '8px', padding: '20px', overflowY: 'auto', border: '1px solid #ddd' }}>
              <h3>{activeTab.toUpperCase()} Letter Output</h3>
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>
                {chats[activeTab]?.output || "Awaiting details..."}
              </div>
            </div>

            {/* Input Area */}
            <div style={{ marginTop: '20px' }}>
              <textarea 
                style={{ width: '100%', height: '100px', padding: '10px', borderRadius: '4px', border: '1px solid #ccc', fontSize: '1rem' }}
                placeholder={`Enter details for ${activeTab} letter...`}
                value={chats[activeTab]?.input || ''}
                onChange={(e) => setChats({...chats, [activeTab]: {...chats[activeTab], input: e.target.value}})}
              />
              <button 
                onClick={handleSend}
                disabled={loading}
                style={{ 
                  width: '100%', padding: '12px', background: '#007bff', color: '#fff', 
                  border: 'none', borderRadius: '4px', cursor: loading ? 'not-allowed' : 'pointer', 
                  marginTop: '10px', fontSize: '1rem', fontWeight: 'bold' 
                }}
              >
                {loading ? 'Generating...' : 'Generate Content'}
              </button>
            </div>
          </>
        ) : (
          <div style={{ textAlign: 'center', marginTop: '100px' }}>
            <h2>No letters configured.</h2>
            <p>Go to Admin Panel to add letter types.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default App;
