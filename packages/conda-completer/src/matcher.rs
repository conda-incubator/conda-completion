use crate::similarity::normalized_damerau_levenshtein;

const MAX_FUZZY_LEN: usize = 128;

pub fn matches(candidate: &str, prefix: &str) -> bool {
    if prefix.is_empty() {
        return true;
    }
    candidate.starts_with(prefix)
}

pub fn fuzzy_match_names(candidates: &[String], query: &str) -> Vec<String> {
    if query.is_empty() {
        return candidates.to_vec();
    }
    if query.len() > MAX_FUZZY_LEN {
        return Vec::new();
    }

    let mut prefix_hits: Vec<_> = candidates
        .iter()
        .filter(|name| name.starts_with(query))
        .map(String::to_owned)
        .collect();
    if !prefix_hits.is_empty() {
        prefix_hits.sort_by(|a, b| a.len().cmp(&b.len()).then_with(|| a.cmp(b)));
        return prefix_hits;
    }

    let mut substr_hits: Vec<_> = candidates
        .iter()
        .filter(|name| name.contains(query))
        .map(String::to_owned)
        .collect();
    if !substr_hits.is_empty() {
        substr_hits.sort_by(|a, b| a.len().cmp(&b.len()).then_with(|| a.cmp(b)));
        return substr_hits;
    }

    let mut scored: Vec<_> = candidates
        .iter()
        .filter(|name| name.len() <= MAX_FUZZY_LEN)
        .map(|name| {
            let mut score = normalized_damerau_levenshtein(name, query);
            if name.as_bytes().first() == query.as_bytes().first() {
                score *= 1.05;
            }
            (name.as_str(), score)
        })
        .filter(|(_, score)| *score > 0.6)
        .collect();
    scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    scored
        .into_iter()
        .take(10)
        .map(|(name, _)| name.to_string())
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

    #[test]
    fn fuzzy_no_results_for_garbage() {
        let candidates = vec![
            "numpy".to_string(),
            "scipy".to_string(),
            "pandas".to_string(),
        ];
        let results = fuzzy_match_names(&candidates, "zzzzzzzzz");
        assert!(results.is_empty());
    }

    #[test]
    fn fuzzy_empty_query_returns_all() {
        let candidates = vec!["numpy".to_string(), "scipy".to_string()];
        let results = fuzzy_match_names(&candidates, "");
        assert_eq!(results.len(), 2);
    }

    #[test_case("num", vec!["numba", "numpy"] ; "prefix tier")]
    #[test_case("dateutil", vec!["python-dateutil"] ; "substring tier")]
    #[test_case("numpie", vec!["numpy"] ; "similarity tier")]
    fn fuzzy_match_names_keeps_match_tiers(query: &str, expected: Vec<&str>) {
        let candidates = vec![
            "numpy".to_string(),
            "numba".to_string(),
            "python-dateutil".to_string(),
            "scipy".to_string(),
        ];

        let results = fuzzy_match_names(&candidates, query);

        for name in expected {
            assert!(results.iter().any(|result| result == name));
        }
    }

    #[test]
    fn fuzzy_match_names_caps_at_ten() {
        let names: Vec<String> = (0..20).map(|i| format!("pkg{}", i)).collect();
        let results = fuzzy_match_names(&names, "pkx0");
        assert!(results.len() <= 10);
    }
}
