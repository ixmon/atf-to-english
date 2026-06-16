# v12 Models vs CuneiformTranslators Comparison

## Overall Quality Scores

| Model | Standard Test Suite | P467316 Royal Test | Notes |
|-------|-------------------|-------------------|-------|
| **v12a (tag-free)** | **49.4/100** | ~50-60/100* | Best overall balance |
| **v12b (tagged)** | **45.1/100** | ~50-60/100* | Good with metadata |
| **CuneiformTranslators** | **20.0/100** | **84.5/100** | Excellent on royal inscriptions |
| v11 (previous) | 39.1/100 | - | Baseline |

*P467316 scores estimated from comparison test

## Key Findings

### Standard Test Suite (24 diverse test cases)
- **v12a wins**: 49.4 vs 20.0 (2.5x better)
- v12a handles diverse genres well (Astronomy, Archival, Medicine, etc.)
- CuneiformTranslators struggles with non-royal texts

### P467316 Royal Inscription Test (4 royal epithet cases)
- **CuneiformTranslators wins**: 84.5 vs ~50-60 (much better on royal texts)
- CuneiformTranslators excels at:
  - Royal epithets ("Ashur, great lord...")
  - Complex royal formulas
  - Period-specific royal language
- Our models are improving but still learning royal patterns

## Detailed Breakdown

### CuneiformTranslators - Standard Test Suite
- **Exact matches**: 0/24 (0%)
- **Keyword accuracy**: 8/43 (18.6%)
- **Average overlap**: 22.2%
- **Best genres**: Archival (66.7%), Astronomy (60.0%)
- **Weak genres**: Literature (0%), Lexicography (0%), Ritual (0%)

### CuneiformTranslators - P467316 Royal Test
- **Exact matches**: 1/4 (25%)
- **Keyword accuracy**: 13/15 (86.7%)
- **Average overlap**: 83.1%
- **Excellent performance** on royal inscriptions

### v12a - Standard Test Suite
- **Exact matches**: 5/24 (20.8%)
- **Keyword accuracy**: 25/43 (58.1%)
- **Average overlap**: ~50%
- **Balanced** across all genres

## Recommendations

1. **For general use**: Use **v12a** (best overall performance)
2. **For royal inscriptions**: Consider **CuneiformTranslators** or hybrid approach
3. **For tagged context**: Use **v12b** when period/genre metadata is available
4. **Future improvement**: Add more royal inscription training data to match CT's performance

## Next Steps

- [ ] Test on full P467316 tablet (all columns)
- [ ] Create hybrid model (ensemble v12a + CT for royal texts)
- [ ] Extract more royal epithets from large inscriptions
- [ ] Fine-tune v12a specifically on royal texts



