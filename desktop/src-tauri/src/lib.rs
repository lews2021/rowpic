// Tauri entry: launches the Python backend as a child process and keeps
// it alive for the lifetime of the window. The webview loads the Vite
// dev URL in dev mode, or the static dist in release mode.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;
#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

struct BackendProcess(Mutex<Option<Child>>);

#[tauri::command]
fn backend_status(state: tauri::State<BackendProcess>) -> bool {
    let mut guard = state.0.lock().unwrap();
    if let Some(child) = guard.as_mut() {
        match child.try_wait() {
            Ok(Some(_)) => false,
            Ok(None) => true,
            Err(_) => false,
        }
    } else {
        false
    }
}

fn spawn_backend() -> Child {
    // Locate the backend directory relative to the executable.
    // In dev: repo root; in bundled: alongside the .exe.
    let backend_dir = if cfg!(debug_assertions) {
        std::env::current_dir()
            .unwrap_or_default()
            .join("..")
            .join("backend")
    } else {
        std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|p| p.to_path_buf()))
            .unwrap_or_default()
            .join("backend")
    };

    let mut cmd = Command::new("python");
    cmd.args(["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8765"]);
    cmd.current_dir(&backend_dir);
    cmd.stdout(Stdio::piped()).stderr(Stdio::piped());
    cmd.env("ROWPIC_HOST", "127.0.0.1");
    cmd.env("ROWPIC_PORT", "8765");

    #[cfg(target_os = "windows")]
    {
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    let mut child = cmd.spawn().expect("failed to start python backend");

    // drain output to avoid pipe buffer blocking
    if let Some(stdout) = child.stdout.take() {
        thread::spawn(move || {
            let _ = BufReader::new(stdout).lines().for_each(|l| {
                if let Ok(line) = l {
                    eprintln!("[backend] {}", line);
                }
            });
        });
    }
    if let Some(stderr) = child.stderr.take() {
        thread::spawn(move || {
            let _ = BufReader::new(stderr).lines().for_each(|l| {
                if let Ok(line) = l {
                    eprintln!("[backend-err] {}", line);
                }
            });
        });
    }

    child
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            let state = app.state::<BackendProcess>();
            let child = spawn_backend();
            *state.0.lock().unwrap() = Some(child);
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let state = window.state::<BackendProcess>();
                if let Some(mut child) = state.0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![backend_status])
        .run(tauri::generate_context!())
        .expect("error while running rowpic");
}
