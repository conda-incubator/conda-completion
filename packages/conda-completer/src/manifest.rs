use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
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
    #[allow(dead_code)]
    pub description: Option<String>,
    #[allow(dead_code)]
    pub metavar: Option<String>,
}

const MAX_PACKAGE_NAMES: usize = 2_000_000;
const MAX_VERSIONS_ENTRIES: usize = 2_000_000;

pub fn load_manifest(path: &Path) -> Result<Manifest, Box<dyn std::error::Error>> {
    let bytes = crate::cache::read_to_bytes_limited(path)
        .ok_or("manifest file not found, is a symlink, or exceeds size limit")?;
    let manifest: Manifest = rmp_serde::from_slice(&bytes)?;
    if manifest.package_names.len() > MAX_PACKAGE_NAMES {
        return Err("manifest contains too many package names".into());
    }
    Ok(manifest)
}

pub fn load_versions(
    path: &Path,
) -> Result<BTreeMap<String, Vec<String>>, Box<dyn std::error::Error>> {
    let bytes = crate::cache::read_to_bytes_limited(path)
        .ok_or("versions file not found, is a symlink, or exceeds size limit")?;
    let versions: BTreeMap<String, Vec<String>> = rmp_serde::from_slice(&bytes)?;
    if versions.len() > MAX_VERSIONS_ENTRIES {
        return Err("versions file contains too many entries".into());
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
                },
            )]),
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
        };
        let bytes = rmp_serde::to_vec(&manifest).unwrap();
        let m: Manifest = rmp_serde::from_slice(&bytes).unwrap();
        let ws = &m.commands["workspace"];
        assert!(ws.subcommands.contains_key("install"));
        let install = &ws.subcommands["install"];
        assert!(install.options.contains_key("--environment"));
    }
}
