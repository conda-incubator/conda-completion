use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::io::{Read, Seek, SeekFrom};
use std::path::Path;

#[derive(Debug, Serialize, Deserialize)]
pub struct Manifest {
    #[allow(dead_code)]
    pub version: u32,
    #[allow(dead_code)]
    pub generated_at: Option<String>,
    #[allow(dead_code)]
    pub plugin_hash: Option<String>,
    #[serde(default)]
    pub package_names: Vec<String>,
    #[serde(default)]
    pub commands: BTreeMap<String, CommandSpec>,
    #[serde(default)]
    pub root_options: BTreeMap<String, OptionSpec>,
    #[serde(default)]
    pub aliases: BTreeMap<String, AliasSpec>,
    #[serde(default)]
    pub runtime_sources: BTreeMap<String, RuntimeSourceSpec>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct CommandSpec {
    pub summary: Option<String>,
    #[serde(default)]
    pub options: BTreeMap<String, OptionSpec>,
    #[serde(default)]
    pub positionals: Vec<PositionalSpec>,
    #[serde(default)]
    pub subcommands: BTreeMap<String, CommandSpec>,
    #[serde(default)]
    #[allow(dead_code)]
    pub exclusive_groups: Vec<Vec<String>>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct OptionSpec {
    pub short: Option<String>,
    pub choices: Option<Vec<String>>,
    pub nargs: Option<String>,
    pub completion_type: Option<String>,
    pub description: Option<String>,
    pub metavar: Option<String>,
    #[allow(dead_code)]
    pub default: Option<String>,
    #[serde(default)]
    #[allow(dead_code)]
    pub required: bool,
    #[serde(default)]
    pub group: Option<String>,
}

impl OptionSpec {
    pub fn takes_value(&self) -> bool {
        if self.choices.is_some() || self.completion_type.is_some() || self.metavar.is_some() {
            return true;
        }
        !matches!(self.nargs.as_deref(), Some("0") | None)
    }

    pub fn is_greedy(&self) -> bool {
        matches!(self.nargs.as_deref(), Some("*") | Some("+"))
    }
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct PositionalSpec {
    #[allow(dead_code)]
    pub name: String,
    pub choices: Option<Vec<String>>,
    #[allow(dead_code)]
    pub nargs: Option<String>,
    pub completion_type: Option<String>,
    pub completion: Option<CompletionSpec>,
    #[allow(dead_code)]
    pub description: Option<String>,
    #[allow(dead_code)]
    pub metavar: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct CompletionSpec {
    #[serde(default)]
    pub sources: Vec<String>,
    #[serde(default)]
    pub rules: Vec<CompletionRule>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct CompletionRule {
    #[serde(default)]
    pub sources: Vec<String>,
    #[serde(default)]
    pub when_options: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AliasSpec {
    #[serde(default)]
    pub target: Vec<String>,
    #[allow(dead_code)]
    pub description: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct RuntimeSourceSpec {
    pub kind: String,
    #[allow(dead_code)]
    pub description: Option<String>,
    pub group: Option<String>,
    pub env_var: Option<String>,
    #[serde(default)]
    pub env_suffix: Vec<String>,
    #[serde(default)]
    pub home_suffix: Vec<String>,
    pub entry_type: Option<String>,
    pub strip_suffix: Option<String>,
    pub max_entries: Option<usize>,
}

const MAX_PACKAGE_NAMES: usize = 2_000_000;
const MAX_VERSIONS_ENTRIES: usize = 2_000_000;
const MAX_VERSION_RECORD_SIZE: u64 = 1024 * 1024;

pub fn load_manifest(path: &Path) -> Result<Manifest, Box<dyn std::error::Error>> {
    let bytes = crate::cache::read_to_bytes_limited(path)
        .ok_or("manifest file not found, is a symlink, or exceeds size limit")?;
    let manifest: Manifest = rmp_serde::from_slice(&bytes)?;
    if manifest.package_names.len() > MAX_PACKAGE_NAMES {
        return Err("manifest contains too many package names".into());
    }
    Ok(manifest)
}

pub fn load_package_versions(
    index_path: &Path,
    package_name: &str,
) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    if package_name.is_empty() {
        return Err("package name is empty".into());
    }
    let bytes = crate::cache::read_to_bytes_limited(index_path)
        .ok_or("package versions index not found, is a symlink, or exceeds size limit")?;
    let index: BTreeMap<String, (u64, u64)> = rmp_serde::from_slice(&bytes)?;
    let (offset, length) = index
        .get(package_name)
        .copied()
        .ok_or("package not found in versions index")?;
    if length > MAX_VERSION_RECORD_SIZE {
        return Err("package versions record exceeds size limit".into());
    }

    let store_path = index_path.with_file_name("versions.store");
    let metadata = std::fs::symlink_metadata(&store_path)?;
    if !metadata.file_type().is_file() {
        return Err("package versions store is not a regular file".into());
    }
    let end = offset
        .checked_add(length)
        .ok_or("package versions index offset overflow")?;
    if end > metadata.len() {
        return Err("package versions index points outside store".into());
    }
    let mut store = std::fs::File::open(&store_path)?;
    store.seek(SeekFrom::Start(offset))?;
    let mut bytes = vec![0; length as usize];
    store.read_exact(&mut bytes)?;
    let versions: Vec<String> = rmp_serde::from_slice(&bytes)?;
    if versions.len() > MAX_VERSIONS_ENTRIES {
        return Err("package versions file contains too many entries".into());
    }
    Ok(versions)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn minimal_manifest() -> Manifest {
        Manifest {
            version: 1,
            generated_at: Some("2026-01-01T00:00:00Z".to_string()),
            plugin_hash: None,
            package_names: vec![],
            commands: BTreeMap::from([
                (
                    "install".to_string(),
                    CommandSpec {
                        summary: Some("Install packages".to_string()),
                        options: BTreeMap::from([
                            (
                                "--name".to_string(),
                                OptionSpec {
                                    short: Some("-n".to_string()),
                                    choices: None,
                                    nargs: None,
                                    completion_type: Some("env_name".to_string()),
                                    description: Some("Environment name".to_string()),
                                    metavar: None,
                                    default: None,
                                    required: false,
                                    group: None,
                                },
                            ),
                            (
                                "--verbose".to_string(),
                                OptionSpec {
                                    short: None,
                                    choices: None,
                                    nargs: None,
                                    completion_type: None,
                                    description: Some("Be verbose".to_string()),
                                    metavar: None,
                                    default: None,
                                    required: false,
                                    group: None,
                                },
                            ),
                        ]),
                        positionals: vec![],
                        subcommands: BTreeMap::new(),
                        exclusive_groups: vec![],
                    },
                ),
                (
                    "remove".to_string(),
                    CommandSpec {
                        summary: Some("Remove packages".to_string()),
                        options: BTreeMap::new(),
                        positionals: vec![],
                        subcommands: BTreeMap::new(),
                        exclusive_groups: vec![],
                    },
                ),
            ]),
            root_options: BTreeMap::from([(
                "--debug".to_string(),
                OptionSpec {
                    short: None,
                    choices: None,
                    nargs: None,
                    completion_type: None,
                    description: Some("Debug mode".to_string()),
                    metavar: None,
                    default: None,
                    required: false,
                    group: None,
                },
            )]),
            aliases: BTreeMap::new(),
            runtime_sources: BTreeMap::new(),
        }
    }

    fn minimal_manifest_bytes() -> Vec<u8> {
        rmp_serde::to_vec(&minimal_manifest()).unwrap()
    }

    #[test]
    fn parse_minimal_manifest() {
        let bytes = minimal_manifest_bytes();
        let m: Manifest = rmp_serde::from_slice(&bytes).unwrap();
        assert_eq!(m.version, 1);
        assert_eq!(m.commands.len(), 2);
        assert!(m.commands.contains_key("install"));
        assert!(m.commands.contains_key("remove"));
    }

    #[test]
    fn parse_command_options() {
        let bytes = minimal_manifest_bytes();
        let m: Manifest = rmp_serde::from_slice(&bytes).unwrap();
        let install = &m.commands["install"];
        assert_eq!(install.summary.as_deref(), Some("Install packages"));
        let name_opt = &install.options["--name"];
        assert_eq!(name_opt.short.as_deref(), Some("-n"));
        assert_eq!(name_opt.completion_type.as_deref(), Some("env_name"));
    }

    #[test]
    fn parse_root_options() {
        let bytes = minimal_manifest_bytes();
        let m: Manifest = rmp_serde::from_slice(&bytes).unwrap();
        assert!(m.root_options.contains_key("--debug"));
    }

    #[test]
    fn parse_aliases_and_completion_rules() {
        let manifest = Manifest {
            version: 1,
            generated_at: None,
            plugin_hash: None,
            package_names: vec![],
            commands: BTreeMap::from([(
                "exec".to_string(),
                CommandSpec {
                    summary: None,
                    options: BTreeMap::new(),
                    positionals: vec![PositionalSpec {
                        name: "tool".to_string(),
                        choices: None,
                        nargs: None,
                        completion_type: None,
                        completion: Some(CompletionSpec {
                            sources: vec!["cached_tool".to_string(), "package_spec".to_string()],
                            rules: vec![CompletionRule {
                                sources: vec!["cached_tool".to_string()],
                                when_options: vec!["--clean".to_string()],
                            }],
                        }),
                        description: None,
                        metavar: None,
                    }],
                    subcommands: BTreeMap::new(),
                    exclusive_groups: vec![],
                },
            )]),
            root_options: BTreeMap::new(),
            aliases: BTreeMap::from([(
                "ce".to_string(),
                AliasSpec {
                    target: vec!["exec".to_string()],
                    description: None,
                },
            )]),
            runtime_sources: BTreeMap::from([(
                "cached_tool".to_string(),
                RuntimeSourceSpec {
                    kind: "directory_entries".to_string(),
                    description: Some("cached tool".to_string()),
                    group: Some("tool".to_string()),
                    env_var: Some("TOOL_HOME".to_string()),
                    env_suffix: vec!["envs".to_string()],
                    home_suffix: vec![".tools".to_string(), "envs".to_string()],
                    entry_type: Some("directory".to_string()),
                    strip_suffix: Some("--".to_string()),
                    max_entries: Some(10_000),
                },
            )]),
        };

        let bytes = rmp_serde::to_vec(&manifest).unwrap();
        let parsed: Manifest = rmp_serde::from_slice(&bytes).unwrap();
        let completion = parsed.commands["exec"].positionals[0]
            .completion
            .as_ref()
            .unwrap();

        assert_eq!(parsed.aliases["ce"].target, vec!["exec"]);
        assert_eq!(completion.sources, vec!["cached_tool", "package_spec"]);
        assert_eq!(completion.rules[0].when_options, vec!["--clean"]);
        assert_eq!(
            parsed.runtime_sources["cached_tool"].kind,
            "directory_entries"
        );
    }

    #[test]
    fn takes_value_with_completion_type() {
        let opt = OptionSpec {
            short: None,
            choices: None,
            nargs: None,
            completion_type: Some("env_name".to_string()),
            description: None,
            metavar: None,
            default: None,
            required: false,
            group: None,
        };
        assert!(opt.takes_value());
    }

    #[test]
    fn takes_value_with_choices() {
        let opt = OptionSpec {
            short: None,
            choices: Some(vec!["a".to_string()]),
            nargs: None,
            completion_type: None,
            description: None,
            metavar: None,
            default: None,
            required: false,
            group: None,
        };
        assert!(opt.takes_value());
    }

    #[test]
    fn takes_value_with_metavar() {
        let opt = OptionSpec {
            short: None,
            choices: None,
            nargs: None,
            completion_type: None,
            description: None,
            metavar: Some("NAME".to_string()),
            default: None,
            required: false,
            group: None,
        };
        assert!(opt.takes_value());
    }

    #[test]
    fn boolean_flag_does_not_take_value() {
        let opt = OptionSpec {
            short: None,
            choices: None,
            nargs: Some("0".to_string()),
            completion_type: None,
            description: None,
            metavar: None,
            default: None,
            required: false,
            group: None,
        };
        assert!(!opt.takes_value());
    }

    #[test]
    fn bare_flag_does_not_take_value() {
        let opt = OptionSpec {
            short: None,
            choices: None,
            nargs: None,
            completion_type: None,
            description: None,
            metavar: None,
            default: None,
            required: false,
            group: None,
        };
        assert!(!opt.takes_value());
    }

    #[test]
    fn is_greedy_star() {
        let opt = OptionSpec {
            short: None,
            choices: None,
            nargs: Some("*".to_string()),
            completion_type: None,
            description: None,
            metavar: Some("PKG".to_string()),
            default: None,
            required: false,
            group: None,
        };
        assert!(opt.is_greedy());
        assert!(opt.takes_value());
    }

    #[test]
    fn is_greedy_plus() {
        let opt = OptionSpec {
            short: None,
            choices: None,
            nargs: Some("+".to_string()),
            completion_type: None,
            description: None,
            metavar: Some("PKG".to_string()),
            default: None,
            required: false,
            group: None,
        };
        assert!(opt.is_greedy());
    }

    #[test]
    fn is_not_greedy_single() {
        let opt = OptionSpec {
            short: None,
            choices: None,
            nargs: Some("1".to_string()),
            completion_type: None,
            description: None,
            metavar: None,
            default: None,
            required: false,
            group: None,
        };
        assert!(!opt.is_greedy());
    }

    #[test]
    fn load_manifest_from_file() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("manifest.msgpack");
        let bytes = minimal_manifest_bytes();
        std::fs::write(&path, &bytes).unwrap();

        let m = load_manifest(&path).unwrap();
        assert_eq!(m.version, 1);
        assert_eq!(m.commands.len(), 2);
    }

    #[test]
    fn load_manifest_missing_file() {
        let result = load_manifest(Path::new("/nonexistent/manifest.msgpack"));
        assert!(result.is_err());
    }

    #[test]
    fn load_package_versions_from_indexed_store() {
        let dir = tempfile::tempdir().unwrap();
        let index_path = dir.path().join("versions.index");
        let store_path = dir.path().join("versions.store");
        let record = rmp_serde::to_vec(&vec!["2.0".to_string(), "1.26".to_string()]).unwrap();
        std::fs::write(&store_path, &record).unwrap();
        std::fs::write(
            &index_path,
            rmp_serde::to_vec(&BTreeMap::from([(
                "numpy".to_string(),
                (0_u64, record.len() as u64),
            )]))
            .unwrap(),
        )
        .unwrap();

        let versions = load_package_versions(&index_path, "numpy").unwrap();

        assert_eq!(versions, vec!["2.0", "1.26"]);
    }

    #[test]
    fn load_package_versions_rejects_out_of_bounds_index() {
        let dir = tempfile::tempdir().unwrap();
        let index_path = dir.path().join("versions.index");
        let store_path = dir.path().join("versions.store");
        std::fs::write(&store_path, b"short").unwrap();
        std::fs::write(
            &index_path,
            rmp_serde::to_vec(&BTreeMap::from([("numpy".to_string(), (0_u64, 10_u64))])).unwrap(),
        )
        .unwrap();

        let result = load_package_versions(&index_path, "numpy");

        assert!(result.is_err());
    }

    #[test]
    fn nested_subcommands() {
        let manifest = Manifest {
            version: 1,
            generated_at: None,
            plugin_hash: None,
            package_names: vec![],
            commands: BTreeMap::from([(
                "workspace".to_string(),
                CommandSpec {
                    summary: Some("Workspace commands".to_string()),
                    options: BTreeMap::new(),
                    positionals: vec![],
                    subcommands: BTreeMap::from([(
                        "install".to_string(),
                        CommandSpec {
                            summary: Some("Install workspace".to_string()),
                            options: BTreeMap::from([(
                                "--environment".to_string(),
                                OptionSpec {
                                    short: Some("-e".to_string()),
                                    choices: None,
                                    nargs: None,
                                    completion_type: Some("env_name".to_string()),
                                    description: Some("Target environment".to_string()),
                                    metavar: None,
                                    default: None,
                                    required: false,
                                    group: None,
                                },
                            )]),
                            positionals: vec![],
                            subcommands: BTreeMap::new(),
                            exclusive_groups: vec![],
                        },
                    )]),
                    exclusive_groups: vec![],
                },
            )]),
            root_options: BTreeMap::new(),
            aliases: BTreeMap::new(),
            runtime_sources: BTreeMap::new(),
        };
        let bytes = rmp_serde::to_vec(&manifest).unwrap();
        let m: Manifest = rmp_serde::from_slice(&bytes).unwrap();
        let ws = &m.commands["workspace"];
        assert!(ws.subcommands.contains_key("install"));
        let install = &ws.subcommands["install"];
        assert!(install.options.contains_key("--environment"));
    }
}
