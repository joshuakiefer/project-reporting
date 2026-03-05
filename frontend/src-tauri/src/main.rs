//! WorkOptimize AI — Tauri backend
//!
//! The Tauri layer handles:
//! - Window management (overlay positioning, always-on-top)
//! - System tray integration
//! - Launching the Python backend service
//! - Native OS integrations (notifications, global shortcuts)

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;

/// Launch the Python FastAPI backend as a sidecar process.
fn spawn_backend() -> Option<std::process::Child> {
    // In production, the Python service is bundled as a sidecar executable
    // (PyInstaller or Nuitka compiled). During development, we assume
    // the developer runs it separately.
    let result = std::process::Command::new("workoptimize")
        .args(["serve", "--port", "8321"])
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn();

    match result {
        Ok(child) => {
            println!("Backend service started (PID: {})", child.id());
            Some(child)
        }
        Err(e) => {
            eprintln!("Failed to start backend service: {e}");
            eprintln!("Make sure 'workoptimize' is installed: pip install -e .");
            None
        }
    }
}

fn main() {
    let _backend = spawn_backend();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Position window in bottom-right of screen
            if let Some(window) = app.get_webview_window("main") {
                if let Ok(monitor) = window.current_monitor() {
                    if let Some(monitor) = monitor {
                        let screen = monitor.size();
                        let scale = monitor.scale_factor();
                        let w = 400.0;
                        let h = 600.0;
                        let x = (screen.width as f64 / scale) - w - 20.0;
                        let y = (screen.height as f64 / scale) - h - 60.0;
                        let _ = window.set_position(tauri::PhysicalPosition::new(
                            (x * scale) as i32,
                            (y * scale) as i32,
                        ));
                    }
                }
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running WorkOptimize AI");
}
