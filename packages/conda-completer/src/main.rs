mod cache;
mod context;
mod global;
mod manifest;
mod matcher;
mod shell;
mod similarity;

use std::env;
use std::path::PathBuf;
use std::process;

fn main() {
    let args: Vec<String> = env::args().collect();

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

    let versions_path =
        parsed.versions.unwrap_or_else(|| parsed.manifest.with_file_name("versions.msgpack"));

    let cache_path = parsed.manifest.with_file_name("context_cache.msgpack");
    let mut stat_cache = cache::StatCache::load(&cache_path);

    let cwd = env::current_dir().unwrap_or_default();
    let ctx = context::ProjectContext::from_cwd(&cwd, &mut stat_cache);
    let global_ctx = global::GlobalContext::load(&mut stat_cache);

    stat_cache.save(&cache_path);

    let mut candidates = complete(&manifest, &versions_path, &ctx, &global_ctx, &parsed.words, parsed.cword);
    const MAX_CANDIDATES: usize = 500;
    candidates.truncate(MAX_CANDIDATES);
    let output = shell::format_candidates(&parsed.shell, &candidates);
    print!("{}", output);
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

fn complete(
    manifest: &manifest::Manifest,
    versions_path: &std::path::Path,
    ctx: &context::ProjectContext,
    global_ctx: &global::GlobalContext,
    words: &[String],
    cword: usize,
) -> Vec<(String, Option<String>)> {
    let current_word = words.get(cword).map(|s| s.as_str()).unwrap_or("");

    let mut current_cmd: Option<&manifest::CommandSpec> = None;
    let mut expecting_value_for: Option<&manifest::OptionSpec> = None;
    let mut greedy_flag: bool = false;
    let mut used_flags: std::collections::HashSet<String> = std::collections::HashSet::new();

    for (i, word) in words.iter().enumerate().skip(1) {
        if i >= cword {
            break;
        }

        if greedy_flag {
            if word.starts_with('-') {
                greedy_flag = false;
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
            let opt = options.get(flag_name).or_else(|| {
                options
                    .values()
                    .find(|o| o.short.as_deref() == Some(flag_name))
            });
            if let Some(opt) = opt {
                if opt.takes_value() && !word.contains('=') {
                    if opt.is_greedy() {
                        greedy_flag = true;
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
        for (name, opt) in options {
            if excluded.contains(name.as_str()) {
                continue;
            }
            if matcher::matches(name, current_word) {
                candidates.push((name.clone(), opt.description.clone()));
            }
            if let Some(short) = &opt.short {
                if !excluded.contains(short.as_str()) && matcher::matches(short, current_word) {
                    candidates.push((short.clone(), opt.description.clone()));
                }
            }
        }
        return candidates;
    }

    if let Some(cmd) = current_cmd {
        for (name, sub) in &cmd.subcommands {
            if matcher::matches(name, current_word) {
                candidates.push((name.clone(), sub.summary.clone()));
            }
        }

        for pos in &cmd.positionals {
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
            if let Some(ref choices) = pos.choices {
                for choice in choices {
                    if matcher::matches(choice, current_word) {
                        candidates.push((choice.clone(), None));
                    }
                }
            }
        }
    } else {
        for (name, cmd) in &manifest.commands {
            if matcher::matches(name, current_word) {
                candidates.push((name.clone(), cmd.summary.clone()));
            }
        }
    }

    candidates
}

fn complete_flag_value(
    opt: &manifest::OptionSpec,
    manifest: &manifest::Manifest,
    versions_path: &std::path::Path,
    ctx: &context::ProjectContext,
    global_ctx: &global::GlobalContext,
    current_word: &str,
) -> Vec<(String, Option<String>)> {
    if let Some(ref choices) = opt.choices {
        return choices
            .iter()
            .filter(|c| matcher::matches(c, current_word))
            .map(|c| (c.clone(), None))
            .collect();
    }

    if let Some(ref comp_type) = opt.completion_type {
        return resolve_dynamic(comp_type, manifest, versions_path, ctx, global_ctx, current_word);
    }

    Vec::new()
}

fn excluded_flags<'a>(
    used: &'a std::collections::HashSet<String>,
    exclusive_groups: &'a [Vec<String>],
) -> std::collections::HashSet<&'a str> {
    let mut excluded: std::collections::HashSet<&str> = used.iter().map(|s| s.as_str()).collect();
    for group in exclusive_groups {
        if group.iter().any(|f| used.contains(f.as_str())) {
            for f in group {
                excluded.insert(f.as_str());
            }
        }
    }
    excluded
}

fn collect_matching(
    sources: &[&[String]],
    description: &str,
    current_word: &str,
    candidates: &mut Vec<(String, Option<String>)>,
) {
    let desc = Some(description.to_string());
    let mut seen = std::collections::HashSet::new();
    for source in sources {
        for name in *source {
            if matcher::matches(name, current_word) && seen.insert(name.as_str()) {
                candidates.push((name.clone(), desc.clone()));
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
) -> Vec<(String, Option<String>)> {
    let mut candidates = Vec::new();

    match comp_type {
        "env_name" => collect_matching(
            &[&ctx.env_names, &global_ctx.env_names],
            "environment",
            current_word,
            &mut candidates,
        ),
        "channel" => collect_matching(
            &[&ctx.channels, &global_ctx.channels],
            "channel",
            current_word,
            &mut candidates,
        ),
        "task_name" => collect_matching(&[&ctx.task_names], "task", current_word, &mut candidates),
        "global_tool" => collect_matching(
            &[&global_ctx.tool_names],
            "global tool",
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
                            candidates.push((candidate, None));
                        }
                    }
                }
            } else {
                let all_packages: Vec<_> = manifest
                    .package_names
                    .iter()
                    .map(|n| (n.clone(), Some("package".to_string())))
                    .collect();
                candidates.extend(matcher::fuzzy_match(&all_packages, current_word));
            }
        }
        "directory" => {}
        _ => {}
    }

    candidates
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

    fn names(candidates: &[(String, Option<String>)]) -> Vec<&str> {
        candidates.iter().map(|(n, _)| n.as_str()).collect()
    }

    fn no_versions() -> PathBuf {
        PathBuf::from("/nonexistent/versions.msgpack")
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
        let result = complete(&m, &no_versions(), &empty_ctx(), &empty_global(), &words("conda "), 1);
        let n = names(&result);
        assert!(n.contains(&"install"));
        assert!(n.contains(&"remove"));
        assert!(n.contains(&"workspace"));
    }

    #[test]
    fn complete_top_level_with_prefix() {
        let m = test_manifest();
        let result = complete(&m, &no_versions(), &empty_ctx(), &empty_global(), &words("conda ins"), 1);
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
        let result = complete(&m, &no_versions(), &empty_ctx(), &empty_global(), &words("conda --"), 1);
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

        let result = complete(&m, &no_versions(), &ctx, &empty_global(), &words("conda install -n "), 3);
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
                            },
                        ),
                    ]),
                    positionals: vec![],
                    subcommands: std::collections::BTreeMap::new(),
                    exclusive_groups: vec![],
                },
            )]),
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
}
