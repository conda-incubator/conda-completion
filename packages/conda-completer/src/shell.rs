use std::fmt::Write;

pub fn format_candidates(shell: &str, candidates: &[(String, Option<String>)]) -> String {
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

fn format_bash(candidates: &[(String, Option<String>)], out: &mut String) {
    for (i, (name, _)) in candidates.iter().enumerate() {
        if i > 0 {
            out.push('\n');
        }
        out.push_str(name);
    }
}

fn format_zsh(candidates: &[(String, Option<String>)], out: &mut String) {
    for (i, (name, desc)) in candidates.iter().enumerate() {
        if i > 0 {
            out.push('\n');
        }
        if let Some(d) = desc {
            let _ = write!(out, "{}:{}", name, d.replace(':', "\\:"));
        } else {
            out.push_str(name);
        }
    }
}

fn format_fish(candidates: &[(String, Option<String>)], out: &mut String) {
    for (i, (name, desc)) in candidates.iter().enumerate() {
        if i > 0 {
            out.push('\n');
        }
        if let Some(d) = desc {
            let _ = write!(out, "{}\t{}", name, d);
        } else {
            out.push_str(name);
        }
    }
}

fn format_powershell(candidates: &[(String, Option<String>)], out: &mut String) {
    for (i, (name, desc)) in candidates.iter().enumerate() {
        if i > 0 {
            out.push('\n');
        }
        if let Some(d) = desc {
            let _ = write!(out, "{}\t{}", name, d);
        } else {
            out.push_str(name);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn candidates() -> Vec<(String, Option<String>)> {
        vec![
            ("install".to_string(), Some("Install packages".to_string())),
            ("remove".to_string(), Some("Remove packages".to_string())),
            ("list".to_string(), None),
        ]
    }

    #[test]
    fn bash_one_per_line_no_descriptions() {
        let out = format_candidates("bash", &candidates());
        assert_eq!(out, "install\nremove\nlist");
    }

    #[test]
    fn zsh_colon_separated_descriptions() {
        let out = format_candidates("zsh", &candidates());
        let lines: Vec<&str> = out.lines().collect();
        assert_eq!(lines[0], "install:Install packages");
        assert_eq!(lines[1], "remove:Remove packages");
        assert_eq!(lines[2], "list");
    }

    #[test]
    fn zsh_escapes_colons_in_descriptions() {
        let items = vec![(
            "flag".to_string(),
            Some("Use format: json".to_string()),
        )];
        let out = format_candidates("zsh", &items);
        assert_eq!(out, "flag:Use format\\: json");
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
}
