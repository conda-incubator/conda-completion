mod cache;
mod context;
mod global;
mod manifest;
mod matcher;
mod shell;
mod similarity;

use std::env;
use std::path::{Path, PathBuf};
use std::process;

fn main() {
    let args: Vec<String> = env::args().collect();

    if let Some(manifest_path) = parse_alias_args(&args) {
        let manifest = match manifest::load_manifest(&manifest_path) {
            Ok(m) => m,
            Err(e) => {
                eprintln!("Failed to load manifest: {}", e);
                process::exit(1);
            }
        };
        print_aliases(&manifest);
        return;
    }

    let parsed = match parse_args(&args) {
        Some(p) => p,
        None => {
            eprintln!(
                "Usage: _conda_completer --shell <shell> --manifest <path> [--versions <path>] -- <words...> <cword>"
            );
            process::exit(1);
        }
    };

    let manifest = match manifest::load_manifest(&parsed.manifest) {
        Ok(m) => m,
        Err(e) => {
            eprintln!("Failed to load manifest: {}", e);
            process::exit(1);
        }
    };

    let versions_path = parsed
        .versions
        .unwrap_or_else(|| parsed.manifest.with_file_name("versions.index"));

    let cache_path = parsed.manifest.with_file_name("context_cache.msgpack");
    let mut stat_cache = cache::StatCache::load(&cache_path);

    let cwd = env::current_dir().unwrap_or_default();
    let ctx = context::ProjectContext::from_cwd(&cwd, &mut stat_cache);
    let global_ctx = global::GlobalContext::load(&mut stat_cache);

    stat_cache.save(&cache_path);

    let mut candidates = complete(
        &manifest,
        &versions_path,
        &ctx,
        &global_ctx,
        &parsed.words,
        parsed.cword,
    );
    candidates.sort_by(|a, b| a.name.cmp(&b.name));
    const MAX_CANDIDATES: usize = 500;
    candidates.truncate(MAX_CANDIDATES);
    let output = shell::format_candidates(&parsed.shell, &candidates);
    if !output.is_empty() {
        println!("{}", output);
    }
}

fn parse_alias_args(args: &[String]) -> Option<PathBuf> {
    let mut wants_aliases = false;
    let mut manifest_path = None;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--" => break,
            "--aliases" => wants_aliases = true,
            "--manifest" => {
                i += 1;
                manifest_path = args.get(i).map(PathBuf::from);
            }
            _ => {}
        }
        i += 1;
    }

    if wants_aliases {
        manifest_path
    } else {
        None
    }
}

fn print_aliases(manifest: &manifest::Manifest) {
    for name in manifest.aliases.keys() {
        println!("{}", name);
    }
}

struct ParsedArgs {
    shell: String,
    manifest: PathBuf,
    versions: Option<PathBuf>,
    words: Vec<String>,
    cword: usize,
}

fn parse_args(args: &[String]) -> Option<ParsedArgs> {
    let mut shell = None;
    let mut manifest_path = None;
    let mut versions_path = None;
    let mut separator_idx = None;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--shell" => {
                i += 1;
                shell = args.get(i).cloned();
            }
            "--manifest" => {
                i += 1;
                manifest_path = args.get(i).map(PathBuf::from);
            }
            "--versions" => {
                i += 1;
                versions_path = args.get(i).map(PathBuf::from);
            }
            "--" => {
                separator_idx = Some(i);
                break;
            }
            _ => {}
        }
        i += 1;
    }

    let shell = shell?;
    let manifest_path = manifest_path?;
    let sep = separator_idx?;

    let remaining = &args[sep + 1..];
    if remaining.is_empty() {
        return None;
    }

    let cword: usize = remaining.last()?.parse().ok()?;
    let words: Vec<String> = remaining[..remaining.len() - 1].to_vec();

    Some(ParsedArgs {
        shell,
        manifest: manifest_path,
        versions: versions_path,
        words,
        cword,
    })
}

use shell::Candidate;

