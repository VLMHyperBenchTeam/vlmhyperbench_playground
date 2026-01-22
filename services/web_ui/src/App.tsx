import { useState, useEffect } from 'react'

interface Experiment {
  id: string;
  name: string;
  status: string;
  created_at: string;
}

function App() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [newExpName, setNewExpName] = useState("");
  const [configContent, setConfigContent] = useState("");

  const fetchExperiments = () => {
    fetch('/api/experiments')
      .then(res => res.json())
      .then(data => {
        setExperiments(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch experiments:", err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchExperiments();
  }, []);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setConfigContent(ev.target?.result as string);
      };
      reader.readAsText(file);
    }
  };

  const createExperiment = async () => {
    try {
      let config = {};
      try {
        config = JSON.parse(configContent);
      } catch (e) {
        // Если это не JSON, попробуем использовать как имя запуска
        config = { run_name: configContent.trim() };
      }

      const response = await fetch('/api/experiments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newExpName,
          config: config
        })
      });

      if (response.ok) {
        setShowModal(false);
        setNewExpName("");
        setConfigContent("");
        fetchExperiments();
      }
    } catch (err) {
      console.error("Failed to create experiment:", err);
    }
  };

  return (
    <div className="min-h-screen bg-vscode-bg text-vscode-text flex flex-col">
      {/* Header */}
      <header className="h-12 border-b border-vscode-border flex items-center px-4 bg-vscode-sidebar">
        <h1 className="text-sm font-bold tracking-wider uppercase">VLMHyperBench Dashboard</h1>
      </header>

      <div className="flex flex-1">
        {/* Sidebar */}
        <aside className="w-64 bg-vscode-sidebar border-r border-vscode-border p-4">
          <button
            onClick={() => setShowModal(true)}
            className="w-full bg-vscode-accent text-white py-2 px-4 rounded text-sm font-medium hover:bg-blue-600 transition-colors"
          >
            New Experiment
          </button>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">
          <h2 className="text-xl font-semibold mb-6">Experiments</h2>
          
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <span className="animate-pulse">Loading core systems...</span>
            </div>
          ) : (
            <div className="grid gap-4">
              {experiments.length === 0 ? (
                <div className="border border-dashed border-vscode-border p-8 text-center rounded">
                  No experiments found. Start your first VLM benchmark!
                </div>
              ) : (
                experiments.map(exp => (
                  <div key={exp.id} className="bg-vscode-active p-4 rounded border border-vscode-border hover:border-vscode-accent transition-colors">
                    <div className="flex justify-between items-center">
                      <div>
                        <h3 className="font-bold">{exp.name}</h3>
                        <p className="text-xs text-vscode-text/60 mt-1">{new Date(exp.created_at).toLocaleString()}</p>
                      </div>
                      <span className={`px-2 py-1 rounded text-xs font-mono ${
                        exp.status === 'COMPLETED' ? 'bg-green-900 text-green-300' : 
                        exp.status === 'RUNNING' ? 'bg-blue-900 text-blue-300' : 'bg-vscode-border'
                      }`}>
                        {exp.status}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </main>
      </div>

      {/* Footer / Status Bar */}
      <footer className="h-6 bg-vscode-accent text-white flex items-center px-2 text-[10px] uppercase tracking-tighter">
        <div className="flex gap-4">
          <span>Ready</span>
          <span>Docker: Connected</span>
          <span>GPU: 1 Active</span>
        </div>
      </footer>

      {/* Modal Form */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-vscode-sidebar border border-vscode-border rounded-lg w-full max-w-md p-6 shadow-2xl">
            <h2 className="text-lg font-bold mb-4">Create New Experiment</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-xs uppercase opacity-60 mb-1">Experiment Name</label>
                <input
                  type="text"
                  value={newExpName}
                  onChange={(e) => setNewExpName(e.target.value)}
                  className="w-full bg-vscode-bg border border-vscode-border rounded px-3 py-2 text-sm focus:border-vscode-accent outline-none"
                  placeholder="e.g. SNILS Qwen Test"
                />
              </div>

              <div>
                <label className="block text-xs uppercase opacity-60 mb-1">Config File (JSON) or Run Name</label>
                <input
                  type="file"
                  onChange={handleFileUpload}
                  className="w-full text-xs text-vscode-text file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-vscode-active file:text-vscode-text hover:file:bg-vscode-border cursor-pointer"
                />
                <textarea
                  value={configContent}
                  onChange={(e) => setConfigContent(e.target.value)}
                  className="w-full h-32 mt-2 bg-vscode-bg border border-vscode-border rounded px-3 py-2 text-xs font-mono focus:border-vscode-accent outline-none"
                  placeholder='{"run_name": "qwen_snils_extraction"}'
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm hover:bg-vscode-active rounded"
              >
                Cancel
              </button>
              <button
                onClick={createExperiment}
                className="bg-vscode-accent text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-600"
              >
                Launch
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
