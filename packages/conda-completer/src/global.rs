use std::collections::HashSet;
use std::env;
use std::path::Component;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Deserializer};

use crate::cache::{file_stat, CachedFile, StatCache};

#[derive(Deserialize, Default)]
struct Condarc {
    #[serde(default)]
    channels: Vec<String>,
    #[serde(default, deserialize_with = "string_or_vec")]
    envs_dirs: Vec<String>,
    #[serde(default, deserialize_with = "string_or_vec")]
    envs_path: Vec<String>,
}

#[derive(Debug, Default)]
pub struct GlobalContext {
    pub env_names: Vec<String>,
    pub env_prefixes: Vec<String>,
    pub channels: Vec<String>,
    pub tool_names: Vec<String>,
    pub home: Option<PathBuf>,
}

const ENV_CACHE_FORMAT: u32 = 1;

#[derive(Debug, PartialEq, Eq)]
enum EnvironmentEntry {
    Name(String),
    Prefix(String),
}

struct EnvRegistry {
    env_dirs: Vec<PathBuf>,
    root_prefix: Option<PathBuf>,
}

impl EnvRegistry {
    fn from_home(home: &Path) -> Self {
        let root_prefix = Self::conda_root_prefix();
        let env_dirs = Self::known_env_dirs(home, root_prefix.as_deref());
        Self {
            env_dirs,
            root_prefix,
        }
    }

    fn classify(&self, raw: &str) -> Option<EnvironmentEntry> {
        let raw = raw.trim();
        if raw.is_empty() {
            return None;
        }
        let prefix = PathBuf::from(raw);
        if self
            .root_prefix
            .as_deref()
            .is_some_and(|root| Self::same_path(&prefix, root))
        {
            return Some(EnvironmentEntry::Name("base".to_string()));
        }
        self.named_env_name(&prefix)
            .map(EnvironmentEntry::Name)
            .or_else(|| Some(EnvironmentEntry::Prefix(raw.to_string())))
    }

    fn known_env_dirs(home: &Path, root_prefix: Option<&Path>) -> Vec<PathBuf> {
        let mut dirs = Vec::new();

        for var_name in ["CONDA_ENVS_PATH", "CONDA_ENVS_DIRS"] {
            if let Some(value) = env::var_os(var_name).filter(|value| !value.is_empty()) {
                for path in env::split_paths(&value) {
                    Self::add_env_dir(&mut dirs, path);
                }
            }
        }

        for path in Self::condarc_paths(home) {
            if !crate::cache::is_regular_file(&path) {
                continue;
            }
            let Some(content) = crate::cache::read_to_string_limited(&path) else {
                continue;
            };
            let Ok(rc) = serde_saphyr::from_str::<Condarc>(&content) else {
                continue;
            };
            for raw in rc.envs_dirs.iter().chain(&rc.envs_path) {
                if let Some(path) = Self::expand_config_path(raw, home) {
                    Self::add_env_dir(&mut dirs, path);
                }
            }
        }

        if let Some(root) = root_prefix {
            Self::add_env_dir(&mut dirs, root.join("envs"));
        }
        Self::add_env_dir(&mut dirs, home.join(".conda").join("envs"));

        #[cfg(target_os = "windows")]
        if let Some(appdata) = env::var_os("APPDATA").filter(|value| !value.is_empty()) {
            Self::add_env_dir(
                &mut dirs,
                PathBuf::from(appdata)
                    .join("conda")
                    .join("conda")
                    .join("envs"),
            );
        }

        dirs
    }

    fn condarc_paths(home: &Path) -> Vec<PathBuf> {
        let mut paths = vec![home.join(".condarc")];

        if let Some(condarc) = env::var_os("CONDARC").filter(|value| !value.is_empty()) {
            let p = PathBuf::from(condarc);
            if !paths.iter().any(|path| Self::same_path(path, &p)) {
                paths.insert(0, p);
            }
        }

        #[cfg(target_os = "windows")]
        {
            let system_path = PathBuf::from(r"C:\ProgramData\conda\.condarc");
            if !paths.iter().any(|path| Self::same_path(path, &system_path)) {
                paths.push(system_path);
            }
        }

        paths
    }

    fn conda_root_prefix() -> Option<PathBuf> {
        if let Some(root) = env::var_os("CONDA_ROOT_PREFIX").filter(|value| !value.is_empty()) {
            return Some(PathBuf::from(root));
        }
        let conda_exe = PathBuf::from(env::var_os("CONDA_EXE").filter(|value| !value.is_empty())?);
        conda_exe
            .parent()
            .and_then(Path::parent)
            .map(Path::to_path_buf)
    }

