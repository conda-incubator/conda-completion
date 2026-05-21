use std::collections::HashMap;
use std::path::Path;

use serde::de::IgnoredAny;
use serde::Deserialize;

use crate::cache::{file_stat, CachedFile, StatCache};

const MAX_WALK_DEPTH: usize = 10;

#[derive(Debug, Default)]
pub struct ProjectContext {
    pub env_names: Vec<String>,
    pub task_names: Vec<String>,
    pub feature_names: Vec<String>,
    pub channels: Vec<String>,
}

impl ProjectContext {
    pub fn from_cwd(cwd: &Path, cache: &mut StatCache) -> Self {
        let mut ctx = Self::default();

        let mut dir = Some(cwd);
        let mut depth = 0;
        while let Some(d) = dir {
            if depth >= MAX_WALK_DEPTH {
                break;
            }
            if try_read_conda_toml(d, &mut ctx, cache)
                || try_read_pixi_toml(d, &mut ctx, cache)
                || try_read_pyproject_toml(d, &mut ctx, cache)
                || try_read_anaconda_project_yml(d, &mut ctx, cache)
                || try_read_conda_project_yml(d, &mut ctx, cache)
            {
                try_read_rattler_lock(d, &mut ctx, cache);
                try_read_conda_lock_yml(d, &mut ctx, cache);
                break;
            }
            try_read_environment_yml(d, &mut ctx, cache);
            dir = d.parent();
            depth += 1;
        }

        ctx
    }
}

fn apply_cached_to_project(cached: &CachedFile, ctx: &mut ProjectContext) {
    ctx.env_names.extend(cached.env_names.iter().cloned());
    ctx.task_names.extend(cached.task_names.iter().cloned());
    ctx.feature_names.extend(cached.feature_names.iter().cloned());
    ctx.channels.extend(cached.channels.iter().cloned());
}

fn cache_from_project(ctx: &ProjectContext, mtime: u64, size: u64) -> CachedFile {
    CachedFile {
        mtime_secs: mtime,
        size,
        env_names: ctx.env_names.clone(),
        task_names: ctx.task_names.clone(),
        feature_names: ctx.feature_names.clone(),
        channels: ctx.channels.clone(),
        tool_names: Vec::new(),
    }
}

fn try_read_toml_file(
    path: &Path,
    ctx: &mut ProjectContext,
    cache: &mut StatCache,
    extract: fn(&str, &mut ProjectContext),
) -> bool {
    if !crate::cache::is_regular_file(path) {
        return false;
    }
    let path_str = path.to_string_lossy();

    if let Some(cached) = cache.get_if_fresh(&path_str) {
        apply_cached_to_project(cached, ctx);
        return true;
    }

    if let Some(content) = crate::cache::read_to_string_limited(path) {
        let mut file_ctx = ProjectContext::default();
        extract(&content, &mut file_ctx);

        if let Some((mtime, size)) = file_stat(path) {
            cache.update(&path_str, cache_from_project(&file_ctx, mtime, size));
        }

        apply_cached_to_project(
            &CachedFile {
                mtime_secs: 0,
                size: 0,
                env_names: file_ctx.env_names,
                task_names: file_ctx.task_names,
                feature_names: file_ctx.feature_names,
                channels: file_ctx.channels,
                tool_names: Vec::new(),
            },
            ctx,
        );
        return true;
    }
    false
}

fn try_read_conda_toml(dir: &Path, ctx: &mut ProjectContext, cache: &mut StatCache) -> bool {
    try_read_toml_file(&dir.join("conda.toml"), ctx, cache, |content, ctx| {
        extract_toml_workspace(content, ctx);
    })
}

fn try_read_pixi_toml(dir: &Path, ctx: &mut ProjectContext, cache: &mut StatCache) -> bool {
    try_read_toml_file(&dir.join("pixi.toml"), ctx, cache, |content, ctx| {
        extract_toml_workspace(content, ctx);
    })
}

fn try_read_pyproject_toml(dir: &Path, ctx: &mut ProjectContext, cache: &mut StatCache) -> bool {
    try_read_toml_file(
        &dir.join("pyproject.toml"),
        ctx,
        cache,
        |content, ctx| {
            if let Ok(value) = content.parse::<toml::Value>() {
                if let Some(tool) = value.get("tool") {
                    for prefix in &["conda", "pixi"] {
                        if let Some(section) = tool.get(prefix) {
                            extract_toml_value(section, ctx);
                            return;
                        }
                    }
                }
            }
        },
    )
}

