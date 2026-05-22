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

    let mut d = vec![vec![0usize; len_b + 1]; len_a + 1];

    for (i, row) in d.iter_mut().enumerate().take(len_a + 1) {
        row[0] = i;
    }
    #[allow(clippy::needless_range_loop)]
    for j in 0..=len_b {
        d[0][j] = j;
    }

    for i in 1..=len_a {
        for j in 1..=len_b {
            let cost = if a[i - 1] == b[j - 1] { 0 } else { 1 };
            d[i][j] = min(min(d[i - 1][j] + 1, d[i][j - 1] + 1), d[i - 1][j - 1] + cost);

            if i > 1 && j > 1 && a[i - 1] == b[j - 2] && a[i - 2] == b[j - 1] {
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1);
            }
        }
    }

    d[len_a][len_b]
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

    #[test]
    fn identical_strings() {
        assert_eq!(damerau_levenshtein("numpy", "numpy"), 0);
        assert_eq!(normalized_damerau_levenshtein("numpy", "numpy"), 1.0);
    }

    #[test]
    fn empty_strings() {
        assert_eq!(damerau_levenshtein("", ""), 0);
        assert_eq!(damerau_levenshtein("abc", ""), 3);
        assert_eq!(damerau_levenshtein("", "abc"), 3);
    }

    #[test]
    fn single_substitution() {
        assert_eq!(damerau_levenshtein("numpy", "numpx"), 1);
    }

    #[test]
    fn transposition() {
        assert_eq!(damerau_levenshtein("numpy", "nupmy"), 1);
    }

    #[test]
    fn typo_numpie() {
        let dist = damerau_levenshtein("numpy", "numpie");
        assert!(dist <= 2);
    }

    #[test]
    fn missing_hyphen() {
        assert_eq!(damerau_levenshtein("scikit-learn", "scikitlearn"), 1);
    }

    #[test]
    fn prefix_typo() {
        let dist = damerau_levenshtein("beautifulsoup4", "beutifulsoup");
        assert!(dist <= 3);
    }

    #[test]
    fn normalized_range() {
        let score = normalized_damerau_levenshtein("numpy", "numpie");
        assert!(score > 0.0 && score < 1.0);
    }

    #[test]
    fn normalized_threshold_realistic() {
        assert!(normalized_damerau_levenshtein("numpy", "numpie") > 0.6);
        assert!(normalized_damerau_levenshtein("numpy", "nupmy") > 0.6);
        assert!(normalized_damerau_levenshtein("numpy", "zzzzz") < 0.6);
    }
}
