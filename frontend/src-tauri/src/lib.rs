use std::sync::Mutex;

use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

struct SidecarState(Mutex<Option<CommandChild>>);

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
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
                    if let Some(child) = state.0.lock().expect("sidecar state poisoned").as_mut() {
                        let _ = child.kill();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
