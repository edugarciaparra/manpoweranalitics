"""
Conexión con la API de IA, por HTTP directo (sin librerías del proveedor).

Se configura en el .env y sirve la API de cualquier empresa:

    IA_PROVEEDOR=anthropic   API de Claude (Anthropic)
    IA_PROVEEDOR=openai      OpenAI o cualquier API "compatible con OpenAI":
                             DeepSeek, Mistral, Groq, OpenRouter, Ollama, LM Studio...
                             (para esas, poner su dirección en IA_URL)
    IA_PROVEEDOR=azure       Azure OpenAI (IA_URL = https://<recurso>.openai.azure.com,
                             IA_MODELO = nombre del deployment)
    IA_PROVEEDOR=gemini      Google Gemini (por su API compatible con OpenAI)

    IA_API_KEY   clave de la API
    IA_MODELO    modelo (vacío = el de MODELOS_POR_DEFECTO)
    IA_URL       dirección de la API (vacío = la oficial del proveedor)

Todo el proyecto usa get_proveedor().completar(sistema, mensajes) o
get_proveedor().responder(sistema, pregunta). mensajes es una lista de
{"role": "user" | "assistant", "content": "..."}.
"""
import json
import urllib.error
import urllib.request

from django.conf import settings

SEGUNDOS_ESPERA = 120

URLS_POR_DEFECTO = {
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
}
MODELOS_POR_DEFECTO = {
    "anthropic": "claude-sonnet-5-5",
    "openai": "gpt-4.1",
    "gemini": "gemini-2.5-flash",
}
# Nombres alternativos que se aceptan en IA_PROVEEDOR
ALIAS = {"claude": "anthropic", "compatible": "openai", "deepseek": "openai", "mistral": "openai",
         "groq": "openai", "openrouter": "openai", "ollama": "openai", "google": "gemini"}


class ErrorIA(Exception):
    pass


def _post(url, cuerpo, encabezados):
    pedido = urllib.request.Request(
        url, data=json.dumps(cuerpo).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", **encabezados},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=SEGUNDOS_ESPERA) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "replace")[:400]
        try:
            j = json.loads(detalle)
            detalle = (j.get("error") or {}).get("message") or j.get("message") or detalle
        except (json.JSONDecodeError, AttributeError):
            pass
        raise ErrorIA(f"La API de IA respondió {e.code}: {detalle}") from e
    except urllib.error.URLError as e:
        raise ErrorIA(f"No se pudo conectar con la API de IA ({url}): {e.reason}") from e
    except TimeoutError as e:
        raise ErrorIA("La API de IA tardó demasiado en responder.") from e


class ProveedorIA:
    nombre = "base"

    @property
    def modelo(self):
        return settings.IA_MODELO or MODELOS_POR_DEFECTO.get(self.nombre, "")

    @property
    def url(self):
        return (settings.IA_URL or URLS_POR_DEFECTO.get(self.nombre, "")).rstrip("/")

    def completar(self, sistema: str, mensajes: list, max_tokens: int = 1500) -> str:
        raise NotImplementedError

    def responder(self, sistema: str, pregunta: str) -> str:
        return self.completar(sistema, [{"role": "user", "content": pregunta}])


class AnthropicProveedor(ProveedorIA):
    """API de mensajes de Anthropic (Claude)."""
    nombre = "anthropic"

    def completar(self, sistema, mensajes, max_tokens=1500):
        r = _post(f"{self.url}/v1/messages", {
            "model": self.modelo,
            "max_tokens": max_tokens,
            # El texto del sistema (esquema de la base) se repite en cada pregunta: se cachea
            "system": [{"type": "text", "text": sistema, "cache_control": {"type": "ephemeral"}}],
            "messages": mensajes,
        }, {"x-api-key": settings.IA_API_KEY, "anthropic-version": "2023-06-01"})
        return "".join(b.get("text", "") for b in r.get("content", []) if b.get("type") == "text").strip()


class OpenAIProveedor(ProveedorIA):
    """API de chat de OpenAI y de todas las compatibles (DeepSeek, Mistral, Groq, Ollama, ...)."""
    nombre = "openai"

    def _direccion(self):
        return f"{self.url}/chat/completions", {"Authorization": f"Bearer {settings.IA_API_KEY}"}

    def completar(self, sistema, mensajes, max_tokens=1500):
        url, encabezados = self._direccion()
        r = _post(url, {
            "model": self.modelo,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": sistema}] + mensajes,
        }, encabezados)
        try:
            return (r["choices"][0]["message"]["content"] or "").strip()
        except (KeyError, IndexError, TypeError) as e:
            raise ErrorIA(f"Respuesta inesperada de la API de IA: {str(r)[:300]}") from e


class GeminiProveedor(OpenAIProveedor):
    nombre = "gemini"


class AzureProveedor(OpenAIProveedor):
    """Azure OpenAI: la dirección lleva el deployment (IA_MODELO) y la versión de la API."""
    nombre = "azure"

    def _direccion(self):
        base = (settings.IA_URL or settings.IA_AZURE_ENDPOINT).rstrip("/")
        url = (f"{base}/openai/deployments/{self.modelo}/chat/completions"
               f"?api-version={settings.IA_AZURE_VERSION}")
        return url, {"api-key": settings.IA_API_KEY}


PROVEEDORES = {p.nombre: p for p in
               [AnthropicProveedor, OpenAIProveedor, AzureProveedor, GeminiProveedor]}


def get_proveedor() -> ProveedorIA:
    nombre = (settings.IA_PROVEEDOR or "").strip().lower()
    if not nombre:
        raise ErrorIA("Rafa no está configurado: completá IA_PROVEEDOR e IA_API_KEY en el archivo .env "
                      "y reiniciá el servidor.")
    clase = PROVEEDORES.get(ALIAS.get(nombre, nombre))
    if clase is None:
        raise ValueError(
            f"IA_PROVEEDOR='{settings.IA_PROVEEDOR}' no existe. Opciones: {', '.join(PROVEEDORES)}"
        )
    return clase()
