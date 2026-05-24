use crate::similarity::normalized_damerau_levenshtein;

const MAX_FUZZY_LEN: usize = 128;

pub fn matches(candidate: &str, prefix: &str) -> bool {
    if prefix.is_empty() {
        return true;
    }
    candidate.starts_with(prefix)
}

pub fn fuzzy_match(
    candidates: &[(String, Option<String>)],
    query: &str,
) -> Vec<(String, Option<String>)> {
    if query.is_empty() {
        return candidates.to_vec();
    }
    if query.len() > MAX_FUZZY_LEN {
        return Vec::new();
    }

    let mut prefix_hits: Vec<_> = candidates
        .iter()
        .filter(|(name, _)| name.starts_with(query))
        .cloned()
        .collect();
    if !prefix_hits.is_empty() {
        prefix_hits.sort_by(|a, b| a.0.len().cmp(&b.0.len()).then_with(|| a.0.cmp(&b.0)));
        return prefix_hits;
    }

    let mut substr_hits: Vec<_> = candidates
        .iter()
        .filter(|(name, _)| name.contains(query))
        .cloned()
        .collect();
    if !substr_hits.is_empty() {
        substr_hits.sort_by(|a, b| a.0.len().cmp(&b.0.len()).then_with(|| a.0.cmp(&b.0)));
        return substr_hits;
    }

    let mut scored: Vec<_> = candidates
        .iter()
        .filter(|(name, _)| name.len() <= MAX_FUZZY_LEN)
        .map(|(name, desc)| {
            let mut score = normalized_damerau_levenshtein(name, query);
            if name.as_bytes().first() == query.as_bytes().first() {
                score *= 1.05;
            }
            (name.clone(), desc.clone(), score)
        })
        .filter(|(_, _, score)| *score > 0.6)
        .collect();
    scored.sort_by(|a, b| b.2.partial_cmp(&a.2).unwrap_or(std::cmp::Ordering::Equal));
    scored
        .into_iter()
        .take(10)
        .map(|(name, desc, _)| (name, desc))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use test_case::test_case;

    #[test_case("install", "", true ; "empty prefix matches")]
    #[test_case("--verbose", "", true ; "empty prefix matches flag")]
    #[test_case("install", "install", true ; "exact match")]
    #[test_case("install", "ins", true ; "prefix match")]
    #[test_case("--verbose", "--v", true ; "flag prefix match")]
    #[test_case("install", "rem", false ; "no match")]
    #[test_case("install", "installs", false ; "longer than candidate")]
    #[test_case("install", "Install", false ; "case sensitive")]
    fn prefix_matches(candidate: &str, prefix: &str, expected: bool) {
        assert_eq!(matches(candidate, prefix), expected);
    }

    fn pkg(name: &str) -> (String, Option<String>) {
        (name.to_string(), Some("package".to_string()))
    }

    #[test]
    fn fuzzy_prefix_tier() {
        let candidates = vec![pkg("numpy"), pkg("numba"), pkg("nose")];
        let results = fuzzy_match(&candidates, "num");
        let names: Vec<&str> = results.iter().map(|(n, _)| n.as_str()).collect();
        assert!(names.contains(&"numpy"));
        assert!(names.contains(&"numba"));
        assert!(!names.contains(&"nose"));
    }

    #[test]
    fn fuzzy_substring_tier() {
        let candidates = vec![pkg("python-dateutil"), pkg("numpy"), pkg("pandas")];
        let results = fuzzy_match(&candidates, "dateutil");
        let names: Vec<&str> = results.iter().map(|(n, _)| n.as_str()).collect();
        assert_eq!(names, vec!["python-dateutil"]);
    }

    #[test_case("numpie", "numpy" ; "typo")]
    #[test_case("nupmy", "numpy" ; "transposition")]
    fn fuzzy_similarity_tier(query: &str, expected_hit: &str) {
        let candidates = vec![pkg("numpy"), pkg("scipy"), pkg("pandas")];
        let results = fuzzy_match(&candidates, query);
        let names: Vec<&str> = results.iter().map(|(n, _)| n.as_str()).collect();
        assert!(names.contains(&expected_hit));
    }

    #[test]
    fn fuzzy_no_results_for_garbage() {
        let candidates = vec![pkg("numpy"), pkg("scipy"), pkg("pandas")];
        let results = fuzzy_match(&candidates, "zzzzzzzzz");
        assert!(results.is_empty());
    }

    #[test]
    fn fuzzy_empty_query_returns_all() {
        let candidates = vec![pkg("numpy"), pkg("scipy")];
        let results = fuzzy_match(&candidates, "");
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn fuzzy_caps_at_ten() {
        let candidates: Vec<_> = (0..20).map(|i| pkg(&format!("pkg{}", i))).collect();
        let results = fuzzy_match(&candidates, "pkx0");
        assert!(results.len() <= 10);
    }
}