fn try_read_yaml_file<T: serde::de::DeserializeOwned>(
    path: &Path,
    ctx: &mut ProjectContext,
    cache: &mut StatCache,
    extract: fn(&T, &mut ProjectContext),
) -> bool {
    if !crate::cache::is_regular_file(path) {
        return false;
    }
    let path_str = path.to_string_lossy();

    if let Some(cached) = cache.get_if_fresh(&path_str) {
        apply_cached_to_project(cached, ctx);
        return true;
    }

    if let Some(content) = crate::cache::read_to_string_limited(path) {
        let mut file_ctx = ProjectContext::default();
        if let Ok(value) = serde_saphyr::from_str::<T>(&content) {
            extract(&value, &mut file_ctx);
        }

        if let Some((mtime, size)) = file_stat(path) {
            cache.update(&path_str, cache_from_project(&file_ctx, mtime, size));
        }

        apply_cached_to_project(
            &CachedFile {
                mtime_secs: 0,
                size: 0,
                env_names: file_ctx.env_names,
                task_names: file_ctx.task_names,
                feature_names: file_ctx.feature_names,
                channels: file_ctx.channels,
                tool_names: Vec::new(),
            },
            ctx,
        );
        return true;
    }
    false
}

// -- YAML typed structs ---------------------------------------------------

#[derive(Deserialize, Default)]
struct EnvironmentYml {
    #[serde(default)]
    name: Option<String>,
    #[serde(default)]
    channels: Vec<String>,
}

#[derive(Deserialize, Default)]
struct AnacondaProjectYml {
    #[serde(default)]
    env_specs: HashMap<String, IgnoredAny>,
    #[serde(default)]
    commands: HashMap<String, IgnoredAny>,
}

#[derive(Deserialize, Default)]
struct CondaProjectYml {
    #[serde(default)]
    environments: HashMap<String, IgnoredAny>,
    #[serde(default)]
    commands: HashMap<String, IgnoredAny>,
}

#[derive(Deserialize, Default)]
struct CondaLockYml {
    #[serde(default)]
    metadata: CondaLockMetadata,
}

#[derive(Deserialize, Default)]
struct CondaLockMetadata {
    #[serde(default)]
    channels: Vec<CondaLockChannel>,
}

#[derive(Deserialize)]
struct CondaLockChannel {
    #[serde(default)]
    url: String,
}

#[derive(Deserialize, Default)]
struct RattlerLock {
    #[serde(default)]
    environments: HashMap<String, RattlerLockEnv>,
}

#[derive(Deserialize, Default)]
struct RattlerLockEnv {
    #[serde(default)]
    channels: Vec<RattlerLockChannel>,
}

#[derive(Deserialize)]
struct RattlerLockChannel {
    #[serde(default)]
    url: String,
}

// -- YAML extractors ------------------------------------------------------

fn try_read_environment_yml(dir: &Path, ctx: &mut ProjectContext, cache: &mut StatCache) {
    try_read_yaml_file::<EnvironmentYml>(
        &dir.join("environment.yml"),
        ctx,
        cache,
        |doc, ctx| {
            if let Some(name) = &doc.name {
                ctx.env_names.push(name.clone());
            }
            ctx.channels.extend(doc.channels.iter().cloned());
        },
    );
}

fn try_read_anaconda_project_yml(
    dir: &Path,
    ctx: &mut ProjectContext,
    cache: &mut StatCache,
) -> bool {
    try_read_yaml_file::<AnacondaProjectYml>(
        &dir.join("anaconda-project.yml"),
        ctx,
        cache,
        |doc, ctx| {
            ctx.env_names.extend(doc.env_specs.keys().cloned());
            ctx.task_names.extend(doc.commands.keys().cloned());
        },
    )
}

fn try_read_conda_project_yml(
    dir: &Path,
    ctx: &mut ProjectContext,
    cache: &mut StatCache,
) -> bool {
    try_read_yaml_file::<CondaProjectYml>(
        &dir.join("conda-project.yml"),
        ctx,
        cache,
        |doc, ctx| {
            ctx.env_names.extend(doc.environments.keys().cloned());
            ctx.task_names.extend(doc.commands.keys().cloned());
        },
    )
}

fn try_read_conda_lock_yml(dir: &Path, ctx: &mut ProjectContext, cache: &mut StatCache) {
    try_read_yaml_file::<CondaLockYml>(
        &dir.join("conda-lock.yml"),
        ctx,
        cache,
        |doc, ctx| {
            for ch in &doc.metadata.channels {
                ctx.channels.push(ch.url.clone());
            }
        },
    );
}

fn try_read_rattler_lock(dir: &Path, ctx: &mut ProjectContext, cache: &mut StatCache) {
    if !try_read_yaml_file::<RattlerLock>(
        &dir.join("conda.lock"),
        ctx,
        cache,
        extract_rattler_lock,
    ) {
        try_read_yaml_file::<RattlerLock>(
            &dir.join("pixi.lock"),
            ctx,
            cache,
            extract_rattler_lock,
        );
    }
}

