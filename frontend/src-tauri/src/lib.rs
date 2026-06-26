use std::path::PathBuf;
use std::sync::Mutex;

use tauri::Manager;
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

struct SidecarState(Mutex<Option<CommandChild>>);

#[tauri::command]
async fn save_zip_file(app: tauri::AppHandle, suggested_name: String, bytes: Vec<u8>) -> Result<Option<String>, String> {
    if bytes.is_empty() {
        return Err("ZIP 内容为空，无法保存".to_string());
    }

    let file_name = normalized_zip_file_name(&suggested_name);
    let Some(file_path) = app
        .dialog()
        .file()
        .set_title("保存 ZIP 结果包")
        .set_file_name(file_name)
        .add_filter("ZIP 文件", &["zip"])
        .blocking_save_file()
    else {
        return Ok(None);
    };

    let target = ensure_zip_extension(
        file_path
            .into_path()
            .map_err(|error| format!("无法解析保存路径：{error}"))?,
    );
    std::fs::write(&target, bytes).map_err(|error| format!("保存 ZIP 失败：{error}"))?;

    Ok(Some(target.to_string_lossy().into_owned()))
}

fn normalized_zip_file_name(name: &str) -> String {
    let trimmed = name.trim();
    let fallback = if trimmed.is_empty() { "result.zip" } else { trimmed };
    let mut safe_name = fallback
        .chars()
        .map(|item| match item {
            '\\' | '/' | ':' | '*' | '?' | '"' | '<' | '>' | '|' => '_',
            _ => item,
        })
        .collect::<String>();

    if !safe_name.to_lowercase().ends_with(".zip") {
        safe_name.push_str(".zip");
    }
    safe_name
}

fn ensure_zip_extension(path: PathBuf) -> PathBuf {
    if path.extension().and_then(|value| value.to_str()).is_some_and(|value| value.eq_ignore_ascii_case("zip")) {
        return path;
    }
    path.with_extension("zip")
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![save_zip_file])
        .setup(|app| {
            match app.shell().sidecar("word-batch-sidecar") {
                Ok(command) => match command.args(["--host", "127.0.0.1", "--port", "8765"]).spawn() {
                    Ok((mut receiver, child)) => {
                        app.manage(SidecarState(Mutex::new(Some(child))));
                        tauri::async_runtime::spawn(async move {
                            while let Some(event) = receiver.recv().await {
                                println!("sidecar: {:?}", event);
                            }
                        });
                    }
                    Err(error) => {
                        eprintln!("failed to start sidecar: {error}");
                        app.manage(SidecarState(Mutex::new(None)));
                    }
                },
                Err(error) => {
                    eprintln!("failed to create sidecar command: {error}");
                    app.manage(SidecarState(Mutex::new(None)));
                }
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let app = window.app_handle();
                if let Some(state) = app.try_state::<SidecarState>() {
                    if let Some(child) = state.0.lock().expect("sidecar state poisoned").take() {
                        let _ = child.kill();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