fn complete(
    manifest: &manifest::Manifest,
    versions_path: &std::path::Path,
    ctx: &context::ProjectContext,
    global_ctx: &global::GlobalContext,
    words: &[String],
    cword: usize,
) -> Vec<Candidate> {
    let (normalized_words, normalized_cword) = normalize_alias(manifest, words, cword);
    let words = normalized_words.as_slice();
    let cword = normalized_cword;
    let current_word = words.get(cword).map(|s| s.as_str()).unwrap_or("");

    let mut current_cmd: Option<&manifest::CommandSpec> = None;
    let mut expecting_value_for: Option<&manifest::OptionSpec> = None;
    let mut greedy_flag: Option<&manifest::OptionSpec> = None;
    let mut used_flags: std::collections::HashSet<String> = std::collections::HashSet::new();

    for (i, word) in words.iter().enumerate().skip(1) {
        if i >= cword {
            break;
        }

        if greedy_flag.is_some() {
            if word.starts_with('-') {
                greedy_flag = None;
            } else {
                continue;
            }
        }

        if expecting_value_for.is_some() {
            expecting_value_for = None;
            continue;
        }

        if word.starts_with('-') {
            let options = match current_cmd {
                Some(cmd) => &cmd.options,
                None => &manifest.root_options,
            };
            let flag_name = word.split('=').next().unwrap_or(word);
            used_flags.insert(flag_name.to_string());
            if let Some((canonical_name, opt)) = find_option(options, flag_name) {
                used_flags.insert(canonical_name.to_string());
                if opt.takes_value() && !word.contains('=') {
                    if opt.is_greedy() {
                        greedy_flag = Some(opt);
                    } else {
                        expecting_value_for = Some(opt);
                    }
                }
            }
            continue;
        }

        if let Some(cmd) = current_cmd {
            if let Some(sub) = cmd.subcommands.get(word.as_str()) {
                current_cmd = Some(sub);
                continue;
            }
        } else if let Some(cmd) = manifest.commands.get(word.as_str()) {
            current_cmd = Some(cmd);
            continue;
        }
    }

    if let Some(opt) = expecting_value_for {
        return complete_flag_value(opt, manifest, versions_path, ctx, global_ctx, current_word);
    }
    if let Some(opt) = greedy_flag {
        if !current_word.starts_with('-') {
            return complete_flag_value(
                opt,
                manifest,
                versions_path,
                ctx,
                global_ctx,
                current_word,
            );
        }
    }

    let mut candidates = Vec::new();

    if current_word.starts_with('-') {
        let options = match current_cmd {
            Some(cmd) => &cmd.options,
            None => &manifest.root_options,
        };
        let exclusive_groups = match current_cmd {
            Some(cmd) => &cmd.exclusive_groups,
            None => &Vec::new(),
        };
        let excluded = excluded_flags(&used_flags, exclusive_groups);
        let long_prefix = current_word.starts_with("--");
        for (name, opt) in options {
            if excluded.contains(name.as_str()) {
                continue;
            }
            let group = opt.group.as_deref().unwrap_or("option").to_string();
            if long_prefix {
                if matcher::matches(name, current_word) {
                    candidates.push(Candidate {
                        name: name.clone(),
                        description: opt.description.clone(),
                        group: group.clone(),
                    });
                }
            } else if let Some(short) = &opt.short {
                if !excluded.contains(short.as_str()) && matcher::matches(short, current_word) {
                    candidates.push(Candidate {
                        name: short.clone(),
                        description: opt.description.clone(),
                        group,
                    });
                }
            }
        }
        return candidates;
    }

    if let Some(cmd) = current_cmd {
        for (name, sub) in &cmd.subcommands {
            if matcher::matches(name, current_word) {
                candidates.push(Candidate {
                    name: name.clone(),
                    description: sub.summary.clone(),
                    group: "subcommand".into(),
                });
            }
        }

        for pos in &cmd.positionals {
            candidates.extend(complete_positional(
                pos,
                manifest,
                versions_path,
                ctx,
                global_ctx,
                &used_flags,
                current_word,
            ));
            if let Some(ref choices) = pos.choices {
                for choice in choices {
                    if matcher::matches(choice, current_word) {
                        candidates.push(Candidate {
                            name: choice.clone(),
                            description: None,
                            group: "choice".into(),
                        });
                    }
                }
            }
        }
    } else {
        for (name, cmd) in &manifest.commands {
            if matcher::matches(name, current_word) {
                candidates.push(Candidate {
                    name: name.clone(),
                    description: cmd.summary.clone(),
                    group: "subcommand".into(),
                });
            }
        }
    }

    candidates
}

fn normalize_alias(
    manifest: &manifest::Manifest,
    words: &[String],
    cword: usize,
) -> (Vec<String>, usize) {
    let Some(first) = words.first() else {
        return (Vec::new(), cword);
    };
    let Some(alias) = manifest.aliases.get(first) else {
        return (words.to_vec(), cword);
    };
    if alias.target.is_empty() {
        return (words.to_vec(), cword);
    }

    let mut normalized = Vec::with_capacity(words.len() + alias.target.len());
    normalized.push("conda".to_string());
    normalized.extend(alias.target.iter().cloned());
    normalized.extend(words.iter().skip(1).cloned());
    (normalized, cword.saturating_add(alias.target.len()))
}

fn find_option<'a>(
    options: &'a std::collections::BTreeMap<String, manifest::OptionSpec>,
    flag_name: &str,
) -> Option<(&'a str, &'a manifest::OptionSpec)> {
    if let Some((name, opt)) = options.get_key_value(flag_name) {
        return Some((name.as_str(), opt));
    }
    options
        .iter()
        .find(|(_, opt)| opt.short.as_deref() == Some(flag_name))
        .map(|(name, opt)| (name.as_str(), opt))
}

fn complete_flag_value(
    opt: &manifest::OptionSpec,
    manifest: &manifest::Manifest,
    versions_path: &std::path::Path,
    ctx: &context::ProjectContext,
    global_ctx: &global::GlobalContext,
    current_word: &str,
) -> Vec<Candidate> {
    if let Some(ref choices) = opt.choices {
        return choices
            .iter()
            .filter(|c| matcher::matches(c, current_word))
            .map(|c| Candidate {
                name: c.clone(),
                description: None,
                group: "choice".into(),
            })
            .collect();
    }

    if let Some(ref comp_type) = opt.completion_type {
        return resolve_dynamic(
            comp_type,
            manifest,
            versions_path,
            ctx,
            global_ctx,
            current_word,
        );
    }

    Vec::new()
}

fn complete_positional(
    pos: &manifest::PositionalSpec,
    manifest: &manifest::Manifest,
    versions_path: &std::path::Path,
    ctx: &context::ProjectContext,
    global_ctx: &global::GlobalContext,
    used_flags: &std::collections::HashSet<String>,
    current_word: &str,
) -> Vec<Candidate> {
    let mut candidates = Vec::new();

    if let Some(completion) = &pos.completion {
        let sources = completion
            .rules
            .iter()
            .find(|rule| {
                rule.when_options
                    .iter()
                    .all(|option| used_flags.contains(option))
            })
            .map(|rule| rule.sources.as_slice())
            .unwrap_or(completion.sources.as_slice());
        for comp_type in sources {
            candidates.extend(resolve_dynamic(
                comp_type,
                manifest,
                versions_path,
                ctx,
                global_ctx,
                current_word,
            ));
        }
        return candidates;
    }

    if let Some(ref comp_type) = pos.completion_type {
        candidates.extend(resolve_dynamic(
            comp_type,
            manifest,
            versions_path,
            ctx,
            global_ctx,
            current_word,
        ));
    }

    candidates
}