fn extract_rattler_lock(doc: &RattlerLock, ctx: &mut ProjectContext) {
    ctx.env_names.extend(doc.environments.keys().cloned());
    for env in doc.environments.values() {
        for ch in &env.channels {
            ctx.channels.push(ch.url.clone());
        }
    }
}

// -- TOML extractors (unchanged) ------------------------------------------

fn extract_toml_workspace(content: &str, ctx: &mut ProjectContext) {
    if let Ok(value) = content.parse::<toml::Value>() {
        extract_toml_value(&value, ctx);
    }
}

fn extract_toml_value(value: &toml::Value, ctx: &mut ProjectContext) {
    use std::collections::HashSet;

    let mut seen_envs: HashSet<&str> = HashSet::new();
    let mut seen_tasks: HashSet<&str> = HashSet::new();
    let mut seen_features: HashSet<&str> = HashSet::new();
    let mut seen_channels: HashSet<&str> = HashSet::new();

    if let Some(table) = value.get("environments").and_then(|v| v.as_table()) {
        for key in table.keys() {
            if seen_envs.insert(key.as_str()) {
                ctx.env_names.push(key.clone());
            }
        }
    }

    if let Some(table) = value.get("tasks").and_then(|v| v.as_table()) {
        for key in table.keys() {
            if seen_tasks.insert(key.as_str()) {
                ctx.task_names.push(key.clone());
            }
        }
    }

    if let Some(table) = value.get("feature").and_then(|v| v.as_table()) {
        for key in table.keys() {
            if seen_features.insert(key.as_str()) {
                ctx.feature_names.push(key.clone());
            }
        }
    }

    if let Some(workspace) = value.get("workspace") {
        if let Some(channels) = workspace.get("channels") {
            extract_channel_list(channels, ctx, &mut seen_channels);
        }
    }
    if let Some(channels) = value.get("channels") {
        extract_channel_list(channels, ctx, &mut seen_channels);
    }
}

