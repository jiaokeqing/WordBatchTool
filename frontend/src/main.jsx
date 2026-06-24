import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Download, FileUp, FileText, FolderInput, Play, RefreshCw, UploadCloud } from 'lucide-react';
import './styles.css';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const defaultTemplate = {
  mode: 'builtin',
  builtin: {
    preset: 'paper-photo',
    title_font: '方正小标宋_GBK',
    title_size: 22,
    body_font: '仿宋_GB2312',
    body_size: 16,
    heading_font: '黑体',
    heading_size: 16,
    second_heading_font: '楷体_GB2312',
    third_heading_font: '仿宋_GB2312',
    latin_font: 'Times New Roman',
    line_spacing_pt: 28,
    space_before_pt: 0,
    space_after_pt: 0,
    first_line_indent_chars: 2,
    margin_top_cm: 3.7,
    margin_bottom_cm: 3.5,
    margin_left_cm: 2.8,
    margin_right_cm: 2.6,
    normalize_spacing: true,
    normalize_parentheses: true,
  },
};

function App() {
  const [files, setFiles] = useState([]);
  const [sampleTemplate, setSampleTemplate] = useState(null);
  const [serverDirectory, setServerDirectory] = useState('');
  const [exportPdf, setExportPdf] = useState(true);
  const [template, setTemplate] = useState(defaultTemplate);
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  const selectedCount = useMemo(() => files.length + (serverDirectory.trim() ? 1 : 0), [files, serverDirectory]);

  async function loadJobs() {
    const response = await fetch(`${API_BASE}/api/jobs`);
    const data = await response.json();
    setJobs(data);
    if (selectedJob) {
      const detail = await fetch(`${API_BASE}/api/jobs/${selectedJob.id}`).then((res) => res.json());
      setSelectedJob(detail);
    }
  }

  useEffect(() => {
    loadJobs().catch(() => {});
    const timer = setInterval(() => loadJobs().catch(() => {}), 2500);
    return () => clearInterval(timer);
  }, []);

  async function createJob(event) {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    try {
      const data = new FormData();
      files.forEach((file) => data.append('files', file, file.webkitRelativePath || file.name));
      if (sampleTemplate) {
        data.append('sample_template', sampleTemplate);
      }
      if (serverDirectory.trim()) {
        data.append('server_directory', serverDirectory.trim());
      }
      data.append('export_pdf', String(exportPdf));
      data.append('template_config', JSON.stringify(sampleTemplate ? { ...template, mode: 'sample' } : template));

      const response = await fetch(`${API_BASE}/api/jobs`, { method: 'POST', body: data });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        setMessage(error.detail || '创建任务失败');
        return;
      }
      const job = await response.json();
      setFiles([]);
      setSampleTemplate(null);
      setServerDirectory('');
      setSelectedJob(job);
      await loadJobs();
    } catch (error) {
      setMessage(`创建任务失败：${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function openJob(job) {
    const detail = await fetch(`${API_BASE}/api/jobs/${job.id}`).then((res) => res.json());
    setSelectedJob(detail);
  }

  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <h1>批量 Word 格式处理</h1>
          <p>局域网批量排版、PDF 导出和 ZIP 结果下载</p>
        </div>
        <button className="iconButton" onClick={loadJobs} title="刷新任务">
          <RefreshCw size={18} />
        </button>
      </section>

      <section className="workspace">
        <form className="panel" onSubmit={createJob}>
          <div className="panelHeader">
            <UploadCloud size={20} />
            <h2>创建任务</h2>
          </div>

          <section className="formSection">
            <div className="sectionTitle">文件来源</div>
            <div className="uploadGrid">
              <label className="uploadTile">
                <input type="file" accept=".doc,.docx" multiple onChange={(event) => setFiles(Array.from(event.target.files || []))} />
                <FileUp size={24} />
                <strong>选择 Word 文件</strong>
                <span>支持单个或多个 .doc/.docx</span>
              </label>
              <label className="uploadTile">
                <input
                  type="file"
                  accept=".doc,.docx"
                  multiple
                  webkitdirectory=""
                  onChange={(event) => setFiles(Array.from(event.target.files || []))}
                />
                <FolderInput size={24} />
                <strong>选择文件夹</strong>
                <span>保留文件夹内相对路径</span>
              </label>
            </div>
            <div className="selectionBar">
              <UploadCloud size={16} />
              <span>{files.length ? `已选择 ${files.length} 个文件` : '尚未选择文件'}</span>
            </div>
          </section>

          <section className="formSection compactSection">
            <div className="sectionTitle">可选来源</div>
            <label className="field">
              <span>服务器共享目录</span>
              <input value={serverDirectory} onChange={(event) => setServerDirectory(event.target.value)} placeholder="例如 D:\\共享文档\\待处理" />
            </label>

            <label className="field">
              <span>样本文档模板</span>
              <input type="file" accept=".docx" onChange={(event) => setSampleTemplate(event.target.files?.[0] || null)} />
            </label>
          </section>

          <section className="formSection">
            <div className="sectionHeader">
              <div className="sectionTitle">格式规则</div>
              <button type="button" className="secondary" onClick={() => setTemplate(defaultTemplate)}>
                套用图片格式要求
              </button>
            </div>

            <div className="ruleNote">抬头和各级标题顶格，普通正文首行缩进，空白段落自动删除。</div>

            <div className="grid">
              <TextInput label="标题字体" value={template.builtin.title_font} onChange={(value) => updateTemplate(setTemplate, 'title_font', value)} />
              <NumberInput label="标题字号" value={template.builtin.title_size} onChange={(value) => updateTemplate(setTemplate, 'title_size', value)} />
              <TextInput label="正文字体" value={template.builtin.body_font} onChange={(value) => updateTemplate(setTemplate, 'body_font', value)} />
              <NumberInput label="正文字号" value={template.builtin.body_size} onChange={(value) => updateTemplate(setTemplate, 'body_size', value)} />
              <TextInput label="一级标题字体" value={template.builtin.heading_font} onChange={(value) => updateTemplate(setTemplate, 'heading_font', value)} />
              <TextInput label="二级标题字体" value={template.builtin.second_heading_font} onChange={(value) => updateTemplate(setTemplate, 'second_heading_font', value)} />
              <TextInput label="三级标题字体" value={template.builtin.third_heading_font} onChange={(value) => updateTemplate(setTemplate, 'third_heading_font', value)} />
              <TextInput label="英文字体" value={template.builtin.latin_font} onChange={(value) => updateTemplate(setTemplate, 'latin_font', value)} />
              <NumberInput label="标题字号" value={template.builtin.heading_size} onChange={(value) => updateTemplate(setTemplate, 'heading_size', value)} />
              <NumberInput label="行距 磅" step="1" value={template.builtin.line_spacing_pt} onChange={(value) => updateTemplate(setTemplate, 'line_spacing_pt', value)} />
              <NumberInput
                label="正文首行缩进 字符"
                step="1"
                value={template.builtin.first_line_indent_chars}
                onChange={(value) => updateTemplate(setTemplate, 'first_line_indent_chars', value)}
              />
              <NumberInput label="上边距 cm" step="0.1" value={template.builtin.margin_top_cm} onChange={(value) => updateTemplate(setTemplate, 'margin_top_cm', value)} />
              <NumberInput label="下边距 cm" step="0.1" value={template.builtin.margin_bottom_cm} onChange={(value) => updateTemplate(setTemplate, 'margin_bottom_cm', value)} />
              <NumberInput label="左边距 cm" step="0.1" value={template.builtin.margin_left_cm} onChange={(value) => updateTemplate(setTemplate, 'margin_left_cm', value)} />
              <NumberInput label="右边距 cm" step="0.1" value={template.builtin.margin_right_cm} onChange={(value) => updateTemplate(setTemplate, 'margin_right_cm', value)} />
            </div>
          </section>

          <section className="optionsRow">
            <label className="check">
              <input
                type="checkbox"
                checked={template.builtin.normalize_parentheses}
                onChange={(event) => updateTemplate(setTemplate, 'normalize_parentheses', event.target.checked)}
              />
              <span>中文括号归一</span>
            </label>

            <label className="check">
              <input
                type="checkbox"
                checked={template.builtin.normalize_spacing}
                onChange={(event) => updateTemplate(setTemplate, 'normalize_spacing', event.target.checked)}
              />
              <span>去除多余空格</span>
            </label>

            <label className="check">
              <input type="checkbox" checked={exportPdf} onChange={(event) => setExportPdf(event.target.checked)} />
              <span>导出 PDF</span>
            </label>
          </section>

          {message && <div className="error">{message}</div>}

          <button className="primary" disabled={busy || selectedCount === 0}>
            <Play size={17} />
            <span>{busy ? '提交中' : '开始处理'}</span>
          </button>
        </form>

        <section className="panel">
          <div className="panelHeader">
            <FileText size={20} />
            <h2>任务列表</h2>
          </div>
          <div className="jobList">
            {jobs.map((job) => (
              <button key={job.id} className="jobRow" onClick={() => openJob(job)}>
                <span className={`status ${job.status}`}>{statusLabel(job.status)}</span>
                <strong>{job.id.slice(0, 8)}</strong>
                <span>{job.succeeded_files}/{job.total_files} 成功</span>
                <span>{new Date(job.created_at).toLocaleString()}</span>
              </button>
            ))}
          </div>
        </section>
      </section>

      {selectedJob && (
        <section className="panel detail">
          <div className="detailHeader">
            <div>
              <h2>任务 {selectedJob.id.slice(0, 8)}</h2>
              <p>{statusLabel(selectedJob.status)} · 成功 {selectedJob.succeeded_files} · 失败 {selectedJob.failed_files}</p>
            </div>
            {selectedJob.download_ready && (
              <a className="primary linkButton" href={`${API_BASE}/api/jobs/${selectedJob.id}/download`}>
                <Download size={17} />
                <span>下载 ZIP</span>
              </a>
            )}
          </div>
          <div className="fileTable">
            {(selectedJob.files || []).map((file) => (
              <div className="fileRow" key={file.id}>
                <span className={`status ${file.status}`}>{statusLabel(file.status)}</span>
                <span>{file.relative_path}</span>
                <span>{file.message}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}

function updateTemplate(setTemplate, key, value) {
  setTemplate((current) => ({ ...current, builtin: { ...current.builtin, [key]: value } }));
}

function TextInput({ label, value, onChange }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function NumberInput({ label, value, onChange, step = '1' }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type="number" step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </label>
  );
}

function statusLabel(status) {
  const labels = {
    queued: '排队中',
    running: '处理中',
    succeeded: '已完成',
    partial_failed: '部分失败',
    failed: '失败',
    expired: '已过期',
  };
  return labels[status] || status;
}

createRoot(document.getElementById('root')).render(<App />);