fn excluded_flags(
    used: &std::collections::HashSet<String>,
    exclusive_groups: &[Vec<String>],
) -> std::collections::HashSet<String> {
    let mut excluded: std::collections::HashSet<String> = used.iter().cloned().collect();
    for group in exclusive_groups {
        if group.iter().any(|f| used.contains(f)) {
            for f in group {
                excluded.insert(f.clone());
            }
        }
    }
    excluded
}

fn collect_matching(
    sources: &[&[String]],
    description: &str,
    group: &str,
    current_word: &str,
    candidates: &mut Vec<Candidate>,
) {
    let mut seen = std::collections::HashSet::new();
    for source in sources {
        for name in *source {
            if matcher::matches(name, current_word) && seen.insert(name.as_str()) {
                candidates.push(Candidate {
                    name: name.clone(),
                    description: Some(description.to_string()),
                    group: group.to_string(),
                });
            }
        }
    }
}

fn resolve_dynamic(
    comp_type: &str,
    manifest: &manifest::Manifest,
    versions_path: &std::path::Path,
    ctx: &context::ProjectContext,
    global_ctx: &global::GlobalContext,
    current_word: &str,
) -> Vec<Candidate> {
    let mut candidates = Vec::new();

    match comp_type {
        "env_name" => collect_matching(
            &[&ctx.env_names, &global_ctx.env_names],
            "environment",
            "environment",
            current_word,
            &mut candidates,
        ),
        "channel" => collect_matching(
            &[&ctx.channels, &global_ctx.channels],
            "channel",
            "channel",
            current_word,
            &mut candidates,
        ),
        "task_name" => collect_matching(
            &[&ctx.task_names],
            "task",
            "task",
            current_word,
            &mut candidates,
        ),
        "global_tool" => collect_matching(
            &[&global_ctx.tool_names],
            "global tool",
            "tool",
            current_word,
            &mut candidates,
        ),
        "package_spec" => {
            if current_word.contains('=') {
                let sep = if current_word.contains("==") {
                    "=="
                } else {
                    "="
                };
                let pkg_name = current_word.split('=').next().unwrap_or("");
                if let Ok(versions) = manifest::load_package_versions(versions_path, pkg_name) {
                    for v in &versions {
                        let candidate = format!("{}{}{}", pkg_name, sep, v);
                        if matcher::matches(&candidate, current_word) {
                            candidates.push(Candidate {
                                name: candidate,
                                description: None,
                                group: "version".into(),
                            });
                        }
                    }
                }
            } else if !current_word.is_empty() {
                candidates.extend(
                    matcher::fuzzy_match_names(&manifest.package_names, current_word)
                        .into_iter()
                        .map(|name| Candidate {
                            name,
                            description: None,
                            group: "package".into(),
                        }),
                );
            }
        }
        "directory" => {
            candidates.push(Candidate {
                name: String::new(),
                description: None,
                group: "directory".into(),
            });
        }
        "file" | "path" => {
            candidates.push(Candidate {
                name: String::new(),
                description: None,
                group: "file".into(),
            });
        }
        _ => {
            if let Some(source) = manifest.runtime_sources.get(comp_type) {
                candidates.extend(resolve_runtime_source(
                    comp_type,
                    source,
                    global_ctx,
                    current_word,
                ));
            }
        }
    }

    candidates
}

const DEFAULT_RUNTIME_SOURCE_LIMIT: usize = 10_000;

fn resolve_runtime_source(
    name: &str,
    source: &manifest::RuntimeSourceSpec,
    global_ctx: &global::GlobalContext,
    current_word: &str,
) -> Vec<Candidate> {
    match source.kind.as_str() {
        "directory_entries" => {
            let Some(path) = runtime_source_dir(source, global_ctx.home.as_deref()) else {
                return Vec::new();
            };
            complete_directory_entries(name, source, &path, current_word)
        }
        _ => Vec::new(),
    }
}

fn runtime_source_dir(
    source: &manifest::RuntimeSourceSpec,
    home: Option<&Path>,
) -> Option<PathBuf> {
    if let Some(env_var) = &source.env_var {
        if let Some(value) = env::var_os(env_var).filter(|value| !value.is_empty()) {
            return Some(append_segments(PathBuf::from(value), &source.env_suffix));
        }
    }
    if source.home_suffix.is_empty() {
        return None;
    }
    home.map(|path| append_segments(path.to_path_buf(), &source.home_suffix))
}

fn append_segments(mut path: PathBuf, segments: &[String]) -> PathBuf {
    for segment in segments {
        path.push(segment);
    }
    path
}

fn complete_directory_entries(
    source_name: &str,
    source: &manifest::RuntimeSourceSpec,
    path: &Path,
    current_word: &str,
) -> Vec<Candidate> {
    let Ok(entries) = fs_err::read_dir(path) else {
        return Vec::new();
    };

    let group = source.group.as_deref().unwrap_or(source_name);
    let description = source.description.as_deref().unwrap_or(group);
    let limit = source
        .max_entries
        .unwrap_or(DEFAULT_RUNTIME_SOURCE_LIMIT)
        .min(DEFAULT_RUNTIME_SOURCE_LIMIT);
    let mut seen = std::collections::HashSet::new();
    let mut candidates = Vec::new();

    for entry in entries.flatten() {
        if candidates.len() >= limit {
            break;
        }
        if !entry_matches_type(&entry, source.entry_type.as_deref()) {
            continue;
        }
        let Some(name) = runtime_entry_name(&entry.file_name(), source.strip_suffix.as_deref())
        else {
            continue;
        };
        if matcher::matches(&name, current_word) && seen.insert(name.clone()) {
            candidates.push(Candidate {
                name,
                description: Some(description.to_string()),
                group: group.to_string(),
            });
        }
    }

    candidates.sort_by(|a, b| a.name.cmp(&b.name));
    candidates
}

