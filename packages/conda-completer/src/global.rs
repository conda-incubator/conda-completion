use std::collections::HashSet;
use std::path::{Path, PathBuf};

use serde::Deserialize;

use crate::cache::{file_stat, CachedFile, StatCache};

#[derive(Deserialize, Default)]
struct Condarc {
    #[serde(default)]
    channels: Vec<String>,
}

#[derive(Debug, Default)]
pub struct GlobalContext {
    pub env_names: Vec<String>,
    pub channels: Vec<String>,
    pub tool_names: Vec<String>,
}

impl GlobalContext {
    pub fn load(cache: &mut StatCache) -> Self {
        let mut ctx = Self::default();
        let home = dirs_home();

        if let Some(ref home) = home {
            load_environments_txt(home, &mut ctx, cache);
            load_condarc(home, &mut ctx, cache);
            load_global_toml(home, &mut ctx, cache);
        }

        ctx
    }
}

fn dirs_home() -> Option<PathBuf> {
    #[cfg(target_os = "windows")]
    {
        std::env::var("USERPROFILE")
            .ok()
            .or_else(|| {
                let drive = std::env::var("HOMEDRIVE").ok()?;
                let path = std::env::var("HOMEPATH").ok()?;
                Some(format!("{}{}", drive, path))
            })
            .map(PathBuf::from)
    }
    #[cfg(not(target_os = "windows"))]
    {
        std::env::var("HOME").ok().map(PathBuf::from)
    }
}

fn load_environments_txt(home: &Path, ctx: &mut GlobalContext, cache: &mut StatCache) {
    let path = home.join(".conda").join("environments.txt");
    if !path.is_file() {
        return;
    }
    let path_str = path.to_string_lossy();

    if let Some(cached) = cache.get_if_fresh(&path_str) {
        ctx.env_names.extend(cached.env_names.iter().cloned());
        return;
    }

    if let Ok(content) = fs_err::read_to_string(&path) {
        let mut seen = HashSet::new();
        let mut env_names = Vec::new();
        for line in content.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }
            if let Some(name) = PathBuf::from(line).file_name() {
                if let Some(s) = name.to_str() {
                    if seen.insert(s.to_string()) {
                        env_names.push(s.to_string());
                    }
                }
            }
        }

        if let Some((mtime, size)) = file_stat(&path) {
            cache.update(
                &path_str,
                CachedFile {
                    mtime_secs: mtime,
                    size,
                    env_names: env_names.clone(),
                    task_names: Vec::new(),
                    feature_names: Vec::new(),
                    channels: Vec::new(),
                    tool_names: Vec::new(),
                },
            );
        }

        ctx.env_names.extend(env_names);
    }
}

fn load_condarc(home: &Path, ctx: &mut GlobalContext, cache: &mut StatCache) {
    let mut paths = vec![home.join(".condarc")];

    if let Ok(condarc) = std::env::var("CONDARC") {
        let p = PathBuf::from(&condarc);
        if p.is_file() && !paths.contains(&p) {
            paths.insert(0, p);
        }
    }

    #[cfg(target_os = "windows")]
    {
        let system_path = PathBuf::from(r"C:\ProgramData\conda\.condarc");
        if system_path.is_file() {
            paths.push(system_path);
        }
    }

    for path in &paths {
        if !path.is_file() {
            continue;
        }
        let path_str = path.to_string_lossy();

        if let Some(cached) = cache.get_if_fresh(&path_str) {
            ctx.channels.extend(cached.channels.iter().cloned());
            continue;
        }

        if let Ok(content) = fs_err::read_to_string(path) {
            let mut seen = HashSet::new();
            let mut channels = Vec::new();
            if let Ok(rc) = serde_saphyr::from_str::<Condarc>(&content) {
                for ch in &rc.channels {
                    if seen.insert(ch.as_str()) {
                        channels.push(ch.clone());
                    }
                }
            }

            if let Some((mtime, size)) = file_stat(path) {
                cache.update(
                    &path_str,
                    CachedFile {
                        mtime_secs: mtime,
                        size,
                        env_names: Vec::new(),
                        task_names: Vec::new(),
                        feature_names: Vec::new(),
                        channels: channels.clone(),
                        tool_names: Vec::new(),
                    },
                );
            }

            ctx.channels.extend(channels);
        }
    }
}

fn load_global_toml(home: &Path, ctx: &mut GlobalContext, cache: &mut StatCache) {
    let path = home.join(".conda").join("global").join("global.toml");
    if !path.is_file() {
        return;
    }
    let path_str = path.to_string_lossy();

    if let Some(cached) = cache.get_if_fresh(&path_str) {
        ctx.tool_names.extend(cached.tool_names.iter().cloned());
        return;
    }

    if let Ok(content) = fs_err::read_to_string(&path) {
        let mut seen = HashSet::new();
        let mut tool_names = Vec::new();
        if let Ok(value) = content.parse::<toml::Value>() {
            if let Some(table) = value.get("envs").and_then(|v| v.as_table()) {
                for key in table.keys() {
                    if seen.insert(key.as_str()) {
                        tool_names.push(key.clone());
                    }
                }
            }
        }

        if let Some((mtime, size)) = file_stat(&path) {
            cache.update(
                &path_str,
                CachedFile {
                    mtime_secs: mtime,
                    size,
                    env_names: Vec::new(),
                    task_names: Vec::new(),
                    feature_names: Vec::new(),
                    channels: Vec::new(),
                    tool_names: tool_names.clone(),
                },
            );
        }

        ctx.tool_names.extend(tool_names);
    }
}
