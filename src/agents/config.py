import os
import requests
import logging
from typing import Optional, Dict, Any

logger=logging.getLogger("OllamaConfig")

class OllamaConfig:

    def __init__(self,base_url:str="http://localhost:11434",model:str="qwen2.5-coder:3b"):
        self.base_url=base_url.rstrip("/")
        self.model=model
        self._verify_connection()
        logger.info(f"Ollama configuration initialized with model: {model}")

    def _verify_connection(self):
        try:
            response=requests.get(f"{self.base_url}/api/tags",timeout=5)
            response.raise_for_status()

            models=response.json().get("models",[])
            model_names=[m.get("name") for m in models]

            if self.model not in model_names:
                logger.warning(f"Model {self.model} not found. Available models: {model_names}")
                raise ValueError(
                    f"Model {self.model} not available. "
                )
            logger.info("Ollama server connected")
        
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                "Can't connect to Ollama server. "
                "Make sure Ollama is running:\n"
            )
        
        except requests.exceptions.Timeout:
            raise TimeoutError("Ollama server is not responding")
    
    def generate(self,prompt:str,**kwargs)->str:
        payload={
            "model":self.model,
            "prompt":prompt,
            "stream":False,
            "options":{
                "temperature":kwargs.get("temperature",0.0),
                "nun_predict":kwargs.get("max_tokens",4096),
            }
        }
        try:
            response=requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120
            )
            response.raise_for_status()

            result=response.json()
            return result.get("response","")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    def chat(self,messages:list,**kwargs)->str:
        payload={
            "model":self.model,
            "messages":messages,
            "stream":False,
            "options":{
                "temperature":kwargs.get("temperature",0.0),
                "num_perdict":kwargs.get("max_tokens",4096),
            }
        }
        try:
            response=requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120
            )
            response.raise_for_status()

            result=response.json()
            return result.get("messages",{}).get("content","")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama chat failed: {e}")
            raise

_config: Optional[OllamaConfig]=None

def get_ollama_client()->OllamaConfig:
    global _config

    if _config is None:
        _config=OllamaConfig()

    return _config

def reset_ollama_client():
    global _config
    _confi=None

OLLAMA_MODEL="qwen2.5-coder:3b"
OLLAMA_MAX_TOKENS=4096
OLLAMA_TEMPERATURE=0.0

if __name__=="__main__":
    print("\n"+"="*70)
    print("OLLAMA CONFIGURATION TEST")
    print("="*70+"\n")

    try:
        client=get_ollama_client()
        print(" Ollama client initialized successfully")
        print(f"Model: {OLLAMA_MODEL}")
        print(f"Sever: http://localhost:11434")
        print(f"Max tokens: {OLLAMA_MAX_TOKENS}")
        print(f"Temperature: {OLLAMA_TEMPERATURE}")

        print("\nTesting gen")
        response=client.generate("What are you?")
        print(f"Response: {response[:100]}")

        print("\n"+"="*70)
        print("ALL TESTS PASSED!")
        print("="*70+"\n")

    except ConnectionError as e:
        print(f"Connection Error: {e}")
    
    except ValueError as e:
        print(f"Configuration error: {e}")

    except Exception as e:
        print(f"Unexpected Error: {e}")

    