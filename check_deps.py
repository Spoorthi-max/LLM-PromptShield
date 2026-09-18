import sys
import os

try:
    import fastapi
    import uvicorn
    import pydantic
    import sentence_transformers
    import transformers
    import torch
    import qdrant_client
    import langgraph
    import langchain
    import outlines
    print("All dependencies are present.")
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

from security.pipeline import pipeline
print("Security pipeline initialized.")

from adversarial.graph import adversarial_app
print("Adversarial graph initialized.")
