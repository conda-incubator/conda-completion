use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::path::Path;
use std::time::SystemTime;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct StatCache {
    pub files: BTreeMap<String, CachedFile>,
    #[serde(skip)]
    dirty: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone, Default, PartialEq, Eq)]
pub struct CachedFile {
    pub mtime_secs: u64,
    pub size: u64,
    #[serde(default)]
    pub env_cache_format: u32,
    #[serde(default)]
    pub env_names: Vec<String>,
    #[serde(default)]
    pub env_prefixes: Vec<String>,
    #[serde(default)]
    pub task_names: Vec<String>,
    #[serde(default)]
    pub feature_names: Vec<String>,
    #[serde(default)]
    pub channels: Vec<String>,
    #[serde(default)]
    pub tool_names: Vec<String>,
}

const MAX_CACHE_ENTRIES: usize = 256;

impl StatCache {
    pub fn load(path: &Path) -> Self {
        if let Some(bytes) = read_to_bytes_limited(path) {
            if let Ok(cache) = rmp_serde::from_slice(&bytes) {
                return cache;
            }
        }
        Self::default()
    }

    pub fn save(&self, path: &Path) {
        if std::fs::symlink_metadata(path)
            .map(|m| m.file_type().is_symlink())
            .unwrap_or(false)
        {
            return;
        }

        let mut pruned = self.clone();
        pruned.evict_stale();
        if !pruned.dirty {
            return;
        }

        if let Ok(bytes) = rmp_serde::to_vec(&pruned) {
            let Some(dir) = path.parent() else {
                return;
            };
            let Ok(tmp) = tempfile::NamedTempFile::new_in(dir) else {
                return;
            };
            if std::io::Write::write_all(&mut tmp.as_file(), &bytes).is_ok() {
                let _ = tmp.persist(path);
            }
        }
    }

    fn evict_stale(&mut self) {
        let len_before = self.files.len();
        self.files.retain(|path, _| Path::new(path).exists());
        if self.files.len() != len_before {
            self.dirty = true;
        }

        if self.files.len() > MAX_CACHE_ENTRIES {
            let mut entries: Vec<_> = self
                .files
                .iter()
                .map(|(k, v)| (k.clone(), v.mtime_secs))
                .collect();
            entries.sort_by_key(|(_, mtime)| *mtime);
            let to_remove = self.files.len() - MAX_CACHE_ENTRIES;
            for (key, _) in entries.into_iter().take(to_remove) {
                self.files.remove(&key);
            }
            self.dirty = true;
        }
    }

    pub fn get_if_fresh(&self, file_path: &str) -> Option<&CachedFile> {
        let cached = self.files.get(file_path)?;
        let metadata = std::fs::symlink_metadata(file_path).ok()?;
        if !metadata.file_type().is_file() {
            return None;
        }

        let mtime = metadata
            .modified()
            .unwrap_or(SystemTime::UNIX_EPOCH)
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        if cached.mtime_secs == mtime && cached.size == metadata.len() {
            Some(cached)
        } else {
            None
        }
    }

    pub fn update(&mut self, file_path: &str, entry: CachedFile) {
        if self.files.get(file_path) == Some(&entry) {
            return;
        }
        self.files.insert(file_path.to_string(), entry);
        self.dirty = true;
    }
}

const MAX_FILE_SIZE: u64 = 10 * 1024 * 1024; // 10 MB

pub fn file_stat(path: &Path) -> Option<(u64, u64)> {
    let metadata = std::fs::symlink_metadata(path).ok()?;
    if metadata.file_type().is_symlink() {
        return None;
    }
    let mtime = metadata
        .modified()
        .ok()?
        .duration_since(SystemTime::UNIX_EPOCH)
        .ok()?
        .as_secs();
    Some((mtime, metadata.len()))
}

pub fn is_regular_file(path: &Path) -> bool {
    std::fs::symlink_metadata(path)
        .map(|m| m.file_type().is_file())
        .unwrap_or(false)
}

pub fn read_to_string_limited(path: &Path) -> Option<String> {
    let metadata = std::fs::symlink_metadata(path).ok()?;
    if !metadata.file_type().is_file() || metadata.len() > MAX_FILE_SIZE {
        return None;
    }
    fs_err::read_to_string(path).ok()
}

