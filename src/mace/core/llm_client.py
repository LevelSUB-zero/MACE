"""
MACE Core: LLM Client (The Worker)

This module provides a unified interface to LLM providers.
The LLM is a "Worker" - it generates text/code on command from the symbolic Manager.

Scientific Basis: Broca's area uses language models for articulation, not reasoning.
ZDP Compliance: LLM is for RENDERING only. All decisions are made by Reptile Brain.
"""

import os
from typing import Optional, Dict, Any, List
from enum import Enum


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    GEMINI = "gemini"
    OPENAI = "openai"
    MOCK = "mock"


class LLMClient:
    """
    Unified LLM interface for MACE.
    Supports Ollama (local), Gemini, and OpenAI with automatic fallback.
    """
    
    def __init__(self, preferred_provider: Optional[str] = None):
        self.provider: Optional[LLMProvider] = None
        self.client = None
        self.model_name: str = ""
        self.ollama_base_url: str = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        
        # Try to initialize in order of preference (Ollama first for local)
        providers = [LLMProvider.OLLAMA, LLMProvider.GEMINI, LLMProvider.OPENAI]
        if preferred_provider:
            pref = preferred_provider.lower()
            if pref == "ollama":
                providers = [LLMProvider.OLLAMA, LLMProvider.GEMINI, LLMProvider.OPENAI]
            elif pref == "gemini":
                providers = [LLMProvider.GEMINI, LLMProvider.OLLAMA, LLMProvider.OPENAI]
            elif pref == "openai":
                providers = [LLMProvider.OPENAI, LLMProvider.OLLAMA, LLMProvider.GEMINI]
                
        for provider in providers:
            if self._try_init_provider(provider):
                break
                
        if self.provider is None:
            print("[LLM CLIENT] No LLM provider available. Using MOCK mode.")
            self.provider = LLMProvider.MOCK
            
    def _try_init_provider(self, provider: LLMProvider) -> bool:
        """Attempt to initialize a specific provider."""
        try:
            if provider == LLMProvider.OLLAMA:
                # Check if Ollama is running
                import requests
                try:
                    response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=2)
                    if response.status_code == 200:
                        models = response.json().get("models", [])
                        if models:
                            # Prefer coding models, fallback to any available
                            model_names = [m.get("name", "") for m in models]
                            preferred = ["qwen2.5-coder", "codellama", "deepseek-coder", "llama3", "mistral", "phi3"]
                            selected = None
                            for pref in preferred:
                                for name in model_names:
                                    if pref in name.lower():
                                        selected = name
                                        break
                                if selected:
                                    break
                            if not selected:
                                selected = model_names[0]
                            
                            self.model_name = selected
                            self.provider = LLMProvider.OLLAMA
                            print(f"[LLM CLIENT] Initialized with Ollama ({self.model_name})")
                            return True
                except requests.exceptions.ConnectionError:
                    pass  # Ollama not running
                except Exception as e:
                    print(f"[LLM CLIENT] Ollama check failed: {e}")
                    
            elif provider == LLMProvider.GEMINI:
                api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
                if api_key:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    self.client = genai.GenerativeModel("gemini-2.0-flash")
                    self.provider = LLMProvider.GEMINI
                    self.model_name = "gemini-2.0-flash"
                    print(f"[LLM CLIENT] Initialized with Gemini ({self.model_name})")
                    return True
                    
            elif provider == LLMProvider.OPENAI:
                api_key = os.environ.get("OPENAI_API_KEY")
                if api_key:
                    import openai
                    self.client = openai.OpenAI(api_key=api_key)
                    self.provider = LLMProvider.OPENAI
                    self.model_name = "gpt-4o-mini"
                    print(f"[LLM CLIENT] Initialized with OpenAI ({self.model_name})")
                    return True
                    
        except ImportError as e:
            print(f"[LLM CLIENT] Provider {provider} not available: {e}")
        except Exception as e:
            print(f"[LLM CLIENT] Failed to init {provider}: {e}")
            
        return False
        
    def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> str:
        """
        Generate text from the LLM.
        
        Args:
            prompt: The user/task prompt
            system_prompt: Optional system instructions
            max_tokens: Maximum response length
            temperature: Creativity (0.0 = deterministic, 1.0 = creative)
            
        Returns:
            Generated text
        """
        if self.provider == LLMProvider.MOCK:
            return self._generate_mock(prompt)
            
        elif self.provider == LLMProvider.OLLAMA:
            return self._generate_ollama(prompt, system_prompt, max_tokens, temperature)
            
        elif self.provider == LLMProvider.GEMINI:
            return self._generate_gemini(prompt, system_prompt, max_tokens, temperature)
            
        elif self.provider == LLMProvider.OPENAI:
            return self._generate_openai(prompt, system_prompt, max_tokens, temperature)
            
        return "[ERROR] No LLM provider configured"
        
    def _generate_ollama(
        self, 
        prompt: str, 
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Generate using Ollama (local)."""
        import requests
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = requests.post(
                f"{self.ollama_base_url}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature
                    }
                },
                timeout=120  # Longer timeout for local inference
            )
            
            if response.status_code == 200:
                return response.json().get("message", {}).get("content", "")
            else:
                return f"[ERROR] Ollama returned {response.status_code}"
                
        except Exception as e:
            print(f"[LLM CLIENT] Ollama error: {e}")
            return f"[ERROR] Ollama generation failed: {e}"
        
    def _generate_mock(self, prompt: str) -> str:
        """Mock generation for testing."""
        # Return structured mock based on prompt type
        if "code" in prompt.lower() or "python" in prompt.lower():
            return '''def main(**kwargs):
    """Generated tool function."""
    return {"status": "success", "result": "mock_output"}
'''
        elif "summarize" in prompt.lower():
            return "This is a mock summary of the provided content."
        else:
            return f"[MOCK RESPONSE] Acknowledged: {prompt[:50]}..."
            
    def _generate_gemini(
        self, 
        prompt: str, 
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Generate using Gemini."""
        try:
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
                
            response = self.client.generate_content(
                full_prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": temperature
                }
            )
            return response.text
            
        except Exception as e:
            print(f"[LLM CLIENT] Gemini error: {e}")
            return f"[ERROR] Gemini generation failed: {e}"
            
    def _generate_openai(
        self, 
        prompt: str, 
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Generate using OpenAI."""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"[LLM CLIENT] OpenAI error: {e}")
            return f"[ERROR] OpenAI generation failed: {e}"
            
    def generate_code(
        self, 
        description: str, 
        language: str = "python"
    ) -> str:
        """
        Generate code for a specific task.
        Wrapper with code-specific prompting.
        """
        system_prompt = f"""You are a code generator. Generate clean, working {language} code.
Rules:
- Output ONLY code, no explanations
- Include docstrings
- Handle errors gracefully
- Use type hints
- Do NOT use dangerous imports (subprocess, socket, requests, etc.)
"""
        
        prompt = f"""Generate {language} code for the following task:

{description}

Requirements:
- Create a main() function that accepts **kwargs and returns a dict
- The return dict must have a "status" key ("success" or "error")
- Include proper error handling
"""
        
        return self.generate(prompt, system_prompt, max_tokens=2048, temperature=0.3)
        
    def articulate(
        self, 
        intent: Dict[str, Any]
    ) -> str:
        """
        Convert a symbolic intent into natural language.
        Used by BrocaBridge for human-readable output.
        """
        system_prompt = """You are a communication assistant. Convert structured intents into natural, helpful responses.
Keep responses concise and professional."""
        
        prompt = f"""Convert this intent into a natural language response:

Action: {intent.get('action', 'unknown')}
Target: {intent.get('target', 'unknown')}
Content: {intent.get('content_payload', '')}
Constraints: {intent.get('constraints', {})}

Generate a helpful, natural response:"""
        
        return self.generate(prompt, system_prompt, max_tokens=512, temperature=0.7)


# Global singleton
_LLM_CLIENT: Optional[LLMClient] = None


def get_llm_client(preferred_provider: Optional[str] = None) -> LLMClient:
    """Get or create the global LLM client."""
    global _LLM_CLIENT
    if _LLM_CLIENT is None:
        _LLM_CLIENT = LLMClient(preferred_provider)
    return _LLM_CLIENT
