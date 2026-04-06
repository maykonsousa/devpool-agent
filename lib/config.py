import os
import hashlib

# --- API Keys ---
GEMINI_API_KEY = os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY", "")
DEVPOOL_API_URL = os.environ.get("DEVPOOL_API_URL", "")
DEVPOOL_API_KEY = os.environ.get("DEVPOOL_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# --- Fontes RSS ---
RSS_FEEDS = []

# --- Repos GitHub (issues como vagas) ---
GITHUB_REPOS = [
    "frontendbr/vagas",
    "backend-br/vagas",
    "react-brasil/vagas",
    "vuejs-br/vagas",
    "phpdevbr/vagas",
    "Gommunity/vagas",
    "androiddevbr/vagas",
    "CocoaHeadsBrasil/vagas",
]

# --- Sites para scraping ---
SCRAPER_SOURCES = []

# --- Mapeamento de enums para normalização ---
SENIORITY_MAP = {
    "junior": "junior",
    "júnior": "junior",
    "jr": "junior",
    "pleno": "pleno",
    "mid": "pleno",
    "middle": "pleno",
    "senior": "senior",
    "sênior": "senior",
    "sr": "senior",
    "especialista": "especialista",
    "specialist": "especialista",
    "lead": "especialista",
    "principal": "especialista",
    "estagio": "estagio",
    "estágio": "estagio",
    "intern": "estagio",
    "internship": "estagio",
    "trainee": "estagio",
}

MODEL_MAP = {
    "remoto": "remoto",
    "remote": "remoto",
    "home office": "remoto",
    "hibrido": "hibrido",
    "híbrido": "hibrido",
    "hybrid": "hibrido",
    "presencial": "presencial",
    "onsite": "presencial",
    "on-site": "presencial",
    "in-office": "presencial",
}

TYPE_MAP = {
    "clt": "clt",
    "pj": "pj",
    "pessoa jurídica": "pj",
    "freelancer": "freelancer",
    "freelance": "freelancer",
    "contractor": "pj",
    "estagio": "estagio",
    "estágio": "estagio",
    "internship": "estagio",
}

# --- LinkedIn/Google Search ---
LINKEDIN_QUERIES_PER_RUN = 3
LINKEDIN_RESULTS_PER_QUERY = 5

# --- Constantes ---
BATCH_SIZE = 20
MAX_ITEMS_PER_SOURCE = 10
REQUEST_TIMEOUT = 30


def generate_external_id(source: str, identifier: str) -> str:
    """Gera um externalId determinístico a partir da fonte e identificador."""
    raw = f"{source}:{identifier}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]
