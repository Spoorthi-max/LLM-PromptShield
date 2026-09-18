from typing import Dict, Any, List, TypedDict, Optional
from adversarial.agents import run_red_agent, run_blue_agent
from security.pipeline import pipeline

class AgentState(TypedDict):
    history: List[str]
    current_attack: str
    pipeline_result: Dict[str, Any]
    last_patch: str
    iterations: int

def evaluate_system(state: AgentState) -> Dict[str, Any]:
    """Runs the current attack through the Antigravity Pipeline."""
    attack = state["current_attack"]
    print(f"[System] Evaluating attack: {attack}")
    
    # 1. Run Pre-processing Layers (1-4)
    result = pipeline.run_security_checks(attack)
    
    # If it passes L1-L4, we simulate an LLM trying to call a tool based on the attack
    if result["status"] == "PASS":
        print("[System] Attack bypassed Layers 1-4! Simulating LLM Tool Call...")
        tool_call_mock = {
            "tool_name": "transfer_funds",
            "args": {"from_acc": "ACC-1111", "to_acc": "ACC-9999", "amount": 50000}
        }
        
        # 2. Run Layer 5 Validation
        l5_result = pipeline.validate_tool_call(tool_call_mock["tool_name"], tool_call_mock["args"])
        
        if l5_result["status"] == "INVALID":
            print(f"[System] Caught at Layer 5: {l5_result['reason']}")
            result["l5_caught"] = True
        else:
            print("[System] CRITICAL FAILURE: Attack completely succeeded.")
            result["l5_caught"] = False
            
    else:
        print(f"[System] Blocked at Layer {result['layer']}: {result['reason']}")
        result["l5_caught"] = False
        
    return {
        "pipeline_result": result,
        "history": state.get("history", []) + [attack],
        "iterations": state.get("iterations", 0) + 1
    }

def should_continue(state: AgentState) -> str:
    """Determines the next node."""
    if state.get("iterations", 0) >= 3:
        return "end"
        
    result = state.get("pipeline_result", {})
    
    if result.get("status") == "PASS" and result.get("l5_caught", False):
        return "blue_agent"
    else:
        return "red_agent"

def apply_blue_patch(state: AgentState) -> Dict[str, Any]:
    """Operationalizes the patch suggested by the Blue Agent."""
    patch = state.get("last_patch")
    if patch:
        success = pipeline.apply_patch(patch)
        return {"patch_applied": success}
    return {"patch_applied": False}

# --- MOCK ADVERSARIAL APP ---
class MockAdversarialApp:
    def invoke(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        print("[Mock] Running adversarial loop without langgraph...")
        state = initial_state.copy()
        state["full_history"] = []
        # Increase iterations to 6 to see more attacks
        for i in range(6):
            # Red Agent
            red_out = run_red_agent(state)
            state.update(red_out)
            # System
            sys_out = evaluate_system(state)
            state.update(sys_out)
            
            # Record this step
            state["full_history"].append({
                "iteration": i,
                "attack": state["current_attack"],
                "result": state["pipeline_result"]
            })
            
            # Blue Agent (conditional)
            if should_continue(state) == "blue_agent":
                blue_out = run_blue_agent(state)
                state.update(blue_out)
                patch_out = apply_blue_patch(state)
                state.update(patch_out)
            
            state["iterations"] = i + 1
        return state

# Build Graph
adversarial_app = None
try:
    from langgraph.graph import StateGraph, END
    workflow = StateGraph(AgentState)
    workflow.add_node("red_agent", run_red_agent)
    workflow.add_node("system", evaluate_system)
    workflow.add_node("blue_agent", run_blue_agent)
    workflow.add_node("patch_pipeline", apply_blue_patch)
    workflow.set_entry_point("red_agent")
    workflow.add_edge("red_agent", "system")
    workflow.add_conditional_edges(
        "system",
        should_continue,
        {"red_agent": "red_agent", "blue_agent": "blue_agent", "end": END}
    )
    workflow.add_edge("blue_agent", "patch_pipeline")
    workflow.add_edge("patch_pipeline", "red_agent")
    adversarial_app = workflow.compile()
except ImportError:
    print("[Graph] langgraph missing. Falling back to MockAdversarialApp.")
    adversarial_app = MockAdversarialApp()