    fn named_env_name(&self, prefix: &Path) -> Option<String> {
        let parent = prefix.parent()?;
        if !self
            .env_dirs
            .iter()
            .any(|env_dir| Self::same_path(parent, env_dir))
        {
            return None;
        }
        let name = prefix.file_name()?.to_str()?;
        (!name.is_empty()).then(|| name.to_string())
    }

    fn add_env_dir(dirs: &mut Vec<PathBuf>, path: PathBuf) {
        if path.as_os_str().is_empty() {
            return;
        }
        let path = Self::normalize_path(&path);
        if !dirs.iter().any(|dir| Self::same_path(dir, &path)) {
            dirs.push(path);
        }
    }

    fn expand_config_path(raw: &str, home: &Path) -> Option<PathBuf> {
        if raw.is_empty() {
            return None;
        }
        if raw == "~" {
            return Some(home.to_path_buf());
        }
        if let Some(rest) = raw.strip_prefix("~/").or_else(|| raw.strip_prefix("~\\")) {
            return Some(home.join(rest));
        }
        Some(PathBuf::from(raw))
    }

    fn same_path(a: &Path, b: &Path) -> bool {
        Self::normalize_path(a) == Self::normalize_path(b)
    }

    fn normalize_path(path: &Path) -> PathBuf {
        let mut normalized = PathBuf::new();
        for component in path.components() {
            match component {
                Component::CurDir => {}
                Component::ParentDir => normalized.push(".."),
                _ => normalized.push(component.as_os_str()),
            }
        }
        normalized
    }
}

impl GlobalContext {
    pub fn load(cache: &mut StatCache) -> Self {
        let home = dirs_home();
        let mut ctx = Self {
            home: home.clone(),
            ..Self::default()
        };

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
    if !crate::cache::is_regular_file(&path) {
        return;
    }
    let path_str = path.to_string_lossy();
    let registry = EnvRegistry::from_home(home);

    if let Some(cached) = cache.get_if_fresh(&path_str) {
        if cached.env_cache_format == ENV_CACHE_FORMAT {
            ctx.env_names.extend(cached.env_names.iter().cloned());
            ctx.env_prefixes.extend(cached.env_prefixes.iter().cloned());
            return;
        }
    }

    if let Some(content) = crate::cache::read_to_string_limited(&path) {
        let mut seen_names = HashSet::new();
        let mut seen_prefixes = HashSet::new();
        let mut env_names = Vec::new();
        let mut env_prefixes = Vec::new();
        for line in content.lines() {
            match registry.classify(line) {
                Some(EnvironmentEntry::Name(name)) if seen_names.insert(name.clone()) => {
                    env_names.push(name);
                }
                Some(EnvironmentEntry::Prefix(prefix)) if seen_prefixes.insert(prefix.clone()) => {
                    env_prefixes.push(prefix);
                }
                None => {}
                _ => {}
            }
        }

        if let Some((mtime, size)) = file_stat(&path) {
            cache.update(
                &path_str,
                CachedFile {
                    mtime_secs: mtime,
                    size,
                    env_cache_format: ENV_CACHE_FORMAT,
                    env_names: env_names.clone(),
                    env_prefixes: env_prefixes.clone(),
                    task_names: Vec::new(),
                    feature_names: Vec::new(),
                    channels: Vec::new(),
                    tool_names: Vec::new(),
                },
            );
        }

        ctx.env_names.extend(env_names);
        ctx.env_prefixes.extend(env_prefixes);
    }
}

fn load_condarc(home: &Path, ctx: &mut GlobalContext, cache: &mut StatCache) {
    for path in &EnvRegistry::condarc_paths(home) {
        if !crate::cache::is_regular_file(path) {
            continue;
        }
        let path_str = path.to_string_lossy();

        if let Some(cached) = cache.get_if_fresh(&path_str) {
            ctx.channels.extend(cached.channels.iter().cloned());
            continue;
        }

        if let Some(content) = crate::cache::read_to_string_limited(path) {
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
                        env_prefixes: Vec::new(),
                        task_names: Vec::new(),
                        feature_names: Vec::new(),
                        channels: channels.clone(),
                        tool_names: Vec::new(),
                        ..CachedFile::default()
                    },
                );
            }

