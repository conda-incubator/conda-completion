/// Check if a candidate matches the current word prefix.
pub fn matches(candidate: &str, prefix: &str) -> bool {
    if prefix.is_empty() {
        return true;
    }
    candidate.starts_with(prefix)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_prefix_matches_everything() {
        assert!(matches("install", ""));
        assert!(matches("--verbose", ""));
    }

    #[test]
    fn exact_match() {
        assert!(matches("install", "install"));
    }

    #[test]
    fn prefix_match() {
        assert!(matches("install", "ins"));
        assert!(matches("--verbose", "--v"));
    }

    #[test]
    fn no_match() {
        assert!(!matches("install", "rem"));
        assert!(!matches("install", "installs"));
    }

    #[test]
    fn case_sensitive() {
        assert!(!matches("install", "Install"));
    }
}
