import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Check,
  Copy,
  Download,
  FileText,
  FileUp,
  FolderInput,
  History,
  Info,
  LayoutDashboard,
  Library,
  Mail,
  MonitorCog,
  Play,
  Plus,
  RefreshCw,
  Save,
  Settings,
  ShieldCheck,
  Trash2,
  UploadCloud,
  X,
} from 'lucide-react';
import './styles.css';
import authorAvatar from './assets/author-avatar.jpg';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const defaultTemplateConfig = {
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

const navItems = [
  { id: 'process', label: '处理任务', icon: LayoutDashboard },
  { id: 'templates', label: '模板库', icon: Library },
  { id: 'history', label: '任务记录', icon: History },
  { id: 'platforms', label: '平台适配', icon: MonitorCog },
  { id: 'settings', label: '设置', icon: Settings },
];

function App() {
  const [activeView, setActiveView] = useState('process');
  const [files, setFiles] = useState([]);
  const [exportPdf, setExportPdf] = useState(true);
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [appInfo, setAppInfo] = useState(null);
  const [platformInfo, setPlatformInfo] = useState(null);
  const [settingsDraft, setSettingsDraft] = useState(null);
  const [updateState, setUpdateState] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [showAvatarModal, setShowAvatarModal] = useState(false);
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);

  const selectedTemplate = templates.find((template) => template.id === selectedTemplateId) || templates.find((template) => template.is_default);
  const selectedCount = useMemo(() => files.length, [files]);

  useEffect(() => {
    boot();
    const timer = setInterval(() => loadJobs().catch(() => {}), 2500);
    return () => clearInterval(timer);
  }, []);

  async function api(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: options.body && !(options.body instanceof FormData) ? { 'Content-Type': 'application/json' } : undefined,
      ...options,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '请求失败');
    }
    return response.json();
  }

  async function refreshAll() {
    await Promise.all([loadTemplates(), loadJobs(), loadAppInfo(), loadPlatformInfo()]);
  }

  async function boot() {
    try {
      await waitForApi();
      await refreshAll();
    } catch (error) {
      setMessage(`本地服务未就绪：${error.message}`);
    }
  }

  async function waitForApi() {
    let lastError = null;
    for (let attempt = 0; attempt < 20; attempt += 1) {
      try {
        await api('/api/health');
        return;
      } catch (error) {
        lastError = error;
        await new Promise((resolve) => setTimeout(resolve, 250));
      }
    }
    throw lastError || new Error('无法连接本地 API');
  }

  async function loadTemplates() {
    const data = await api('/api/templates');
    setTemplates(data);
    setSelectedTemplateId((current) => current || data.find((template) => template.is_default)?.id || data[0]?.id || '');
  }

  async function loadJobs() {
    const data = await api('/api/jobs');
    setJobs(data);
    if (selectedJob) {
      const detail = await api(`/api/jobs/${selectedJob.id}`).catch(() => null);
      if (detail) setSelectedJob(detail);
    }
  }

  async function loadAppInfo() {
    const data = await api('/api/app/info');
    setAppInfo(data);
    setSettingsDraft({
      default_open_dir: data.default_open_dir || '',
      max_files_per_job: data.max_files_per_job,
      retention_hours: data.retention_hours,
      github_repo: data.github_repo,
    });
  }

  async function loadPlatformInfo() {
    setPlatformInfo(await api('/api/platform'));
  }

  function resetFileInputs() {
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (folderInputRef.current) folderInputRef.current.value = '';
  }

  function handleFilesSelected(fileList) {
    setFiles(Array.from(fileList || []));
  }

  function clearSelectedFiles() {
    setFiles([]);
    resetFileInputs();
  }

  function removeSelectedFile(index) {
    setFiles((current) => current.filter((_, itemIndex) => itemIndex !== index));
    resetFileInputs();
  }

  async function createJob(event) {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    try {
      const data = new FormData();
      files.forEach((file) => data.append('files', file, file.webkitRelativePath || file.name));
      if (selectedTemplate?.id) data.append('template_id', selectedTemplate.id);
      data.append('export_pdf', String(exportPdf));

      const response = await fetch(`${API_BASE}/api/jobs`, { method: 'POST', body: data });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        setMessage(error.detail || '创建任务失败');
        return;
      }
      const job = await response.json();
      setFiles([]);
      resetFileInputs();
      await openJob(job);
      await loadJobs();
      setActiveView('history');
    } catch (error) {
      setMessage(`创建任务失败：${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function openJob(job) {
    setSelectedJob(await api(`/api/jobs/${job.id}`));
  }

  async function deleteJob(jobId, event) {
    event?.stopPropagation();
    if (!window.confirm('确定删除这个任务吗？')) return;
    const response = await fetch(`${API_BASE}/api/jobs/${jobId}`, { method: 'DELETE' });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      setMessage(error.detail || '删除任务失败');
      return;
    }
    if (selectedJob?.id === jobId) setSelectedJob(null);
    await loadJobs();
  }

  async function downloadJob(jobId) {
    setMessage('');
    try {
      if (window.pywebview?.api?.save_zip) {
        const result = await window.pywebview.api.save_zip(jobId);
        if (!result.ok) {
          if (!result.cancelled) setMessage(result.message || '下载失败');
          return;
        }
        setMessage(`已保存到：${result.path}`);
        return;
      }
      const response = await fetch(`${API_BASE}/api/jobs/${jobId}/download`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        setMessage(error.detail || '下载失败');
        return;
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${jobId}.zip`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setMessage(`下载失败：${error.message}`);
    }
  }

  async function saveTemplate(template) {
    const payload = { name: template.name, description: template.description, config: template.config };
    try {
      if (template.id && !template.isNew) {
        await api(`/api/templates/${template.id}`, { method: 'PUT', body: JSON.stringify(payload) });
      } else {
        await api('/api/templates', { method: 'POST', body: JSON.stringify(payload) });
      }
      setEditingTemplate(null);
      await loadTemplates();
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function duplicateTemplate(template) {
    try {
      const copy = await api(`/api/templates/${template.id}/duplicate`, { method: 'POST' });
      await loadTemplates();
      setEditingTemplate(copy);
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function deleteTemplate(template) {
    if (!window.confirm(`确定删除“${template.name}”吗？`)) return;
    const response = await fetch(`${API_BASE}/api/templates/${template.id}`, { method: 'DELETE' });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      setMessage(error.detail || '删除模板失败');
      return;
    }
    setEditingTemplate(null);
    await loadTemplates();
  }

  async function setDefaultTemplate(template) {
    try {
      await api(`/api/templates/${template.id}/default`, { method: 'POST' });
      await loadTemplates();
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function saveSettings(event) {
    event.preventDefault();
    try {
      const data = await api('/api/app/settings', { method: 'PUT', body: JSON.stringify(settingsDraft) });
      setAppInfo(data);
      setMessage('设置已保存');
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function checkForUpdates() {
    setUpdateState({ status: 'checking', message: '正在连接 GitHub...' });
    try {
      setUpdateState(await api('/api/app/update-check'));
    } catch (error) {
      setUpdateState({ ok: false, status: 'offline', message: error.message });
    }
  }

  return (
    <main className="appShell">
      <aside className="sidebar">
        <div>
          <div className="brand">
            <div className="brandMark">W</div>
            <div>
              <strong>文档工作台</strong>
              <span>离线批量处理</span>
            </div>
          </div>
          <nav className="navList" aria-label="主导航">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button key={item.id} className={`navItem ${activeView === item.id ? 'active' : ''}`} onClick={() => setActiveView(item.id)}>
                  <Icon size={18} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
        <div className="sideStatus">
          <ShieldCheck size={17} />
          <span>核心功能离线可用</span>
        </div>
      </aside>

      <section className="workbench">
        <header className="topbar">
          <div className="titleBlock">
            <h1>{viewTitle(activeView)}</h1>
            <p>{viewSubtitle(activeView)}</p>
          </div>
          <button className="ghostButton" onClick={refreshAll}>
            <RefreshCw size={17} />
            <span>刷新</span>
          </button>
        </header>

        {message && (
          <div className="notice" role="status">
            <Info size={16} />
            <span>{message}</span>
            <button className="miniIconButton" onClick={() => setMessage('')} title="关闭">
              <X size={14} />
            </button>
          </div>
        )}

        {activeView === 'process' && (
          <ProcessView
            files={files}
            fileInputRef={fileInputRef}
            folderInputRef={folderInputRef}
            handleFilesSelected={handleFilesSelected}
            removeSelectedFile={removeSelectedFile}
            clearSelectedFiles={clearSelectedFiles}
            templates={templates}
            selectedTemplateId={selectedTemplate?.id || ''}
            setSelectedTemplateId={setSelectedTemplateId}
            exportPdf={exportPdf}
            setExportPdf={setExportPdf}
            selectedCount={selectedCount}
            busy={busy}
            createJob={createJob}
            setActiveView={setActiveView}
          />
        )}

        {activeView === 'templates' && (
          <TemplatesView
            templates={templates}
            editingTemplate={editingTemplate}
            setEditingTemplate={setEditingTemplate}
            saveTemplate={saveTemplate}
            duplicateTemplate={duplicateTemplate}
            deleteTemplate={deleteTemplate}
            setDefaultTemplate={setDefaultTemplate}
          />
        )}

        {activeView === 'history' && (
          <HistoryView jobs={jobs} selectedJob={selectedJob} openJob={openJob} deleteJob={deleteJob} downloadJob={downloadJob} loadJobs={loadJobs} setActiveView={setActiveView} />
        )}

        {activeView === 'platforms' && <PlatformView platformInfo={platformInfo} loadPlatformInfo={loadPlatformInfo} />}

        {activeView === 'settings' && (
          <SettingsView
            appInfo={appInfo}
            settingsDraft={settingsDraft}
            setSettingsDraft={setSettingsDraft}
            saveSettings={saveSettings}
            updateState={updateState}
            checkForUpdates={checkForUpdates}
            setShowAvatarModal={setShowAvatarModal}
          />
        )}
      </section>

      {showAvatarModal && (
        <div className="modalBackdrop" role="presentation" onClick={() => setShowAvatarModal(false)}>
          <div className="avatarModal" role="dialog" aria-modal="true" aria-label="作者信息" onClick={(event) => event.stopPropagation()}>
            <img className="modalAvatar" src={authorAvatar} alt="JIAOKEQING" />
            <div className="modalText">JIAOKEQING</div>
            <a className="mailLink" href="mailto:jiaokeqing888@proton.me">
              <Mail size={14} />
              <span>jiaokeqing888@proton.me</span>
            </a>
            <button type="button" className="primary compact" onClick={() => setShowAvatarModal(false)}>
              收到
            </button>
          </div>
        </div>
      )}
    </main>
  );
}

function ProcessView(props) {
  return (
    <form className="pageGrid" onSubmit={props.createJob}>
      <section className="panel wide">
        <PanelTitle icon={UploadCloud} title="选择来源" />
        <div className="uploadGrid">
          <label className="uploadTile">
            <input ref={props.fileInputRef} type="file" accept=".doc,.docx" multiple onChange={(event) => props.handleFilesSelected(event.target.files)} />
            <FileUp size={26} />
            <strong>选择 Word 文件</strong>
            <span>支持多个 .doc / .docx</span>
          </label>
          <label className="uploadTile">
            <input
              type="file"
              accept=".doc,.docx"
              multiple
              webkitdirectory=""
              ref={props.folderInputRef}
              onChange={(event) => props.handleFilesSelected(event.target.files)}
            />
            <FolderInput size={26} />
            <strong>选择文件夹</strong>
            <span>保留相对路径</span>
          </label>
        </div>
        <div className="selectionBar">
          <span>{props.files.length ? `已选择 ${props.files.length} 个文件` : '尚未选择文件'}</span>
          {props.files.length > 0 && (
            <button type="button" className="textButton" onClick={props.clearSelectedFiles}>
              清空
            </button>
          )}
        </div>
        {props.files.length > 0 && (
          <div className="selectedFiles">
            {props.files.map((file, index) => (
              <div className="selectedFile" key={`${file.webkitRelativePath || file.name}-${file.size}-${index}`}>
                <span>{file.webkitRelativePath || file.name}</span>
                <button type="button" className="miniIconButton" onClick={() => props.removeSelectedFile(index)} title="移除文件">
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
      <section className="panel">
        <div className="panelToolbar">
          <PanelTitle icon={Library} title="选择模板" />
          <button type="button" className="secondary" onClick={() => props.setActiveView('templates')}>
            管理
          </button>
        </div>
        <div className="templatePicker">
          {props.templates.map((template) => (
            <label key={template.id} className={`templateChoice ${props.selectedTemplateId === template.id ? 'selected' : ''}`}>
              <input type="radio" name="template" checked={props.selectedTemplateId === template.id} onChange={() => props.setSelectedTemplateId(template.id)} />
              <span>
                <strong>{template.name}</strong>
                <small>{template.description || '自定义格式规则'}</small>
              </span>
              {template.is_default && <em>默认</em>}
            </label>
          ))}
        </div>
      </section>
      <section className="panel">
        <PanelTitle icon={FileText} title="输出选项" />
        <label className="switchRow">
          <input type="checkbox" checked={props.exportPdf} onChange={(event) => props.setExportPdf(event.target.checked)} />
          <span>
            <strong>导出 PDF</strong>
            <small>关闭后输出排版后的 DOCX</small>
          </span>
        </label>
        <button className="primary" disabled={props.busy || props.selectedCount === 0}>
          <Play size={17} />
          <span>{props.busy ? '提交中' : '开始处理'}</span>
        </button>
      </section>
    </form>
  );
}

function TemplatesView({ templates, editingTemplate, setEditingTemplate, saveTemplate, duplicateTemplate, deleteTemplate, setDefaultTemplate }) {
  const draft = editingTemplate || newTemplateDraft();
  return (
    <div className="splitView templateSplit">
      <section className="panel">
        <div className="panelToolbar">
          <PanelTitle icon={Library} title="本地模板" />
          <button className="secondary" onClick={() => setEditingTemplate(newTemplateDraft())}>
            <Plus size={16} />
            <span>新建</span>
          </button>
        </div>
        <div className="templateList">
          {templates.map((template) => (
            <button key={template.id} className={`templateRow ${editingTemplate?.id === template.id ? 'active' : ''}`} onClick={() => setEditingTemplate(clone(template))}>
              <span>
                <strong>{template.name}</strong>
                <small>{template.description || '无说明'}</small>
              </span>
              <span className="rowBadges">
                {template.is_builtin && <em>内置</em>}
                {template.is_default && <em>默认</em>}
              </span>
            </button>
          ))}
        </div>
      </section>
      <section className="panel editorPanel">
        <PanelTitle icon={FileText} title={editingTemplate ? '编辑模板' : '新建模板'} />
        <TemplateEditor template={draft} onChange={setEditingTemplate} onSave={saveTemplate} onDuplicate={duplicateTemplate} onDelete={deleteTemplate} onDefault={setDefaultTemplate} />
      </section>
    </div>
  );
}

function TemplateEditor({ template, onChange, onSave, onDuplicate, onDelete, onDefault }) {
  const builtin = template.config.builtin;
  function updateField(key, value) {
    onChange({ ...template, [key]: value });
  }
  function updateConfig(key, value) {
    onChange({ ...template, config: { ...template.config, builtin: { ...template.config.builtin, [key]: value } } });
  }
  return (
    <div className="templateEditor">
      {template.is_builtin && <div className="hint">内置模板不能直接修改，可以复制后编辑。</div>}
      <div className="grid">
        <TextInput label="模板名称" value={template.name} onChange={(value) => updateField('name', value)} disabled={template.is_builtin} />
        <TextInput label="模板说明" value={template.description} onChange={(value) => updateField('description', value)} disabled={template.is_builtin} />
        <TextInput label="标题字体" value={builtin.title_font} onChange={(value) => updateConfig('title_font', value)} disabled={template.is_builtin} />
        <NumberInput label="标题字号" value={builtin.title_size} onChange={(value) => updateConfig('title_size', value)} disabled={template.is_builtin} />
        <TextInput label="正文字体" value={builtin.body_font} onChange={(value) => updateConfig('body_font', value)} disabled={template.is_builtin} />
        <NumberInput label="正文字号" value={builtin.body_size} onChange={(value) => updateConfig('body_size', value)} disabled={template.is_builtin} />
        <TextInput label="一级标题字体" value={builtin.heading_font} onChange={(value) => updateConfig('heading_font', value)} disabled={template.is_builtin} />
        <TextInput label="二级标题字体" value={builtin.second_heading_font} onChange={(value) => updateConfig('second_heading_font', value)} disabled={template.is_builtin} />
        <TextInput label="三级标题字体" value={builtin.third_heading_font} onChange={(value) => updateConfig('third_heading_font', value)} disabled={template.is_builtin} />
        <TextInput label="英文字体" value={builtin.latin_font} onChange={(value) => updateConfig('latin_font', value)} disabled={template.is_builtin} />
        <NumberInput label="行距 磅" value={builtin.line_spacing_pt} onChange={(value) => updateConfig('line_spacing_pt', value)} disabled={template.is_builtin} />
        <NumberInput label="首行缩进 字符" value={builtin.first_line_indent_chars} onChange={(value) => updateConfig('first_line_indent_chars', value)} disabled={template.is_builtin} />
        <NumberInput label="上边距 cm" step="0.1" value={builtin.margin_top_cm} onChange={(value) => updateConfig('margin_top_cm', value)} disabled={template.is_builtin} />
        <NumberInput label="下边距 cm" step="0.1" value={builtin.margin_bottom_cm} onChange={(value) => updateConfig('margin_bottom_cm', value)} disabled={template.is_builtin} />
        <NumberInput label="左边距 cm" step="0.1" value={builtin.margin_left_cm} onChange={(value) => updateConfig('margin_left_cm', value)} disabled={template.is_builtin} />
        <NumberInput label="右边距 cm" step="0.1" value={builtin.margin_right_cm} onChange={(value) => updateConfig('margin_right_cm', value)} disabled={template.is_builtin} />
      </div>
      <div className="optionsRow">
        <label className="check">
          <input type="checkbox" checked={builtin.normalize_parentheses} disabled={template.is_builtin} onChange={(event) => updateConfig('normalize_parentheses', event.target.checked)} />
          <span>中文括号归一</span>
        </label>
        <label className="check">
          <input type="checkbox" checked={builtin.normalize_spacing} disabled={template.is_builtin} onChange={(event) => updateConfig('normalize_spacing', event.target.checked)} />
          <span>去除多余空格</span>
        </label>
      </div>
      <div className="editorActions">
        {!template.is_builtin && (
          <button className="primary compact" onClick={() => onSave(template)}>
            <Save size={16} />
            <span>保存模板</span>
          </button>
        )}
        {template.id && (
          <button className="secondary" onClick={() => onDuplicate(template)}>
            <Copy size={16} />
            <span>复制</span>
          </button>
        )}
        {template.id && !template.is_default && (
          <button className="secondary" onClick={() => onDefault(template)}>
            <Check size={16} />
            <span>设为默认</span>
          </button>
        )}
        {template.id && !template.is_builtin && !template.is_default && (
          <button className="dangerButton" onClick={() => onDelete(template)}>
            <Trash2 size={16} />
            <span>删除</span>
          </button>
        )}
      </div>
    </div>
  );
}

function HistoryView({ jobs, selectedJob, openJob, deleteJob, downloadJob, loadJobs, setActiveView }) {
  return (
    <div className="splitView historySplit">
      <section className="panel">
        <div className="panelToolbar">
          <PanelTitle icon={History} title="任务列表" />
          <button className="secondary" onClick={loadJobs}>
            <RefreshCw size={16} />
            <span>刷新</span>
          </button>
        </div>
        {jobs.length === 0 ? (
          <EmptyState title="还没有任务" action="开始处理" onAction={() => setActiveView('process')} />
        ) : (
          <div className="jobList">
            {jobs.map((job) => (
              <div
                key={job.id}
                className={`jobRow ${selectedJob?.id === job.id ? 'active' : ''}`}
                role="button"
                tabIndex={0}
                onClick={() => openJob(job)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') openJob(job);
                }}
              >
                <span className={`status ${job.status}`}>{statusLabel(job.status)}</span>
                <strong>{job.id.slice(0, 8)}</strong>
                <span>{job.succeeded_files}/{job.total_files} 成功</span>
                <span>{new Date(job.created_at).toLocaleString()}</span>
                <span className="jobActions">
                  <button type="button" className="miniIconButton danger" onClick={(event) => deleteJob(job.id, event)} title="删除任务">
                    <Trash2 size={15} />
                  </button>
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
      <section className="panel">
        {selectedJob ? (
          <>
            <div className="detailHeader">
              <div>
                <h2>任务 {selectedJob.id.slice(0, 8)}</h2>
                <p>{statusLabel(selectedJob.status)} · 成功 {selectedJob.succeeded_files} · 失败 {selectedJob.failed_files}</p>
              </div>
              {selectedJob.download_ready && (
                <button type="button" className="primary compact" onClick={() => downloadJob(selectedJob.id)}>
                  <Download size={17} />
                  <span>下载 ZIP</span>
                </button>
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
          </>
        ) : (
          <EmptyState title="选择一个任务查看结果" />
        )}
      </section>
    </div>
  );
}

function PlatformView({ platformInfo, loadPlatformInfo }) {
  if (!platformInfo) return <section className="panel">正在检测平台...</section>;
  return (
    <>
      <section className="platformGrid">
        {['Windows', '华为电脑', '统信 UOS'].map((name) => (
          <div className={`platformCard ${platformInfo.platform_label.includes(name) ? 'active' : ''}`} key={name}>
            <strong>{name}</strong>
            <span>{platformText(name)}</span>
            <em>{name === 'Windows' ? '支持' : '适配'}</em>
          </div>
        ))}
      </section>
      <div className="splitView">
        <section className="panel">
          <PanelTitle icon={MonitorCog} title="转换引擎" />
          <div className="engineList">
            {platformInfo.engines.map((engine) => (
              <div className="engineRow" key={engine.id}>
                <span>
                  <strong>{engine.name}</strong>
                  <small>{engine.description}</small>
                </span>
                <em>{engineStatusLabel(engine.status)}</em>
              </div>
            ))}
          </div>
        </section>
        <section className="panel">
          <div className="panelToolbar">
            <PanelTitle icon={Info} title="环境状态" />
            <button className="secondary" onClick={loadPlatformInfo}>
              重新检测
            </button>
          </div>
          <dl className="infoList">
            <div><dt>当前系统</dt><dd>{platformInfo.platform_label} / {platformInfo.machine}</dd></div>
            <div><dt>推荐引擎</dt><dd>{platformInfo.recommended_engine}</dd></div>
            <div><dt>离线能力</dt><dd>{platformInfo.message}</dd></div>
          </dl>
          <div className="updateBox"><strong>建议</strong><span>统信 UOS 建议安装 LibreOffice，以获得稳定的 doc/docx/pdf 转换能力。</span></div>
        </section>
      </div>
    </>
  );
}

function SettingsView({ appInfo, settingsDraft, setSettingsDraft, saveSettings, updateState, checkForUpdates, setShowAvatarModal }) {
  if (!appInfo || !settingsDraft) return <section className="panel">正在读取设置...</section>;
  return (
    <div className="settingsGrid">
      <form className="panel" onSubmit={saveSettings}>
        <PanelTitle icon={Settings} title="本机配置" />
        <TextInput label="默认打开位置" value={settingsDraft.default_open_dir} onChange={(value) => setSettingsDraft({ ...settingsDraft, default_open_dir: value })} />
        <div className="grid">
          <NumberInput label="单批文件上限" value={settingsDraft.max_files_per_job} onChange={(value) => setSettingsDraft({ ...settingsDraft, max_files_per_job: value })} />
          <NumberInput label="结果保留小时" value={settingsDraft.retention_hours} onChange={(value) => setSettingsDraft({ ...settingsDraft, retention_hours: value })} />
        </div>
        <TextInput label="GitHub 仓库" value={settingsDraft.github_repo} onChange={(value) => setSettingsDraft({ ...settingsDraft, github_repo: value })} placeholder="owner/repo" />
        <button className="primary compact">
          <Save size={16} />
          <span>保存设置</span>
        </button>
      </form>
      <section className="panel">
        <PanelTitle icon={Info} title="应用信息" />
        <dl className="infoList">
          <div><dt>版本</dt><dd>{appInfo.version}</dd></div>
          <div><dt>运行模式</dt><dd>{appInfo.mode === 'desktop' ? '桌面客户端' : '浏览器模式'}</dd></div>
          <div><dt>数据目录</dt><dd>{appInfo.data_dir}</dd></div>
          <div><dt>工作线程</dt><dd>{appInfo.worker_count}</dd></div>
        </dl>
        <button className="secondary" onClick={checkForUpdates}>
          <RefreshCw size={16} />
          <span>检查 GitHub 更新</span>
        </button>
        {updateState && (
          <div className={`updateBox ${updateState.status || ''}`}>
            <strong>{updateState.latest_version || updateState.current_version || appInfo.version}</strong>
            <span>{updateState.message}</span>
            {updateState.release_url && <a href={updateState.release_url}>打开发布页</a>}
          </div>
        )}
      </section>
      <section className="panel aboutPanel">
        <PanelTitle icon={Mail} title="关于" />
        <button className="authorCard" onClick={() => setShowAvatarModal(true)}>
          <img src={authorAvatar} alt="JIAOKEQING" />
          <span>
            <strong>JIAOKEQING</strong>
            <small>jiaokeqing888@proton.me</small>
          </span>
        </button>
      </section>
    </div>
  );
}

function PanelTitle({ icon: Icon, title }) {
  return (
    <div className="panelHeader">
      <Icon size={20} />
      <h2>{title}</h2>
    </div>
  );
}

function EmptyState({ title, action, onAction }) {
  return (
    <div className="emptyState">
      <FileText size={28} />
      <strong>{title}</strong>
      {action && onAction && (
        <button className="secondary" onClick={onAction}>
          <Plus size={16} />
          <span>{action}</span>
        </button>
      )}
    </div>
  );
}

function TextInput({ label, value, onChange, disabled = false, placeholder = '' }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input value={value || ''} disabled={disabled} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function NumberInput({ label, value, onChange, step = '1', disabled = false }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type="number" step={step} value={value ?? 0} disabled={disabled} onChange={(event) => onChange(Number(event.target.value))} />
    </label>
  );
}

function newTemplateDraft() {
  return { isNew: true, name: '新模板', description: '', config: clone(defaultTemplateConfig), is_builtin: false, is_default: false };
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function platformText(name) {
  return {
    Windows: '优先使用 WPS / Microsoft Office；未安装时降级为 LibreOffice。',
    华为电脑: '支持 Windows 版华为电脑；Linux 环境使用 LibreOffice 引擎。',
    '统信 UOS': '使用系统 LibreOffice / WPS 命令行能力，提供 deb 安装包。',
  }[name];
}

function engineStatusLabel(status) {
  return { recommended: '推荐', available: '可用', missing: '未安装', unsupported: '不适用' }[status] || status;
}

function viewTitle(view) {
  return { process: '处理任务', templates: '模板库', history: '任务记录', platforms: '平台适配', settings: '设置' }[view];
}

function viewSubtitle(view) {
  return {
    process: '选择文档、套用模板，然后批量输出结果包。',
    templates: '管理可离线复用的本地格式模板。',
    history: '查看处理进度、文件结果和下载包。',
    platforms: '检测当前系统和转换引擎，保证跨平台离线运行。',
    settings: '配置本机目录、保留策略和 GitHub 版本提示。',
  }[view];
}

function statusLabel(status) {
  const labels = { queued: '排队中', running: '处理中', succeeded: '已完成', partial_failed: '部分失败', failed: '失败', expired: '已过期' };
  return labels[status] || status;
}

createRoot(document.getElementById('root')).render(<App />);
