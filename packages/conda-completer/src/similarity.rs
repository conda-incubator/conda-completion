use std::cmp::{max, min};

pub fn damerau_levenshtein(a: &str, b: &str) -> usize {
    let a: Vec<char> = a.chars().collect();
    let b: Vec<char> = b.chars().collect();
    let len_a = a.len();
    let len_b = b.len();

    if len_a == 0 {
        return len_b;
    }
    if len_b == 0 {
        return len_a;
    }

    let w = len_b + 1;
    let mut rows = vec![0usize; w * 3];
    for (j, slot) in rows.iter_mut().take(w).enumerate() {
        *slot = j;
    }

    for i in 1..=len_a {
        let cur = i % 3 * w;
        let prev = ((i + 2) % 3) * w;
        let prev2 = ((i + 1) % 3) * w;
        rows[cur] = i;

        for j in 1..w {
            let cost = if a[i - 1] == b[j - 1] { 0 } else { 1 };
            rows[cur + j] = min(
                min(rows[prev + j] + 1, rows[cur + j - 1] + 1),
                rows[prev + j - 1] + cost,
            );

            if i > 1 && j > 1 && a[i - 1] == b[j - 2] && a[i - 2] == b[j - 1] {
                rows[cur + j] = min(rows[cur + j], rows[prev2 + j - 2] + 1);
            }
        }
    }

    rows[len_a % 3 * w + len_b]
}

pub fn normalized_damerau_levenshtein(a: &str, b: &str) -> f64 {
    let max_len = max(a.len(), b.len());
    if max_len == 0 {
        return 1.0;
    }
    let dist = damerau_levenshtein(a, b);
    1.0 - (dist as f64 / max_len as f64)
}

#[cfg(test)]
mod tests {
    use super::*;
    use test_case::test_case;

    #[test_case("numpy", "numpy", 0 ; "identical")]
    #[test_case("", "", 0 ; "both empty")]
    #[test_case("abc", "", 3 ; "left empty")]
    #[test_case("", "abc", 3 ; "right empty")]
    #[test_case("numpy", "numpx", 1 ; "single substitution")]
    #[test_case("numpy", "nupmy", 1 ; "transposition")]
    #[test_case("scikit-learn", "scikitlearn", 1 ; "missing hyphen")]
    fn distance(a: &str, b: &str, expected: usize) {
        assert_eq!(damerau_levenshtein(a, b), expected);
    }

    #[test_case("numpy", "numpie", 2 ; "numpie typo")]
    #[test_case("beautifulsoup4", "beutifulsoup", 3 ; "prefix typo")]
    fn distance_upper_bound(a: &str, b: &str, max_dist: usize) {
        assert!(damerau_levenshtein(a, b) <= max_dist);
    }

    #[test]
    fn normalized_identical() {
        assert_eq!(normalized_damerau_levenshtein("numpy", "numpy"), 1.0);
    }

    #[test]
    fn normalized_range() {
        let score = normalized_damerau_levenshtein("numpy", "numpie");
        assert!(score > 0.0 && score < 1.0);
    }

    #[test_case("numpy", "numpie", true ; "numpie above threshold")]
    #[test_case("numpy", "nupmy", true ; "transposition above threshold")]
    #[test_case("numpy", "zzzzz", false ; "unrelated below threshold")]
    fn normalized_threshold(a: &str, b: &str, above_06: bool) {
        let score = normalized_damerau_levenshtein(a, b);
        if above_06 {
            assert!(score > 0.6);
        } else {
            assert!(score < 0.6);
        }
    }
}