pub fn read_to_bytes_limited(path: &Path) -> Option<Vec<u8>> {
    let metadata = std::fs::symlink_metadata(path).ok()?;
    if !metadata.file_type().is_file() || metadata.len() > MAX_FILE_SIZE {
        return None;
    }
    fs_err::read(path).ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn load_returns_default_for_missing_file() {
        let cache = StatCache::load(Path::new("/nonexistent/cache.msgpack"));
        assert!(cache.files.is_empty());
    }

    #[test]
    fn save_and_reload_round_trip() {
        let dir = tempfile::tempdir().unwrap();
        let cache_path = dir.path().join("cache.msgpack");
        let real_file = dir.path().join("project.toml");
        std::fs::write(&real_file, "content").unwrap();
        let file_key = real_file.to_str().unwrap();

        let mut cache = StatCache::default();
        cache.update(
            file_key,
            CachedFile {
                mtime_secs: 12345,
                size: 100,
                env_cache_format: 0,
                env_names: vec!["myenv".to_string()],
                env_prefixes: vec![],
                task_names: vec![],
                feature_names: vec![],
                channels: vec!["conda-forge".to_string()],
                tool_names: vec![],
            },
        );
        cache.save(&cache_path);

        let loaded = StatCache::load(&cache_path);
        let entry = loaded.files.get(file_key).unwrap();
        assert_eq!(entry.mtime_secs, 12345);
        assert_eq!(entry.size, 100);
        assert_eq!(entry.env_names, vec!["myenv"]);
        assert_eq!(entry.channels, vec!["conda-forge"]);
    }

    #[test]
    fn save_skips_clean_cache() {
        let dir = tempfile::tempdir().unwrap();
        let cache_path = dir.path().join("cache.msgpack");
        let cache = StatCache::default();

        cache.save(&cache_path);

        assert!(!cache_path.exists());
    }

    #[test]
    fn update_keeps_cache_clean_when_entry_is_unchanged() {
        let dir = tempfile::tempdir().unwrap();
        let cache_path = dir.path().join("cache.msgpack");
        let real_file = dir.path().join("project.toml");
        std::fs::write(&real_file, "content").unwrap();
        let file_key = real_file.to_str().unwrap();
        let entry = CachedFile {
            mtime_secs: 12345,
            size: 100,
            env_cache_format: 0,
            env_names: vec!["myenv".to_string()],
            env_prefixes: vec![],
            task_names: vec![],
            feature_names: vec![],
            channels: vec!["conda-forge".to_string()],
            tool_names: vec![],
        };

        let mut cache = StatCache::default();
        cache.update(file_key, entry.clone());
        cache.save(&cache_path);

        let mut loaded = StatCache::load(&cache_path);
        loaded.update(file_key, entry);

        assert!(!loaded.dirty);
    }

    #[test]
    fn update_marks_cache_dirty_when_entry_changes() {
        let mut cache = StatCache::default();
        cache.update(
            "/tmp/project.toml",
            CachedFile {
                mtime_secs: 12345,
                size: 100,
                env_cache_format: 0,
                env_names: vec!["myenv".to_string()],
                env_prefixes: vec![],
                task_names: vec![],
                feature_names: vec![],
                channels: vec!["conda-forge".to_string()],
                tool_names: vec![],
            },
        );

        assert!(cache.dirty);
    }

    #[test]
    fn get_if_fresh_returns_some_when_stat_matches() {
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("test.toml");
        std::fs::write(&file, "content").unwrap();

        let (mtime, size) = file_stat(&file).unwrap();
        let mut cache = StatCache::default();
        cache.update(
            file.to_str().unwrap(),
            CachedFile {
                mtime_secs: mtime,
                size,
                env_cache_format: 0,
                env_names: vec!["cached".to_string()],
                env_prefixes: vec![],
                task_names: vec![],
                feature_names: vec![],
                channels: vec![],
                tool_names: vec![],
            },
        );

        let result = cache.get_if_fresh(file.to_str().unwrap());
        assert!(result.is_some());
        assert_eq!(result.unwrap().env_names, vec!["cached"]);
    }

    #[test]
    fn get_if_fresh_returns_none_when_size_differs() {
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("test.toml");
        std::fs::write(&file, "short").unwrap();

        let (mtime, _size) = file_stat(&file).unwrap();
        let mut cache = StatCache::default();
        cache.update(
            file.to_str().unwrap(),
            CachedFile {
                mtime_secs: mtime,
                size: 999,
                env_cache_format: 0,
                env_names: vec![],
                env_prefixes: vec![],
                task_names: vec![],
                feature_names: vec![],
                channels: vec![],
                tool_names: vec![],
            },
        );

        assert!(cache.get_if_fresh(file.to_str().unwrap()).is_none());
    }

    #[test]
    fn get_if_fresh_returns_none_for_missing_file() {
        let cache = StatCache::default();
        assert!(cache.get_if_fresh("/nonexistent/file.toml").is_none());
    }

    #[test]
    fn get_if_fresh_returns_none_for_uncached_file() {
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("test.toml");
        std::fs::write(&file, "content").unwrap();

        let cache = StatCache::default();
        assert!(cache.get_if_fresh(file.to_str().unwrap()).is_none());
    }

    #[test]
    fn file_stat_returns_none_for_missing() {
        assert!(file_stat(Path::new("/nonexistent/file")).is_none());
    }

    #[test]
    fn file_stat_returns_correct_size() {
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("sized.txt");
        let mut f = std::fs::File::create(&file).unwrap();
        f.write_all(b"hello").unwrap();
        f.flush().unwrap();
        drop(f);

        let (_, size) = file_stat(&file).unwrap();
        assert_eq!(size, 5);
    }
}
