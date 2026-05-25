use std::borrow::Cow;
use std::fmt::Write;

#[derive(Debug, Clone)]
pub struct Candidate {
    pub name: String,
    pub description: Option<String>,
    pub group: String,
}

fn is_allowed(c: char) -> bool {
    c.is_alphanumeric()
        || matches!(
            c,
            '-' | '.' | '_' | '/' | '=' | '@' | ' ' | ':' | '+' | '~' | '\\'
        )
}

fn sanitize(s: &str) -> Cow<'_, str> {
    if s.chars().all(is_allowed) {
        Cow::Borrowed(s)
    } else {
        Cow::Owned(s.chars().filter(|c| is_allowed(*c)).collect())
    }
}

pub fn format_candidates(shell: &str, candidates: &[Candidate]) -> String {
    let mut out = String::with_capacity(candidates.len() * 32);
    match shell {
        "bash" => format_bash(candidates, &mut out),
        "zsh" => format_zsh(candidates, &mut out),
        "fish" => format_fish(candidates, &mut out),
        "powershell" => format_powershell(candidates, &mut out),
        _ => format_bash(candidates, &mut out),
    }
    out
}

fn format_bash(candidates: &[Candidate], out: &mut String) {
    let mut first = true;
    for c in candidates {
        if c.group == "directory" {
            continue;
        }
        if !first {
            out.push('\n');
        }
        first = false;
        out.push_str(&sanitize(&c.name));
    }
}

fn zsh_escape(s: &str) -> String {
    sanitize(s).replace('\\', "\\\\").replace(':', "\\:")
}

fn truncate_at_word(s: &str, max: usize) -> &str {
    if s.len() <= max {
        return s;
    }
    match s[..max].rfind(' ') {
        Some(i) if i > max / 2 => &s[..i],
        _ => &s[..max],
    }
}

fn format_zsh(candidates: &[Candidate], out: &mut String) {
    let mut first = true;
    for c in candidates {
        if c.group == "directory" {
            if !first {
                out.push('\n');
            }
            first = false;
            out.push_str("__dir__");
            continue;
        }
        if !first {
            out.push('\n');
        }
        first = false;
        let _ = write!(out, "{}\t", c.group);
        let safe_name = zsh_escape(&c.name);
        if let Some(ref d) = c.description {
            let _ = write!(out, "{}:{}", safe_name, zsh_escape(truncate_at_word(d, 80)));
        } else {
            out.push_str(&safe_name);
        }
    }
}

fn format_fish(candidates: &[Candidate], out: &mut String) {
    let mut first = true;
    for c in candidates {
        if c.group == "directory" {
            continue;
        }
        if !first {
            out.push('\n');
        }
        first = false;
        let safe_name = sanitize(&c.name);
        if let Some(ref d) = c.description {
            let _ = write!(out, "{}\t{}", safe_name, sanitize(d));
        } else {
            out.push_str(&safe_name);
        }
    }
}

fn format_powershell(candidates: &[Candidate], out: &mut String) {
    let mut first = true;
    for c in candidates {
        if c.group == "directory" {
            continue;
        }
        if !first {
            out.push('\n');
        }
        first = false;
        let safe_name = sanitize(&c.name);
        if let Some(ref d) = c.description {
            let _ = write!(out, "{}\t{}", safe_name, sanitize(d));
        } else {
            out.push_str(&safe_name);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn c(name: &str, desc: Option<&str>, group: &str) -> Candidate {
        Candidate {
            name: name.to_string(),
            description: desc.map(|s| s.to_string()),
            group: group.to_string(),
        }
    }

    fn candidates() -> Vec<Candidate> {
        vec![
            c("install", Some("Install packages"), "subcommand"),
            c("remove", Some("Remove packages"), "subcommand"),
            c("list", None, "subcommand"),
        ]
    }

    #[test]
    fn bash_one_per_line_no_descriptions() {
        let out = format_candidates("bash", &candidates());
        assert_eq!(out, "install\nremove\nlist");
    }

    #[test]
    fn zsh_grouped_with_descriptions() {
        let out = format_candidates("zsh", &candidates());
        let lines: Vec<&str> = out.lines().collect();
        assert_eq!(lines[0], "subcommand\tinstall:Install packages");
        assert_eq!(lines[1], "subcommand\tremove:Remove packages");
        assert_eq!(lines[2], "subcommand\tlist");
    }

    #[test]
    fn zsh_escapes_colons_in_descriptions() {
        let items = vec![c("flag", Some("Use format: json"), "option")];
        let out = format_candidates("zsh", &items);
        assert_eq!(out, "option\tflag:Use format\\: json");
    }

    #[test]
    fn zsh_directory_marker() {
        let items = vec![
            c("install", Some("Install packages"), "subcommand"),
            c("", None, "directory"),
        ];
        let out = format_candidates("zsh", &items);
        let lines: Vec<&str> = out.lines().collect();
        assert_eq!(lines[0], "subcommand\tinstall:Install packages");
        assert_eq!(lines[1], "__dir__");
    }

    #[test]
    fn bash_skips_directory_marker() {
        let items = vec![c("install", None, "subcommand"), c("", None, "directory")];
        let out = format_candidates("bash", &items);
        assert_eq!(out, "install");
    }

    #[test]
    fn fish_tab_separated() {
        let out = format_candidates("fish", &candidates());
        let lines: Vec<&str> = out.lines().collect();
        assert_eq!(lines[0], "install\tInstall packages");
        assert_eq!(lines[2], "list");
    }

    #[test]
    fn powershell_tab_separated() {
        let out = format_candidates("powershell", &candidates());
        let lines: Vec<&str> = out.lines().collect();
        assert_eq!(lines[0], "install\tInstall packages");
    }

    #[test]
    fn empty_candidates() {
        let out = format_candidates("bash", &[]);
        assert!(out.is_empty());
    }

    #[test]
    fn unknown_shell_falls_back_to_bash() {
        let out = format_candidates("nushell", &candidates());
        assert_eq!(out, format_candidates("bash", &candidates()));
    }

    #[test]
    fn disallowed_characters_stripped_from_candidates() {
        let items = vec![
            c("safe\n$(evil)", Some("desc\ninjected"), "subcommand"),
            c("tab\there", None, "subcommand"),
        ];
        let out = format_candidates("bash", &items);
        assert_eq!(out, "safeevil\ntabhere");

        let out = format_candidates("zsh", &items);
        assert!(!out.contains("$("));
        assert!(!out.contains('\n') || out.lines().count() == 2);
    }

    #[test]
    fn zsh_escapes_colons_in_names() {
        let items = vec![c("https://conda.anaconda.org", None, "channel")];
        let out = format_candidates("zsh", &items);
        assert_eq!(out, "channel\thttps\\://conda.anaconda.org");
    }

    #[test]
    fn zsh_escapes_backslashes() {
        let items = vec![c("foo\\bar", Some("a\\b"), "subcommand")];
        let out = format_candidates("zsh", &items);
        assert_eq!(out, "subcommand\tfoo\\\\bar:a\\\\b");
    }
}
