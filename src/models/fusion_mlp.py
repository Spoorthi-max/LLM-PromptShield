import torch
import torch.nn as nn
import torch.nn.functional as F
import os
from openai import AsyncOpenAI

class FusionMLP(nn.Module):
    def __init__(self):
        super(FusionMLP, self).__init__()
        self.fc1 = nn.Linear(4, 16)
        self.fc2 = nn.Linear(16, 8)
        self.fc3 = nn.Linear(8, 1)
        self.client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = torch.sigmoid(self.fc3(x))
        return x

    def predict(self, features_tensor):
        device_type = 'cuda' if features_tensor.is_cuda else 'cpu'
        with torch.no_grad():
            with torch.autocast(device_type=device_type):
                return self.forward(features_tensor)

    async def get_explainability(self, url: str, features: list, probability: float) -> str:
        if probability <= 0.7 or not self.client.api_key:
            return ""
            
        prompt = f"""
        A phishing detection system has flagged the URL {url} with a probability of {probability:.2f}.
        The detection features were:
        - Multimodal consistency (CLIP similarity): {features[0]:.2f} (lower is more anomalous)
        - Brand mismatch score (VLM): {features[1]:.2f} (1.0 = mismatch)
        - Counterfactual deviation (Distance from Golden AI Reference): {features[2]:.2f} (higher is more anomalous)
        - Temporal mutation score: {features[3]:.2f}
        
        Write a concise, 2-sentence human-readable explanation of the specific anomalies found to explain why this is likely phishing.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Explainability Error: {e}")
            return "High probability of phishing detected based on visual and textual inconsistencies."