fn extract_channel_list<'a>(
    value: &'a toml::Value,
    ctx: &mut ProjectContext,
    seen: &mut std::collections::HashSet<&'a str>,
) {
    if let Some(arr) = value.as_array() {
        for item in arr {
            if let Some(s) = item.as_str() {
                if seen.insert(s) {
                    ctx.channels.push(s.to_string());
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cache::StatCache;

    #[test]
    fn conda_toml_extracts_envs_tasks_features() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("conda.toml"),
            r#"
[workspace]
channels = ["conda-forge", "bioconda"]

[environments]
dev = {}
prod = {}

[tasks]
build = "make build"
test = "pytest"

[feature]
cuda = {}
"#,
        )
        .unwrap();

        let mut cache = StatCache::default();
        let ctx = ProjectContext::from_cwd(dir.path(), &mut cache);

        assert_eq!(ctx.env_names, vec!["dev", "prod"]);
        assert_eq!(ctx.task_names, vec!["build", "test"]);
        assert_eq!(ctx.feature_names, vec!["cuda"]);
        assert_eq!(ctx.channels, vec!["conda-forge", "bioconda"]);
    }

    #[test]
    fn environment_yml_extracts_name_and_channels() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("environment.yml"),
            "name: myenv\nchannels:\n  - defaults\n  - conda-forge\n",
        )
        .unwrap();

        let mut cache = StatCache::default();
        let ctx = ProjectContext::from_cwd(dir.path(), &mut cache);

        assert_eq!(ctx.env_names, vec!["myenv"]);
        assert_eq!(ctx.channels, vec!["defaults", "conda-forge"]);
    }

    #[test]
    fn anaconda_project_yml_extracts_envs_and_commands() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("anaconda-project.yml"),
            "env_specs:\n  default: {}\n  gpu: {}\ncommands:\n  serve:\n    unix: python app.py\n",
        )
        .unwrap();

        let mut cache = StatCache::default();
        let ctx = ProjectContext::from_cwd(dir.path(), &mut cache);

        assert!(ctx.env_names.contains(&"default".to_string()));
        assert!(ctx.env_names.contains(&"gpu".to_string()));
        assert!(ctx.task_names.contains(&"serve".to_string()));
    }

    #[test]
    fn conda_project_yml_extracts_envs_and_commands() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("conda-project.yml"),
            "environments:\n  dev: {}\n  ci: {}\ncommands:\n  lint:\n    cmd: ruff check\n",
        )
        .unwrap();

        let mut cache = StatCache::default();
        let ctx = ProjectContext::from_cwd(dir.path(), &mut cache);

        assert!(ctx.env_names.contains(&"dev".to_string()));
        assert!(ctx.env_names.contains(&"ci".to_string()));
        assert!(ctx.task_names.contains(&"lint".to_string()));
    }

    #[test]
    fn conda_lock_yml_extracts_channels() {
        let dir = tempfile::tempdir().unwrap();
        // conda.toml is needed to trigger lockfile reading
        std::fs::write(dir.path().join("conda.toml"), "[workspace]\n").unwrap();
        std::fs::write(
            dir.path().join("conda-lock.yml"),
            "metadata:\n  channels:\n    - url: https://conda.anaconda.org/conda-forge\n    - url: https://conda.anaconda.org/bioconda\n",
        )
        .unwrap();

        let mut cache = StatCache::default();
        let ctx = ProjectContext::from_cwd(dir.path(), &mut cache);

        assert!(ctx.channels.contains(&"https://conda.anaconda.org/conda-forge".to_string()));
        assert!(ctx.channels.contains(&"https://conda.anaconda.org/bioconda".to_string()));
    }

    #[test]
    fn rattler_lock_extracts_envs_and_channels() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("conda.toml"), "[workspace]\n").unwrap();
        std::fs::write(
            dir.path().join("conda.lock"),
            "version: 6\nenvironments:\n  default:\n    channels:\n      - url: https://conda.anaconda.org/conda-forge\n  test:\n    channels:\n      - url: https://conda.anaconda.org/conda-forge\n",
        )
        .unwrap();

        let mut cache = StatCache::default();
        let ctx = ProjectContext::from_cwd(dir.path(), &mut cache);

        assert!(ctx.env_names.contains(&"default".to_string()));
        assert!(ctx.env_names.contains(&"test".to_string()));
        assert!(ctx.channels.contains(&"https://conda.anaconda.org/conda-forge".to_string()));
    }

    #[test]
    fn pixi_lock_fallback_when_no_conda_lock() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("pixi.toml"), "[workspace]\n").unwrap();
        std::fs::write(
            dir.path().join("pixi.lock"),
            "version: 6\nenvironments:\n  default:\n    channels:\n      - url: https://conda.anaconda.org/conda-forge\n",
        )
        .unwrap();

        let mut cache = StatCache::default();
        let ctx = ProjectContext::from_cwd(dir.path(), &mut cache);

        assert!(ctx.env_names.contains(&"default".to_string()));
    }

    #[test]
    fn conda_toml_takes_priority_over_environment_yml() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("conda.toml"),
            "[environments]\nfromtoml = {}\n",
        )
        .unwrap();
        std::fs::write(
            dir.path().join("environment.yml"),
            "name: fromyml\n",
        )
        .unwrap();

        let mut cache = StatCache::default();
        let ctx = ProjectContext::from_cwd(dir.path(), &mut cache);

        assert!(ctx.env_names.contains(&"fromtoml".to_string()));
        assert!(!ctx.env_names.contains(&"fromyml".to_string()));
    }

    #[test]
    fn empty_directory_returns_empty_context() {
        let dir = tempfile::tempdir().unwrap();
        let mut cache = StatCache::default();
        let ctx = ProjectContext::from_cwd(dir.path(), &mut cache);

        assert!(ctx.env_names.is_empty());
        assert!(ctx.task_names.is_empty());
        assert!(ctx.channels.is_empty());
    }

    #[test]
    fn pyproject_toml_extracts_tool_conda_section() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("pyproject.toml"),
            r#"
[tool.conda.environments]
dev = {}

[tool.conda.tasks]
check = "ruff check"

[tool.conda.workspace]
channels = ["conda-forge"]
"#,
        )
        .unwrap();

        let mut cache = StatCache::default();
        let ctx = ProjectContext::from_cwd(dir.path(), &mut cache);

        assert_eq!(ctx.env_names, vec!["dev"]);
        assert_eq!(ctx.task_names, vec!["check"]);
        assert_eq!(ctx.channels, vec!["conda-forge"]);
    }

    #[test]
    fn cache_prevents_reparse() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("environment.yml"),
            "name: cached\nchannels:\n  - defaults\n",
        )
        .unwrap();

        let mut cache = StatCache::default();
        let ctx1 = ProjectContext::from_cwd(dir.path(), &mut cache);
        assert_eq!(ctx1.env_names, vec!["cached"]);

        // Second call should use cache
        let ctx2 = ProjectContext::from_cwd(dir.path(), &mut cache);
        assert_eq!(ctx2.env_names, vec!["cached"]);
        assert_eq!(cache.files.len(), 1);
    }
}
