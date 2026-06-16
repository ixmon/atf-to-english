#!/usr/bin/env python3
"""
Compare v12a (tag-free) and v12b (tagged) models, plus CuneiformTranslators.
Tests on P467316 (Tiglath-Pileser inscription) and the standard test suite.
"""

import json
import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tests.test_translation_quality import TranslationTester, TEST_CASES
from lib.idiom_resolver import IdiomResolver

# P467316 test cases (first few lines from the royal inscription)
P467316_TEST_CASES = [
    ("{d}a-szur _en gal_ mus-te-szir3 kisz-szat _dingir-mesz_", 
     "Ashur, great lord, who makes the totality of the gods submit",
     "Middle-Assyrian", "Literature", ["ashur", "great", "lord", "gods"]),
    
    ("na-din {gesz}gidri u3 a-ge-e mu-kin2 _man_-ti",
     "who gives scepter and crown, who establishes kingship",
     "Middle-Assyrian", "Literature", ["scepter", "crown", "kingship"]),
    
    ("{d}en-lil2 be-lu _man_ gi-mir {d}a-nun-na-ki",
     "Enlil, lord, king of all the Anunnaku gods",
     "Middle-Assyrian", "Literature", ["enlil", "lord", "king", "anunnaku"]),
    
    ("a-bu _dingir-mesz en kur-kur_",
     "father of the gods, lord of the lands",
     "Middle-Assyrian", "Literature", ["father", "gods", "lord", "lands"]),
]

class TagFreeTester(TranslationTester):
    """Tester for tag-free models (like CuneiformTranslators)."""
    
    def translate(self, atf: str, period: str = "Generic", genre: str = "Generic") -> str:
        """Translate ATF to English using tag-free prompt."""
        import torch
        
        # Simple prompt like CuneiformTranslators
        input_text = f"translate Akkadian to English: {atf}"
        inputs = self.tokenizer(
            input_text, 
            return_tensors="pt", 
            max_length=256, 
            truncation=True
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=128,
                num_beams=4,
                early_stopping=True,
                no_repeat_ngram_size=2,
            )
        
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

