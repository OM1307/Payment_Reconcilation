import { useState, useRef } from 'react';
import { UploadCloud, FileText, CheckCircle, AlertTriangle, RefreshCw, Download, Server, Search } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './index.css';

const formatINR = (v) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(v);

function App() {
  const [platformFile, setPlatformFile] = useState(null);
  const [bankFile, setBankFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [results, setResults] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);

  const platformInputRef = useRef(null);
  const bankInputRef = useRef(null);

  const handleGenerateData = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const response = await fetch('https://payment-reconcilation.onrender.com/api/generate');
      if (!response.ok) throw new Error('Failed to generate data');
      const data = await response.json();
      
      // Create downloadable blobs
      const downloadCSV = (jsonData, filename) => {
        const headers = Array.from(new Set(jsonData.flatMap(row => Object.keys(row))));
        const csvRows = [
          headers.join(','),
          ...jsonData.map(row => headers.map(header => JSON.stringify(row[header] || '')).join(','))
        ];
        const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(url);
      };

      downloadCSV(data.platform_data, 'platform_data.csv');
      downloadCSV(data.bank_data, 'bank_data.csv');
      
    } catch (err) {
      setError(err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleReconcile = async () => {
    if (!platformFile || !bankFile) {
      setError("Please upload both Platform and Bank datasets.");
      return;
    }
    
    setIsUploading(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('platform_file', platformFile);
    formData.append('bank_file', bankFile);

    try {
      const response = await fetch('https://payment-reconcilation.onrender.com/api/reconcile', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Reconciliation failed');
      }
      
      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <>
      <div className="glow-blob blob-1"></div>
      <div className="glow-blob blob-2"></div>
      
      <div className="app-container">
        <header className="header">
          <h1>Reconcilify</h1>
          <p>Intelligent Payment Reconciliation Engine</p>
        </header>

        <section className="assumptions-banner glass-panel">
          <h3>Implementation Assumptions</h3>
          <ul>
            <li>Platform transactions are instantly recorded; bank settlements have a 1-2 day delay.</li>
            <li>A month-end cutoff is applied (e.g. November 2023). Transactions settling in December are flagged.</li>
            <li>Grouped transactions (like split payments) use a common identifier or sum up to a single settlement.</li>
          </ul>
        </section>

        {!results ? (
          <div className="glass-panel" style={{ padding: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
              <h2>1. Provide Datasets</h2>
              <button 
                className="btn btn-secondary" 
                onClick={handleGenerateData}
                disabled={isGenerating}
              >
                {isGenerating ? <RefreshCw className="spinner" size={18} /> : <Server size={18} />}
                Generate Test Data
              </button>
            </div>

            {error && (
              <div style={{ background: 'var(--danger-bg)', color: 'var(--danger)', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', border: '1px solid var(--danger)' }}>
                {error}
              </div>
            )}

            <div className="grid-2">
              <div 
                className={`upload-zone ${platformFile ? 'drag-active' : ''}`}
                onClick={() => platformInputRef.current?.click()}
              >
                <input 
                  type="file" 
                  accept=".csv" 
                  ref={platformInputRef} 
                  style={{ display: 'none' }} 
                  onChange={(e) => setPlatformFile(e.target.files[0])}
                />
                <UploadCloud className="upload-icon" />
                <h3>Platform Dataset</h3>
                <p>{platformFile ? platformFile.name : 'Click or drag CSV here'}</p>
                {platformFile && <CheckCircle color="var(--success)" size={20} style={{ marginTop: '1rem' }} />}
              </div>

              <div 
                className={`upload-zone ${bankFile ? 'drag-active' : ''}`}
                onClick={() => bankInputRef.current?.click()}
              >
                <input 
                  type="file" 
                  accept=".csv" 
                  ref={bankInputRef} 
                  style={{ display: 'none' }} 
                  onChange={(e) => setBankFile(e.target.files[0])}
                />
                <UploadCloud className="upload-icon" />
                <h3>Bank Settlement Dataset</h3>
                <p>{bankFile ? bankFile.name : 'Click or drag CSV here'}</p>
                {bankFile && <CheckCircle color="var(--success)" size={20} style={{ marginTop: '1rem' }} />}
              </div>
            </div>

            <div style={{ textAlign: 'center', marginTop: '2.5rem' }}>
              <button 
                className="btn btn-primary" 
                onClick={handleReconcile}
                disabled={!platformFile || !bankFile || isUploading}
                style={{ padding: '1rem 3rem', fontSize: '1.1rem' }}
              >
                {isUploading ? <RefreshCw className="spinner" /> : <FileText />}
                Run Reconciliation
              </button>
            </div>
          </div>
        ) : (
          <Dashboard results={results} onReset={() => setResults(null)} />
        )}
      </div>
    </>
  );
}

function Dashboard({ results, onReset }) {
  const [searchTerm, setSearchTerm] = useState('');
  const { summary, gaps } = results;

  const renderGapTable = (title, items, type, columns) => {
    if (!items || items.length === 0) return null;
    
    const filteredItems = items.filter(item => {
      if (!searchTerm) return true;
      return Object.values(item).some(val => 
        String(val).toLowerCase().includes(searchTerm.toLowerCase())
      );
    });

    if (filteredItems.length === 0 && searchTerm) return null;
    
    let badgeClass = 'badge-warning';
    if (type === 'cross_month') badgeClass = 'badge-info';
    if (type === 'duplicates' || type === 'unmatched_refunds') badgeClass = 'badge-danger';

    return (
      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertTriangle size={20} color="var(--warning)" />
            {title}
          </h3>
          <span className={`badge ${badgeClass}`}>{filteredItems.length} Issues</span>
        </div>
        
        <div className="table-container">
          <table>
            <thead>
              <tr>
                {columns.map(col => <th key={col.key}>{col.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((item, idx) => (
                <tr key={idx}>
                  {columns.map(col => (
                    <td key={col.key}>
                      {col.format ? col.format(item[col.key]) : item[col.key]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const pieData = [
    { name: 'Cross Month', value: gaps.cross_month.length },
    { name: 'Rounding', value: gaps.rounding_differences.length },
    { name: 'Duplicates', value: gaps.duplicates.length },
    { name: 'Unmatched Refunds', value: gaps.unmatched_refunds.length },
    { name: 'Missing in Bank', value: gaps.missing_in_bank.length },
    { name: 'Missing in Platform', value: gaps.missing_in_platform.length }
  ].filter(d => d.value > 0);

  const COLORS = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];

  return (
    <div style={{ animation: 'fadeIn 0.5s ease-in-out' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h2>Reconciliation Dashboard</h2>
        <button className="btn btn-secondary" onClick={onReset}>
          <RefreshCw size={16} /> New Reconciliation
        </button>
      </div>

      <div className="grid-2" style={{ marginBottom: '2rem' }}>
        <div className="glass-panel" style={{ padding: '1.5rem', textAlign: 'center' }}>
          <h4 style={{ color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '0.85rem' }}>Match Rate</h4>
          <div style={{ fontSize: '3rem', fontWeight: '700', color: summary.match_rate_percentage > 95 ? 'var(--success)' : 'var(--warning)' }}>
            {summary.match_rate_percentage}%
          </div>
        </div>
        
        <div className="glass-panel" style={{ padding: '1.5rem', textAlign: 'center' }}>
          <h4 style={{ color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '0.85rem' }}>Total Discrepancies Found</h4>
          <div style={{ fontSize: '3rem', fontWeight: '700', color: summary.total_gaps_found > 0 ? 'var(--danger)' : 'var(--success)' }}>
            {summary.total_gaps_found}
          </div>
        </div>
      </div>

      {summary.total_gaps_found > 0 && (
        <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '2rem', height: '400px' }}>
          <h3 style={{ textAlign: 'center', marginBottom: '1rem' }}>Discrepancy Breakdown</h3>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={110}
                paddingAngle={5}
                dataKey="value"
                stroke="rgba(255,255,255,0.1)"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip 
                formatter={(value, name) => [`${value} Issues`, name]} 
                contentStyle={{ background: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                itemStyle={{ color: '#fff' }}
              />
              <Legend wrapperStyle={{ paddingTop: '20px', paddingBottom: '20px' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {summary.total_gaps_found > 0 && (
        <div className="glass-panel" style={{ padding: '1rem 1.5rem', marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Search size={20} color="var(--text-muted)" />
          <input 
            type="text" 
            placeholder="Search discrepancies by Transaction ID, Amount, Date..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: '100%', background: 'transparent', border: 'none', color: 'var(--text)', outline: 'none', fontSize: '1rem' }}
          />
        </div>
      )}

      {renderGapTable(
        'Transactions Settled Following Month', 
        gaps.cross_month, 
        'cross_month',
        [
          { key: 'transaction_id', label: 'Transaction ID' },
          { key: 'platform_date', label: 'Platform Date' },
          { key: 'bank_settlement_date', label: 'Bank Settlement Date' },
          { key: 'amount', label: 'Amount', format: (v) => formatINR(v) }
        ]
      )}

      {renderGapTable(
        'Rounding Differences (Summed Groups)', 
        gaps.rounding_differences, 
        'rounding',
        [
          { key: 'transaction_id', label: 'Transaction / Group ID' },
          { key: 'platform_amount', label: 'Platform Amount', format: (v) => formatINR(v) },
          { key: 'bank_amount', label: 'Bank Amount', format: (v) => formatINR(v) },
          { key: 'difference', label: 'Difference', format: (v) => formatINR(v) }
        ]
      )}

      {renderGapTable(
        'Duplicate Entries in Bank Data', 
        gaps.duplicates, 
        'duplicates',
        [
          { key: 'bank_ref', label: 'Bank Reference' },
          { key: 'transaction_id', label: 'Transaction ID' },
          { key: 'settlement_date', label: 'Settlement Date' },
          { key: 'amount', label: 'Amount', format: (v) => formatINR(v) }
        ]
      )}

      {renderGapTable(
        'Unmatched Refunds', 
        gaps.unmatched_refunds, 
        'unmatched_refunds',
        [
          { key: 'transaction_id', label: 'Refund Transaction ID' },
          { key: 'date', label: 'Platform Date' },
          { key: 'amount', label: 'Amount', format: (v) => formatINR(v) }
        ]
      )}

      {renderGapTable(
        'Other Missing in Bank', 
        gaps.missing_in_bank, 
        'missing',
        [
          { key: 'transaction_id', label: 'Transaction ID' },
          { key: 'date', label: 'Platform Date' },
          { key: 'amount', label: 'Amount', format: (v) => formatINR(v) }
        ]
      )}
      
      {renderGapTable(
        'Other Missing in Platform (Bank only)', 
        gaps.missing_in_platform, 
        'missing',
        [
          { key: 'bank_ref', label: 'Bank Reference' },
          { key: 'transaction_id', label: 'Transaction ID' },
          { key: 'date', label: 'Settlement Date' },
          { key: 'amount', label: 'Amount', format: (v) => formatINR(v) }
        ]
      )}

    </div>
  );
}

export default App;
