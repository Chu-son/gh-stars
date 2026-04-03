import sys
import asyncio
import httpx
from typing import Any

async def check_ollama_ready(endpoint: str) -> bool:
    """Ollama API が疎通可能か確認します。"""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{endpoint}/api/version")
            return response.status_code == 200
    except Exception:
        return False

async def get_local_models(endpoint: str) -> list[str]:
    """ローカルに存在するモデル一覧を取得します。"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{endpoint}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m["name"] for m in models]
    except Exception:
        pass
    return []

async def pull_model(endpoint: str, model_name: str):
    """指定されたモデルをプルします。"""
    print(f"Pulling model '{model_name}'... This may take a while.")
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{endpoint}/api/pull", json={"name": model_name}) as response:
                if response.status_code != 200:
                    print(f"Error: Failed to pull model. Status: {response.status_code}")
                    return False
                
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        status = data.get("status", "")
                        completed = data.get("completed")
                        total = data.get("total")
                        if total is not None and completed is not None and total > 0:
                            percent = (completed / total) * 100
                            print(f"\rStatus: {status} ({percent:.1f}%)", end="", flush=True)
                        else:
                            print(f"\rStatus: {status}", end="", flush=True)
                print("\nPull completed successfully.")
                return True
    except Exception as e:
        print(f"\nError during model pull: {e}")
        return False

async def run_setup(config: Any):
    """LLM 環境のセットアップメインロジック。"""
    print(f"--- LLM Setup: {config.llm_endpoint} ---")
    
    ready = await check_ollama_ready(config.llm_endpoint)
    if not ready:
        print("Error: Ollama is not running or endpoint is incorrect.")
        print(f"Endpoint: {config.llm_endpoint}")
        print("\nOllama をインストールまたは起動してください:")
        print(" - Mac/Windows: https://ollama.com")
        print(" - Linux: curl -fsSL https://ollama.com/install.sh | sh")
        print(" - Docker: docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama")
        sys.exit(1)
        
    print("Ollama connection: OK")
    
    models = await get_local_models(config.llm_endpoint)
    # Ollama はタグが省略された場合 ':latest' とみなす場合があるため柔軟にチェック
    target = config.llm_model
    if target not in models and f"{target}:latest" not in models:
        print(f"Model '{target}' not found locally.")
        success = await pull_model(config.llm_endpoint, target)
        if not success:
            print("Failed to setup model.")
            sys.exit(1)
    else:
        print(f"Model '{target}': OK")
    
    print("\nLLM Setup finished successfully.")
