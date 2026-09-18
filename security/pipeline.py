import json
from typing import Dict, Any, Optional, List
from security.layers import (
    SyntacticScrubber,
    layer_2_normalize,
    SemanticShield,
    TransformerRiskJudge,
    TransferFundsSchema
)

class AntigravityPipeline:
    def __init__(self):
        # Initialize heavy models once
        print("Initializing Syntactic Scrubber (Layer 1)...")
        self.scrubber = SyntacticScrubber()
        print("Initializing Semantic Shield (Qdrant & Sentence-Transformers)...")
        self.shield = SemanticShield()
        print("Initializing Transformer Risk Judge (Deberta)...")
        self.judge = TransformerRiskJudge()
        print("Pipeline initialization complete.")

    def run_security_checks(self, raw_input: str, history: Optional[List[str]] = None) -> Dict[str, Any]:
        """Runs the 4 pre-processing layers standalone and statefully against conversation history."""
        
        # Step 1: Pre-process and Translate Non-English vectors
        processed_input = self._translate_if_needed(raw_input)
        
        # Step 2: Stateless evaluation of current turn input
        stateless_result = self._evaluate_text(processed_input)
        if stateless_result["status"] == "BLOCKED":
            return stateless_result
            
        # Step 3: Stateful evaluation of cumulative conversation history
        if history and len(history) > 0:
            print(f"[Pipeline] Stateful analysis: evaluating prompt against {len(history)} historical turns...")
            
            # Combine history inputs with the current processed input
            # Join with newline separators to form the continuous context
            combined_history = [self._translate_if_needed(h) for h in history]
            combined_context = "\n".join(combined_history + [processed_input])
            
            stateful_result = self._evaluate_text(combined_context)
            if stateful_result["status"] == "BLOCKED":
                # Mark as blocked due to multi-turn steering detection
                stateful_result["reason"] = f"STATEFUL_BLOCK: {stateful_result['reason']} (Detected via Cumulative Context)"
                stateful_result["is_multi_turn"] = True
                return stateful_result

        # Everything passed
        return stateless_result

    def _evaluate_text(self, text: str) -> Dict[str, Any]:
        """Core evaluation logic across security layers 1 to 4."""
        # Layer 1: Syntactic Scrubber
        success, l1_out = self.scrubber.check(text)
        if not success:
            return {"status": "BLOCKED", "layer": 1, "reason": l1_out}

        # Layer 2: Normalization & Obfuscation Deobfuscator
        normalized = layer_2_normalize(l1_out)

        # Layer 3: Semantic Similarity Vector Shield
        l3_score = self.shield.check(normalized)
        if l3_score > 0.85:
            return {"status": "BLOCKED", "layer": 3, "reason": f"L3_RISK_SCORE: {l3_score:.2f}"}

        # Layer 4: Transformer Risk Judge (Deberta Injection Classifier)
        l4_score = self.judge.get_risk(normalized)
        if l4_score > 0.70:
            return {"status": "BLOCKED", "layer": 4, "reason": f"L4_RISK_SCORE: {l4_score:.2f}"}

        return {
            "status": "PASS",
            "normalized_input": normalized,
            "metrics": {
                "l3_score": l3_score,
                "l4_score": l4_score
            }
        }

    def _translate_if_needed(self, text: str) -> str:
        """Language Pivot Shield: Detects non-English keywords/phrases and maps them to English."""
        # Pre-compiled mapping of common malicious pivot translation triggers
        translations = {
            # Spanish pivot triggers
            "ignorar las instrucciones anteriores": "ignore previous instructions",
            "ignora las instrucciones": "ignore instructions",
            "modo desarrollador": "developer mode",
            "anular sistema": "system override",
            
            # French pivot triggers
            "ignorez les instructions precedentes": "ignore previous instructions",
            "ignorer les instructions": "ignore instructions",
            "mode developpeur": "developer mode",
            "outrepasser le systeme": "system override",
            
            # German pivot triggers
            "ignoriere vorherige anweisungen": "ignore previous instructions",
            "entwicklermodus": "developer mode",
            "systemumgehung": "system override"
        }
        
        normalized_text = text.lower().strip()
        for foreign_phrase, english_translation in translations.items():
            if foreign_phrase in normalized_text:
                print(f"[Pivot Shield] Detected translation bypass: '{foreign_phrase}' -> '{english_translation}'")
                text = text.replace(foreign_phrase, english_translation)
                text = text.replace(foreign_phrase.title(), english_translation)
                
        return text

    def validate_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 5: Tool Validation."""
        try:
            if tool_name == "transfer_funds":
                valid_call = TransferFundsSchema(**tool_args)
                return {"status": "VALID", "validated_args": valid_call.model_dump()}
            else:
                return {"status": "INVALID", "reason": f"Unknown tool: {tool_name}"}
        except Exception as e:
            return {"status": "INVALID", "reason": str(e)}

    def apply_patch(self, patch_data: str) -> bool:
        """Parses a patch from the Blue Agent and updates Layer 1."""
        try:
            data = json.loads(patch_data)
            patch = data.get("suggested_patch")
            if patch:
                print(f"[Pipeline] Applying Patch: {patch}")
                self.scrubber.add_pattern(patch)
                return True
        except Exception as e:
            print(f"[Pipeline] Failed to apply patch: {e}")
        return False

# Singleton instance for the FastAPI app
pipeline = AntigravityPipeline()