fn entry_matches_type(entry: &fs_err::DirEntry, entry_type: Option<&str>) -> bool {
    let Ok(file_type) = entry.file_type() else {
        return false;
    };
    match entry_type {
        Some("directory") => file_type.is_dir(),
        Some("file") => file_type.is_file(),
        Some("any") | None => true,
        _ => false,
    }
}

fn runtime_entry_name(name: &std::ffi::OsStr, strip_suffix: Option<&str>) -> Option<String> {
    let name = name.to_str()?;
    let Some(delimiter) = strip_suffix else {
        return (!name.is_empty()).then(|| name.to_string());
    };
    let (candidate, suffix) = name.rsplit_once(delimiter)?;
    if candidate.is_empty() || suffix.is_empty() {
        return None;
    }
    Some(candidate.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_manifest() -> manifest::Manifest {
        manifest::Manifest {
            version: 1,
            generated_at: None,
            plugin_hash: None,
            package_names: vec![],
            root_options: std::collections::BTreeMap::from([
                (
                    "--debug".to_string(),
                    manifest::OptionSpec {
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
                ),
                (
                    "--verbose".to_string(),
                    manifest::OptionSpec {
                        short: Some("-v".to_string()),
                        choices: None,
                        nargs: None,
                        completion_type: None,
                        description: Some("Verbose".to_string()),
                        metavar: None,
                        default: None,
                        required: false,
                        group: None,
                    },
                ),
            ]),
            commands: std::collections::BTreeMap::from([
                (
                    "install".to_string(),
                    manifest::CommandSpec {
                        summary: Some("Install packages".to_string()),
                        options: std::collections::BTreeMap::from([
                            (
                                "--name".to_string(),
                                manifest::OptionSpec {
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
                                "--channel".to_string(),
                                manifest::OptionSpec {
                                    short: Some("-c".to_string()),
                                    choices: None,
                                    nargs: None,
                                    completion_type: Some("channel".to_string()),
                                    description: Some("Channel".to_string()),
                                    metavar: None,
                                    default: None,
                                    required: false,
                                    group: None,
                                },
                            ),
                            (
                                "--dry-run".to_string(),
                                manifest::OptionSpec {
                                    short: None,
                                    choices: None,
                                    nargs: None,
                                    completion_type: None,
                                    description: Some("Dry run".to_string()),
                                    metavar: None,
                                    default: None,
                                    required: false,
                                    group: None,
                                },
                            ),
                        ]),
                        positionals: vec![],
                        subcommands: std::collections::BTreeMap::new(),
                        exclusive_groups: vec![],
                    },
                ),
                (
                    "remove".to_string(),
                    manifest::CommandSpec {
                        summary: Some("Remove packages".to_string()),
                        options: std::collections::BTreeMap::new(),
                        positionals: vec![],
                        subcommands: std::collections::BTreeMap::new(),
                        exclusive_groups: vec![],
                    },
                ),
                (
                    "workspace".to_string(),
                    manifest::CommandSpec {
                        summary: Some("Workspace commands".to_string()),
                        options: std::collections::BTreeMap::new(),
                        positionals: vec![],
                        subcommands: std::collections::BTreeMap::from([
                            (
                                "install".to_string(),
                                manifest::CommandSpec {
                                    summary: Some("Install workspace".to_string()),
                                    options: std::collections::BTreeMap::from([(
                                        "--environment".to_string(),
                                        manifest::OptionSpec {
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
                                    subcommands: std::collections::BTreeMap::new(),
                                    exclusive_groups: vec![],
                                },
                            ),
                            (
                                "list".to_string(),
                                manifest::CommandSpec {
                                    summary: Some("List workspaces".to_string()),
                                    options: std::collections::BTreeMap::new(),
                                    positionals: vec![],
                                    subcommands: std::collections::BTreeMap::new(),
                                    exclusive_groups: vec![],
                                },
                            ),
                        ]),
                        exclusive_groups: vec![],
                    },
                ),
            ]),
            aliases: std::collections::BTreeMap::new(),
            runtime_sources: std::collections::BTreeMap::new(),
        }
    }

    fn empty_ctx() -> context::ProjectContext {
        context::ProjectContext::default()
    }

    fn empty_global() -> global::GlobalContext {
        global::GlobalContext::default()
    }

    fn words(s: &str) -> Vec<String> {
        s.split_whitespace().map(String::from).collect()
    }

    fn names(candidates: &[Candidate]) -> Vec<&str> {
        candidates.iter().map(|c| c.name.as_str()).collect()
    }

    fn no_versions() -> PathBuf {
        PathBuf::from("/nonexistent/versions")
    }

    fn config_keys() -> Vec<String> {
        vec![
            "channels".to_string(),
            "envs_dirs".to_string(),
            "pkgs_dirs".to_string(),
        ]
    }

    fn config_key_option(nargs: Option<&str>) -> manifest::OptionSpec {
        manifest::OptionSpec {
            short: None,
            choices: Some(config_keys()),
            nargs: nargs.map(str::to_string),
            completion_type: None,
            description: Some("Config key".to_string()),
            metavar: Some("KEY".to_string()),
            default: None,
            required: false,
            group: None,
        }
    }

    fn config_manifest() -> manifest::Manifest {
        manifest::Manifest {
            version: 1,
            generated_at: None,
            plugin_hash: None,
            package_names: vec![],
            root_options: std::collections::BTreeMap::new(),
            commands: std::collections::BTreeMap::from([(
                "config".to_string(),
                manifest::CommandSpec {
                    summary: Some("Modify configuration values".to_string()),
                    options: std::collections::BTreeMap::from([
                        ("--show".to_string(), config_key_option(Some("*"))),
                        ("--add".to_string(), config_key_option(Some("2"))),
                        ("--set".to_string(), config_key_option(Some("2"))),
                        ("--remove-key".to_string(), config_key_option(None)),
                    ]),
                    positionals: vec![],
                    subcommands: std::collections::BTreeMap::new(),
                    exclusive_groups: vec![],
                },
            )]),
            aliases: std::collections::BTreeMap::new(),
            runtime_sources: std::collections::BTreeMap::new(),
        }
    }

    fn health_manifest() -> manifest::Manifest {
        manifest::Manifest {
            version: 1,
            generated_at: None,
            plugin_hash: None,
            package_names: vec![],
            root_options: std::collections::BTreeMap::new(),
            commands: std::collections::BTreeMap::from([(
                "doctor".to_string(),
                manifest::CommandSpec {
                    summary: Some("Run health checks".to_string()),
                    options: std::collections::BTreeMap::new(),
                    positionals: vec![manifest::PositionalSpec {
                        name: "checks".to_string(),
                        choices: Some(vec![
                            "altered-files".to_string(),
                            "base-protection".to_string(),
                            "pinned".to_string(),
                        ]),
                        nargs: Some("*".to_string()),
                        completion_type: None,
                        completion: None,
                        description: Some("Health checks".to_string()),
                        metavar: Some("NAME".to_string()),
                    }],
                    subcommands: std::collections::BTreeMap::new(),
                    exclusive_groups: vec![],
                },
            )]),
            aliases: std::collections::BTreeMap::new(),
            runtime_sources: std::collections::BTreeMap::new(),
        }
    }

    fn conda_exec_manifest() -> manifest::Manifest {
        manifest::Manifest {
            version: 1,
            generated_at: None,
            plugin_hash: None,
            package_names: vec!["numpy".to_string(), "scipy".to_string()],
            root_options: std::collections::BTreeMap::new(),
            commands: std::collections::BTreeMap::from([(
                "exec".to_string(),
                manifest::CommandSpec {
                    summary: Some("Run a tool".to_string()),
                    options: std::collections::BTreeMap::from([
                        (
                            "--clean".to_string(),
                            manifest::OptionSpec {
                                short: None,
                                choices: None,
                                nargs: None,
                                completion_type: None,
                                description: Some("Clean cached tools".to_string()),
                                metavar: None,
                                default: None,
                                required: false,
                                group: None,
                            },
                        ),
                        (
                            "--lock".to_string(),
                            manifest::OptionSpec {
                                short: None,
                                choices: None,
                                nargs: None,
                                completion_type: None,
                                description: Some("Lock a script".to_string()),
                                metavar: None,
                                default: None,
                                required: false,
                                group: None,
                            },
                        ),
                    ]),
                    positionals: vec![manifest::PositionalSpec {
                        name: "tool".to_string(),
                        choices: None,
                        nargs: None,
                        completion_type: None,
                        completion: Some(manifest::CompletionSpec {
                            sources: vec!["cached_tool".to_string(), "package_spec".to_string()],
                            rules: vec![
                                manifest::CompletionRule {
                                    sources: vec!["cached_tool".to_string()],
                                    when_options: vec!["--clean".to_string()],
                                },
                                manifest::CompletionRule {
                                    sources: vec!["file".to_string()],
                                    when_options: vec!["--lock".to_string()],
                                },
                            ],
                        }),
                        description: None,
                        metavar: None,
                    }],
                    subcommands: std::collections::BTreeMap::new(),
                    exclusive_groups: vec![],
                },
            )]),
            aliases: std::collections::BTreeMap::from([(
                "ce".to_string(),
                manifest::AliasSpec {
                    target: vec!["exec".to_string()],
                    description: None,
                },
            )]),
            runtime_sources: std::collections::BTreeMap::from([(
                "cached_tool".to_string(),
                manifest::RuntimeSourceSpec {
                    kind: "directory_entries".to_string(),
                    description: Some("cached tool".to_string()),
                    group: Some("tool".to_string()),
                    env_var: None,
                    env_suffix: vec![],
                    home_suffix: vec!["exec-cache".to_string(), "envs".to_string()],
                    entry_type: Some("directory".to_string()),
                    strip_suffix: Some("--".to_string()),
                    max_entries: Some(10_000),
                },
            )]),
        }
    }

    fn cached_tool_global(tool_names: &[&str]) -> (tempfile::TempDir, global::GlobalContext) {
        let dir = tempfile::tempdir().unwrap();
        let envs = dir.path().join("exec-cache").join("envs");
        fs_err::create_dir_all(&envs).unwrap();
        for (index, tool_name) in tool_names.iter().enumerate() {
            fs_err::create_dir_all(envs.join(format!("{tool_name}--hash{index}"))).unwrap();
        }
        fs_err::create_dir_all(envs.join("missing-delimiter")).unwrap();
        fs_err::write(envs.join("not-a-dir--hash"), "").unwrap();

        let mut global = empty_global();
        global.home = Some(dir.path().to_path_buf());
        (dir, global)
    }

    #[test]
    fn parse_args_valid() {
        let args: Vec<String> = vec![
            "bin",
            "--shell",
            "bash",
            "--manifest",
            "/path/m.toml",
            "--",
            "conda",
            "inst",
            "2",
        ]
        .into_iter()
        .map(String::from)
        .collect();

        let parsed = parse_args(&args).unwrap();
        assert_eq!(parsed.shell, "bash");
        assert_eq!(parsed.manifest, PathBuf::from("/path/m.toml"));
        assert!(parsed.versions.is_none());
        assert_eq!(parsed.words, vec!["conda", "inst"]);
        assert_eq!(parsed.cword, 2);
    }

    #[test]
    fn parse_args_missing_shell() {
        let args: Vec<String> = vec!["bin", "--manifest", "/m.toml", "--", "conda", "1"]
            .into_iter()
            .map(String::from)
            .collect();
        assert!(parse_args(&args).is_none());
    }

    #[test]
    fn parse_alias_args_valid() {
        let args: Vec<String> = vec!["bin", "--aliases", "--manifest", "/path/m.msgpack"]
            .into_iter()
            .map(String::from)
            .collect();

        assert_eq!(
            parse_alias_args(&args).unwrap(),
            PathBuf::from("/path/m.msgpack"),
        );
    }

    #[test]
    fn parse_alias_args_ignores_completion_mode() {
        let args: Vec<String> = vec![
            "bin",
            "--shell",
            "bash",
            "--manifest",
            "/path/m.msgpack",
            "--",
            "conda",
            "1",
        ]
        .into_iter()
        .map(String::from)
        .collect();

        assert!(parse_alias_args(&args).is_none());
    }

    #[test]
    fn parse_alias_args_ignores_user_words_after_separator() {
        let args: Vec<String> = vec![
            "bin",
            "--shell",
            "bash",
            "--manifest",
            "/path/m.msgpack",
            "--",
            "conda",
            "exec",
            "--aliases",
            "3",
        ]
        .into_iter()
        .map(String::from)
        .collect();

        assert!(parse_alias_args(&args).is_none());
    }

    #[test]
    fn parse_args_missing_separator() {
        let args: Vec<String> = vec!["bin", "--shell", "bash", "--manifest", "/m.toml"]
            .into_iter()
            .map(String::from)
            .collect();
        assert!(parse_args(&args).is_none());
    }

    #[test]
    fn parse_args_empty_after_separator() {
        let args: Vec<String> = vec!["bin", "--shell", "bash", "--manifest", "/m.toml", "--"]
            .into_iter()
            .map(String::from)
            .collect();
        assert!(parse_args(&args).is_none());
    }

    #[test]
    fn complete_top_level_commands() {
        let m = test_manifest();
        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda "),
            1,
        );
        let n = names(&result);
        assert!(n.contains(&"install"));
        assert!(n.contains(&"remove"));
        assert!(n.contains(&"workspace"));
    }

    #[test]
    fn complete_top_level_with_prefix() {
        let m = test_manifest();
        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda ins"),
            1,
        );
        let n = names(&result);
        assert!(n.contains(&"install"));
        assert!(!n.contains(&"remove"));
    }

    #[test]
    fn complete_subcommand_flags() {
        let m = test_manifest();
        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda install --"),
            2,
        );
        let n = names(&result);
        assert!(n.contains(&"--name"));
        assert!(n.contains(&"--channel"));
        assert!(n.contains(&"--dry-run"));
    }

    #[test]
    fn complete_flag_short_form() {
        let m = test_manifest();
        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda install -"),
            2,
        );
        let n = names(&result);
        assert!(n.contains(&"-n"));
        assert!(n.contains(&"-c"));
    }

    #[test]
    fn complete_nested_subcommands() {
        let m = test_manifest();
        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda workspace "),
            2,
        );
        let n = names(&result);
        assert!(n.contains(&"install"));
        assert!(n.contains(&"list"));
    }

    #[test]
    fn complete_dynamic_env_name() {
        let m = test_manifest();
        let mut ctx = empty_ctx();
        ctx.env_names = vec!["myenv".to_string(), "test".to_string()];

        let result = complete(
            &m,
            &no_versions(),
            &ctx,
            &empty_global(),
            &words("conda install --name m"),
            3,
        );
        let n = names(&result);
        assert!(n.contains(&"myenv"));
        assert!(!n.contains(&"test"));
    }

    #[test]
    fn complete_dynamic_channel() {
        let m = test_manifest();
        let mut ctx = empty_ctx();
        ctx.channels = vec!["conda-forge".to_string(), "bioconda".to_string()];

        let result = complete(
            &m,
            &no_versions(),
            &ctx,
            &empty_global(),
            &words("conda install --channel c"),
            3,
        );
        let n = names(&result);
        assert!(n.contains(&"conda-forge"));
        assert!(!n.contains(&"bioconda"));
    }

    #[test]
    fn complete_root_flags() {
        let m = test_manifest();
        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda --"),
            1,
        );
        let n = names(&result);
        assert!(n.contains(&"--debug"));
        assert!(n.contains(&"--verbose"));
    }

    #[test]
    fn complete_flag_value_skips_to_next_word() {
        let m = test_manifest();
        let mut ctx = empty_ctx();
        ctx.env_names = vec!["dev".to_string()];

        let result = complete(
            &m,
            &no_versions(),
            &ctx,
            &empty_global(),
            &words("conda install --name dev "),
            4,
        );
        let n = names(&result);
        assert!(!n.contains(&"--name"));
    }

    #[test]
    fn complete_flag_equals_value_syntax() {
        let m = test_manifest();
        let mut ctx = empty_ctx();
        ctx.env_names = vec!["dev".to_string()];

        let result = complete(
            &m,
            &no_versions(),
            &ctx,
            &empty_global(),
            &words("conda install --channel=conda-forge --name "),
            4,
        );
        let n = names(&result);
        assert!(n.contains(&"dev"));
    }

    #[test]
    fn complete_short_flag_value() {
        let m = test_manifest();
        let mut ctx = empty_ctx();
        ctx.env_names = vec!["myenv".to_string()];

        let result = complete(
            &m,
            &no_versions(),
            &ctx,
            &empty_global(),
            &words("conda install -n "),
            3,
        );
        let n = names(&result);
        assert!(n.contains(&"myenv"));
    }

    #[test]
    fn complete_greedy_nargs_consumes_multiple_values() {
        let m = manifest::Manifest {
            version: 1,
            generated_at: None,
            plugin_hash: None,
            package_names: vec![],
            root_options: std::collections::BTreeMap::new(),
            commands: std::collections::BTreeMap::from([(
                "install".to_string(),
                manifest::CommandSpec {
                    summary: Some("Install packages".to_string()),
                    options: std::collections::BTreeMap::from([
                        (
                            "--packages".to_string(),
                            manifest::OptionSpec {
                                short: None,
                                choices: None,
                                nargs: Some("*".to_string()),
                                completion_type: None,
                                description: Some("Packages to install".to_string()),
                                metavar: Some("PKG".to_string()),
                                default: None,
                                required: false,
                                group: None,
                            },
                        ),
                        (
                            "--name".to_string(),
                            manifest::OptionSpec {
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
                    ]),
                    positionals: vec![],
                    subcommands: std::collections::BTreeMap::new(),
                    exclusive_groups: vec![],
                },
            )]),
            aliases: std::collections::BTreeMap::new(),
            runtime_sources: std::collections::BTreeMap::new(),
        };

        let mut ctx = empty_ctx();
        ctx.env_names = vec!["dev".to_string()];

        let result = complete(
            &m,
            &no_versions(),
            &ctx,
            &empty_global(),
            &words("conda install --packages foo bar --name "),
            6,
        );
        let n = names(&result);
        assert!(
            n.contains(&"dev"),
            "should complete env name after greedy flag ends"
        );
    }

    #[test]
    fn complete_greedy_flag_value_choices() {
        let m = config_manifest();

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda config --show chan"),
            3,
        );
        let n = names(&result);

        assert!(n.contains(&"channels"));
        assert!(!n.contains(&"envs_dirs"));
    }

    #[test]
    fn complete_greedy_flag_value_choices_after_existing_value() {
        let m = config_manifest();

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda config --show channels pk"),
            4,
        );
        let n = names(&result);

        assert!(n.contains(&"pkgs_dirs"));
        assert!(!n.contains(&"channels"));
    }

    #[test]
    fn complete_two_value_flag_choices_only_first_value() {
        let m = config_manifest();

        let first_value = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda config --set chan"),
            3,
        );
        let first_names = names(&first_value);
        assert!(first_names.contains(&"channels"));

        let second_value = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda config --set channels conda-forge"),
            4,
        );
        assert!(second_value.is_empty());
    }

    #[test]
    fn complete_single_value_config_key_flag_choices() {
        let m = config_manifest();

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda config --remove-key env"),
            3,
        );
        let n = names(&result);

        assert!(n.contains(&"envs_dirs"));
        assert!(!n.contains(&"channels"));
    }

    #[test]
    fn complete_config_parameter_alias_flag_choices() {
        let m = config_manifest();

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda config --add env"),
            3,
        );
        let n = names(&result);

        assert!(n.contains(&"envs_dirs"));
        assert!(!n.contains(&"channels"));
    }

    #[test]
    fn complete_health_check_positional_choices() {
        let m = health_manifest();

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda doctor pin"),
            2,
        );
        let n = names(&result);

        assert!(n.contains(&"pinned"));
        assert!(!n.contains(&"altered-files"));
    }

    #[test]
    fn complete_global_env_names() {
        let m = test_manifest();
        let mut global = empty_global();
        global.env_names = vec!["base".to_string(), "globalenv".to_string()];

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &global,
            &words("conda install --name "),
            3,
        );
        let n = names(&result);
        assert!(n.contains(&"base"));
        assert!(n.contains(&"globalenv"));
    }

    #[test]
    fn complete_conda_exec_tool_and_package_sources() {
        let m = conda_exec_manifest();
        let (_dir, global) = cached_tool_global(&["ruff", "pytest"]);

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &global,
            &words("conda exec py"),
            2,
        );
        let n = names(&result);
        assert!(n.contains(&"pytest"));

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &global,
            &words("conda exec num"),
            2,
        );
        let n = names(&result);
        assert!(n.contains(&"numpy"));
    }

    #[test]
    fn complete_conda_exec_clean_uses_cached_tools_only() {
        let m = conda_exec_manifest();
        let (_dir, global) = cached_tool_global(&["ruff"]);

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &global,
            &words("conda exec --clean num"),
            3,
        );
        let n = names(&result);
        assert!(!n.contains(&"numpy"));

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &global,
            &words("conda exec --clean r"),
            3,
        );
        let n = names(&result);
        assert!(n.contains(&"ruff"));
    }

    #[test]
    fn complete_conda_exec_lock_uses_file_completion() {
        let m = conda_exec_manifest();

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda exec --lock "),
            3,
        );

        assert_eq!(result[0].group, "file");
    }

    #[test]
    fn complete_alias_uses_target_command_path() {
        let m = conda_exec_manifest();
        let (_dir, global) = cached_tool_global(&["ruff"]);

        let result = complete(&m, &no_versions(), &empty_ctx(), &global, &words("ce r"), 1);
        let n = names(&result);
        assert!(n.contains(&"ruff"));
    }

    #[test]
    fn complete_user_alias_flag_stays_in_completion_mode() {
        let m = test_manifest();

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda --aliases --"),
            2,
        );
        let n = names(&result);
        assert!(n.contains(&"--debug"));
    }

    #[test]
    fn runtime_source_without_home_suffix_does_not_complete_home() {
        let m = manifest::Manifest {
            version: 1,
            generated_at: None,
            plugin_hash: None,
            package_names: vec![],
            root_options: std::collections::BTreeMap::new(),
            commands: std::collections::BTreeMap::from([(
                "exec".to_string(),
                manifest::CommandSpec {
                    summary: None,
                    options: std::collections::BTreeMap::new(),
                    positionals: vec![manifest::PositionalSpec {
                        name: "tool".to_string(),
                        choices: None,
                        nargs: None,
                        completion_type: Some("cached_tool".to_string()),
                        completion: None,
                        description: None,
                        metavar: None,
                    }],
                    subcommands: std::collections::BTreeMap::new(),
                    exclusive_groups: vec![],
                },
            )]),
            aliases: std::collections::BTreeMap::new(),
            runtime_sources: std::collections::BTreeMap::from([(
                "cached_tool".to_string(),
                manifest::RuntimeSourceSpec {
                    kind: "directory_entries".to_string(),
                    description: Some("cached tool".to_string()),
                    group: Some("tool".to_string()),
                    env_var: Some("CONDA_COMPLETION_TEST_UNSET".to_string()),
                    env_suffix: vec!["envs".to_string()],
                    home_suffix: vec![],
                    entry_type: Some("directory".to_string()),
                    strip_suffix: Some("--".to_string()),
                    max_entries: Some(10_000),
                },
            )]),
        };
        let dir = tempfile::tempdir().unwrap();
        fs_err::create_dir_all(dir.path().join("ruff--hash")).unwrap();
        let mut global = empty_global();
        global.home = Some(dir.path().to_path_buf());
        env::remove_var("CONDA_COMPLETION_TEST_UNSET");

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &global,
            &words("conda exec r"),
            2,
        );

        assert!(result.is_empty());
    }

    #[test]
    fn runtime_source_with_home_suffix_completes_home_path() {
        let mut m = conda_exec_manifest();
        m.runtime_sources.get_mut("cached_tool").unwrap().env_var =
            Some("CONDA_COMPLETION_TEST_UNSET".to_string());
        let (_dir, global) = cached_tool_global(&["ruff"]);
        env::remove_var("CONDA_COMPLETION_TEST_UNSET");

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &global,
            &words("conda exec r"),
            2,
        );
        let n = names(&result);

        assert!(n.contains(&"ruff"));
    }

    #[test]
    fn empty_prefix_skips_packages() {
        let m = manifest::Manifest {
            version: 1,
            generated_at: None,
            plugin_hash: None,
            package_names: vec!["numpy".to_string(), "scipy".to_string()],
            root_options: std::collections::BTreeMap::new(),
            commands: std::collections::BTreeMap::from([(
                "install".to_string(),
                manifest::CommandSpec {
                    summary: Some("Install".to_string()),
                    options: std::collections::BTreeMap::new(),
                    positionals: vec![manifest::PositionalSpec {
                        name: "packages".to_string(),
                        choices: None,
                        nargs: Some("*".to_string()),
                        completion_type: Some("package_spec".to_string()),
                        completion: None,
                        description: None,
                        metavar: None,
                    }],
                    subcommands: std::collections::BTreeMap::new(),
                    exclusive_groups: vec![],
                },
            )]),
            aliases: std::collections::BTreeMap::new(),
            runtime_sources: std::collections::BTreeMap::new(),
        };

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda install "),
            2,
        );
        let n = names(&result);
        assert!(
            !n.contains(&"numpy"),
            "packages should not appear on empty prefix"
        );
        assert!(
            !n.contains(&"scipy"),
            "packages should not appear on empty prefix"
        );
    }

    #[test]
    fn option_group_passed_to_candidate() {
        let m = manifest::Manifest {
            version: 1,
            generated_at: None,
            plugin_hash: None,
            package_names: vec![],
            root_options: std::collections::BTreeMap::new(),
            commands: std::collections::BTreeMap::from([(
                "install".to_string(),
                manifest::CommandSpec {
                    summary: None,
                    options: std::collections::BTreeMap::from([
                        (
                            "--channel".to_string(),
                            manifest::OptionSpec {
                                short: None,
                                choices: None,
                                nargs: None,
                                completion_type: None,
                                description: None,
                                metavar: Some("CH".to_string()),
                                default: None,
                                required: false,
                                group: Some("Channel Customization".to_string()),
                            },
                        ),
                        (
                            "--verbose".to_string(),
                            manifest::OptionSpec {
                                short: None,
                                choices: None,
                                nargs: None,
                                completion_type: None,
                                description: None,
                                metavar: None,
                                default: None,
                                required: false,
                                group: None,
                            },
                        ),
                    ]),
                    positionals: vec![],
                    subcommands: std::collections::BTreeMap::new(),
                    exclusive_groups: vec![],
                },
            )]),
            aliases: std::collections::BTreeMap::new(),
            runtime_sources: std::collections::BTreeMap::new(),
        };

        let result = complete(
            &m,
            &no_versions(),
            &empty_ctx(),
            &empty_global(),
            &words("conda install --"),
            2,
        );
        let channel = result.iter().find(|c| c.name == "--channel").unwrap();
        assert_eq!(channel.group, "Channel Customization");
        let verbose = result.iter().find(|c| c.name == "--verbose").unwrap();
        assert_eq!(verbose.group, "option");
    }
}