            ctx.channels.extend(channels);
        }
    }
}

fn load_global_toml(home: &Path, ctx: &mut GlobalContext, cache: &mut StatCache) {
    let path = home.join(".conda").join("global").join("global.toml");
    if !crate::cache::is_regular_file(&path) {
        return;
    }
    let path_str = path.to_string_lossy();

    if let Some(cached) = cache.get_if_fresh(&path_str) {
        ctx.tool_names.extend(cached.tool_names.iter().cloned());
        return;
    }

    if let Some(content) = crate::cache::read_to_string_limited(&path) {
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
                    env_prefixes: Vec::new(),
                    task_names: Vec::new(),
                    feature_names: Vec::new(),
                    channels: Vec::new(),
                    tool_names: tool_names.clone(),
                    ..CachedFile::default()
                },
            );
        }

        ctx.tool_names.extend(tool_names);
    }
}

fn string_or_vec<'de, D>(deserializer: D) -> Result<Vec<String>, D::Error>
where
    D: Deserializer<'de>,
{
    #[derive(Deserialize)]
    #[serde(untagged)]
    enum StringList {
        One(String),
        Many(Vec<String>),
    }

    Ok(match Option::<StringList>::deserialize(deserializer)? {
        Some(StringList::One(value)) if !value.is_empty() => vec![value],
        Some(StringList::Many(values)) => values,
        _ => Vec::new(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use test_case::test_case;

    #[test_case(
        "/Users/example/.local/conda/envs/conda-build-dev",
        Some(EnvironmentEntry::Name("conda-build-dev".to_string())) ;
        "named env"
    )]
    #[test_case(
        "/Users/example/.local/conda/envs/conda-build-dev/conda-bld/debug/_h_env",
        Some(EnvironmentEntry::Prefix(
            "/Users/example/.local/conda/envs/conda-build-dev/conda-bld/debug/_h_env".to_string()
        )) ;
        "nested prefix"
    )]
    #[test_case("", None ; "empty line")]
    fn env_registry_classifies_entries(raw: &str, expected: Option<EnvironmentEntry>) {
        let envs_dir = PathBuf::from("/Users/example/.local/conda/envs");
        let registry = EnvRegistry {
            env_dirs: vec![envs_dir],
            root_prefix: None,
        };

        assert_eq!(registry.classify(raw), expected);
    }

    #[test]
    fn env_registry_classifies_root_prefix_as_base() {
        let registry = EnvRegistry {
            env_dirs: vec![],
            root_prefix: Some(PathBuf::from("/opt/conda")),
        };

        assert_eq!(
            registry.classify("/opt/conda"),
            Some(EnvironmentEntry::Name("base".to_string())),
        );
    }

    #[test]
    fn environments_txt_splits_names_from_prefixes() {
        let home = tempfile::tempdir().unwrap();
        let envs_dir = home.path().join(".local").join("conda").join("envs");
        let named_env = envs_dir.join("conda-build-dev");
        let build_env = named_env.join("conda-bld").join("debug").join("_h_env");
        let conda_dir = home.path().join(".conda");
        fs_err::create_dir_all(&conda_dir).unwrap();
        fs_err::write(
            home.path().join(".condarc"),
            format!("envs_dirs:\n  - {}\n", envs_dir.display()),
        )
        .unwrap();
        fs_err::write(
            conda_dir.join("environments.txt"),
            format!("{}\n{}\n", named_env.display(), build_env.display()),
        )
        .unwrap();

        let mut ctx = GlobalContext::default();
        let mut cache = StatCache::default();
        load_environments_txt(home.path(), &mut ctx, &mut cache);

        assert_eq!(ctx.env_names, vec!["conda-build-dev"]);
        assert_eq!(
            ctx.env_prefixes,
            vec![build_env.to_string_lossy().to_string()]
        );
    }

    #[test_case("envs_dirs: /tmp/conda/envs\n", vec!["/tmp/conda/envs"] ; "scalar")]
    #[test_case("envs_dirs:\n  - /tmp/conda/envs\n  - /opt/conda/envs\n", vec!["/tmp/conda/envs", "/opt/conda/envs"] ; "list")]
    fn condarc_envs_dirs_accepts_scalar_or_list(content: &str, expected: Vec<&str>) {
        let rc = serde_saphyr::from_str::<Condarc>(content).unwrap();

        assert_eq!(rc.envs_dirs, expected);
    }
}