def test_cuneiform_translators(atf_text: str) -> str:
    """Test using CuneiformTranslators model (via their example.py)."""
    try:
        # Run their example.py with the ATF text
        script_dir = "data/CuneiformTranslators"
        if not os.path.exists(script_dir):
            return "ERROR: CuneiformTranslators not found"
        
        # Create a temporary test script
        test_script = f"""
import sys
sys.path.insert(0, '{script_dir}')
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, TranslationPipeline

tokenizer = AutoTokenizer.from_pretrained("praeclarum/cuneiform")
model = AutoModelForSeq2SeqLM.from_pretrained("praeclarum/cuneiform", max_length=tokenizer.model_max_length)
pipeline = TranslationPipeline(model=model, tokenizer=tokenizer)

def translate(akkadian):
    return pipeline(f"translate Akkadian to English: {{akkadian}}")[0]["translation_text"]

result = translate("{atf_text}")
print(result)
"""
        
        # Run in their venv if it exists
        venv_python = os.path.join(script_dir, "venv", "bin", "python")
        if os.path.exists(venv_python):
            result = subprocess.run(
                [venv_python, "-c", test_script],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=script_dir
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"ERROR: {result.stderr[:100]}"
        else:
            return "ERROR: venv not found"
    except Exception as e:
        return f"ERROR: {str(e)[:100]}"

def main():
    print("=" * 70)
    print("v12 Model Comparison Test")
    print("=" * 70)
    
    results = {}
    
    # Test v12a (tag-free)
    print("\n" + "=" * 70)
    print("Testing v12a (tag-free, like CuneiformTranslators)")
    print("=" * 70)
    v12a_path = "models/atf-translator-v12a-tagfree-final"
    if os.path.exists(v12a_path):
        tester_v12a = TagFreeTester(v12a_path)
        tester_v12a.load_model()
        
        # Test on standard suite
        print("\n📊 Standard Test Suite:")
        main_results_v12a = tester_v12a.run_tests(TEST_CASES, "v12a")
        quality_v12a = tester_v12a.print_results(main_results_v12a)
        results["v12a"] = {
            "quality_score": quality_v12a,
            "main_results": main_results_v12a
        }
        
        # Test on P467316
        print("\n📊 P467316 Royal Inscription Test:")
        p467316_results_v12a = tester_v12a.run_tests(P467316_TEST_CASES, "v12a-P467316")
        tester_v12a.print_results(p467316_results_v12a)
        results["v12a"]["p467316_results"] = p467316_results_v12a
    else:
        print(f"⚠️  v12a model not found at {v12a_path}")
        results["v12a"] = None
    
    # Test v12b (tagged)
    print("\n" + "=" * 70)
    print("Testing v12b (tagged, with period/genre)")
    print("=" * 70)
    v12b_path = "models/atf-translator-v12b-tagged-final"
    if os.path.exists(v12b_path):
        tester_v12b = TranslationTester(v12b_path)
        tester_v12b.load_model()
        
        # Test on standard suite
        print("\n📊 Standard Test Suite:")
        main_results_v12b = tester_v12b.run_tests(TEST_CASES, "v12b")
        quality_v12b = tester_v12b.print_results(main_results_v12b)
        results["v12b"] = {
            "quality_score": quality_v12b,
            "main_results": main_results_v12b
        }
        
        # Test on P467316
        print("\n📊 P467316 Royal Inscription Test:")
        p467316_results_v12b = tester_v12b.run_tests(P467316_TEST_CASES, "v12b-P467316")
        tester_v12b.print_results(p467316_results_v12b)
        results["v12b"]["p467316_results"] = p467316_results_v12b
    else:
        print(f"⚠️  v12b model not found at {v12b_path}")
        results["v12b"] = None
    
    # Test CuneiformTranslators on P467316
    print("\n" + "=" * 70)
    print("Testing CuneiformTranslators (praeclarum/cuneiform)")
    print("=" * 70)
    print("\n📊 P467316 Royal Inscription Test:")
    
    ct_results = {
        "name": "CuneiformTranslators",
        "total": len(P467316_TEST_CASES),
        "keyword_hits": 0,
        "keyword_total": 0,
        "overlap_scores": [],
        "details": []
    }
    
    from tests.test_translation_quality import keyword_match, word_overlap_score
    
    for atf, expected, period, genre, keywords in P467316_TEST_CASES:
        predicted = test_cuneiform_translators(atf)
        
        kw_found, kw_total = keyword_match(predicted, keywords)
        overlap = word_overlap_score(predicted, expected)
        
        ct_results["keyword_hits"] += kw_found
        ct_results["keyword_total"] += kw_total
        ct_results["overlap_scores"].append(overlap)
        ct_results["details"].append({
            "atf": atf,
            "expected": expected,
            "predicted": predicted,
            "keyword_hits": kw_found,
            "keyword_total": kw_total,
            "overlap_score": overlap
        })
        
        print(f"\nATF: {atf}")
        print(f"Expected: {expected}")
        print(f"CT:       {predicted}")
        print(f"Keywords: {kw_found}/{kw_total}, Overlap: {overlap:.2f}")
    
    if ct_results["keyword_total"] > 0:
        keyword_acc = ct_results["keyword_hits"] / ct_results["keyword_total"]
    else:
        keyword_acc = 0.0
    avg_overlap = sum(ct_results["overlap_scores"]) / len(ct_results["overlap_scores"]) if ct_results["overlap_scores"] else 0.0
    quality_ct = (keyword_acc * 0.4 + avg_overlap * 0.6)
    
    print(f"\n📊 CuneiformTranslators Summary:")
    print(f"Keyword Accuracy: {100*keyword_acc:.1f}%")
    print(f"Average Overlap: {100*avg_overlap:.1f}%")
    print(f"Quality Score: {100*quality_ct:.1f}/100")
    
    results["cuneiform_translators"] = {
        "quality_score": quality_ct,
        "p467316_results": ct_results
    }
    
    # Save results
    output_file = "tests/v12_comparison_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Results saved to {output_file}")
    
    # Summary comparison
    print("\n" + "=" * 70)
    print("SUMMARY COMPARISON")
    print("=" * 70)
    if results.get("v12a"):
        print(f"v12a (tag-free):     {100*results['v12a']['quality_score']:.1f}/100")
    if results.get("v12b"):
        print(f"v12b (tagged):       {100*results['v12b']['quality_score']:.1f}/100")
    if results.get("cuneiform_translators"):
        print(f"CuneiformTranslators: {100*results['cuneiform_translators']['quality_score']:.1f}/100")
    print("=" * 70)

if __name__ == "__main__":
    main()



