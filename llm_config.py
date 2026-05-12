# # llm_config.py
# # ─────────────────────────────────────────────────────────────────────────────
# # Configure your LLM here.  The rest of the project imports `llm` from here.
# # Supports any OpenAI-compatible endpoint (OpenAI, Together.ai, Ollama, etc.)
# # ─────────────────────────────────────────────────────────────────────────────

# import os
# from openai import OpenAI

# # ── Configure these three values ──────────────────────────────────────────────
# API_KEY   = os.getenv("OPENAI_API_KEY", "your-api-key-here")   # set via env var
# BASE_URL  = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")  # or any compatible endpoint
# LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")             # model name
# # ─────────────────────────────────────────────────────────────────────────────

# # Build the shared client — imported as `llm` everywhere in the project
# llm = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# # Quick sanity-check helper (not called automatically)
# def test_connection() -> bool:
#     try:
#         resp = llm.chat.completions.create(
#             model=LLM_MODEL,
#             messages=[{"role": "user", "content": "Reply with OK"}],
#             max_tokens=5,
#         )
#         return resp.choices[0].message.content.strip() != ""
#     except Exception as e:
#         print(f"[llm_config] Connection test failed: {e}")
#         return False
import os
from langchain_openai import ChatOpenAI
# from langchain_huggingface import HuggingFaceEmbeddings


def _load_local_env(path: str = ".env") -> None:
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env()

# ==========================================================
# 🔐 1. Set up Hugging Face API key
# ==========================================================
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
HF_API_KEY = os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN")

if not HF_API_KEY:
    raise RuntimeError("Set HF_API_KEY in your environment or local .env file.")

# You can also load from environment (optional)
os.environ["HF_TOKEN"] = HF_API_KEY


# ==========================================================
# 🧠 2. Configure the LLM (Chat model)
# ==========================================================

llm1 = ChatOpenAI(
    base_url="https://router.huggingface.co/v1",  # Hugging Face OpenAI-compatible endpoint
    api_key=HF_API_KEY,                           # Your HF token
    model_name="openai/gpt-oss-120b",             # Chosen Hugging Face model
    temperature=0.7,                              # Balance creativity and determinism
    max_tokens=1024,                              # Adjust based on your output length needs
    request_timeout=120,                          # Prevent premature timeout on long responses
)

llm = ChatOpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_API_KEY,
    model_name="meta-llama/Llama-3.1-8B-Instruct",
    temperature=0.5,
    max_tokens=2048,   # Allow bigger JSON output
    request_timeout=150,
)

# ==========================================================
# 🔎 3. Configure the Embeddings model (for vector stores, retrieval, etc.)
# ==========================================================

# You can use a high-quality sentence embedding model from Hugging Face
# embeddings = HuggingFaceEmbeddings(
#     model_name="sentence-transformers/all-MiniLM-L6-v2"
# )


# ==========================================================
# ✅ 4. Quick Test (optional)
# ==========================================================

if __name__ == "__main__":
    print("✅ Hugging Face LLM and Embeddings configured successfully!")

    # Simple test prompt
    #response = llm.invoke("Give a short summary of how insurance fraud detection works.")
    #print("\n🧠 Model Response:\n", response)
