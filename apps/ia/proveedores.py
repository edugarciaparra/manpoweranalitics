"""
Capa de proveedores de IA.

Todo el proyecto usa get_proveedor().responder(...). Cuál proveedor se usa se
decide en .env con IA_PROVEEDOR, así cambiar de Claude a OpenAI/Azure/Gemini
en otra empresa no requiere tocar código.

Por ahora solo está implementado "mock" (respuestas de ejemplo, sin clave).
Los demás están armados como esqueleto: hay que instalar su SDK y descomentar.
"""
from django.conf import settings


class ProveedorIA:
    nombre = "base"

    def responder(self, sistema: str, pregunta: str) -> str:
        raise NotImplementedError


class MockProveedor(ProveedorIA):
    """Respuestas fijas para desarrollar la interfaz sin gastar tokens."""
    nombre = "mock"

    def responder(self, sistema, pregunta):
        return (
            f"Respuesta de ejemplo a: «{pregunta}».\n\n"
            "El asistente todavía no está conectado a un modelo real. "
            "Cuando configures IA_PROVEEDOR e IA_API_KEY en el archivo .env, "
            "esta respuesta la va a generar el modelo usando los datos del módulo."
        )


class ClaudeProveedor(ProveedorIA):
    nombre = "claude"

    def responder(self, sistema, pregunta):
        import anthropic  # pip install anthropic
        cliente = anthropic.Anthropic(api_key=settings.IA_API_KEY)
        r = cliente.messages.create(
            model=settings.IA_MODELO,
            max_tokens=1024,
            system=sistema,
            messages=[{"role": "user", "content": pregunta}],
        )
        return r.content[0].text.strip()


class OpenAIProveedor(ProveedorIA):
    nombre = "openai"

    def _cliente(self):
        from openai import OpenAI  # pip install openai
        return OpenAI(api_key=settings.IA_API_KEY)

    def responder(self, sistema, pregunta):
        r = self._cliente().chat.completions.create(
            model=settings.IA_MODELO,
            messages=[{"role": "system", "content": sistema},
                      {"role": "user", "content": pregunta}],
        )
        return r.choices[0].message.content.strip()


class AzureProveedor(OpenAIProveedor):
    """Azure OpenAI (lo que usa Copilot por detrás)."""
    nombre = "azure"

    def _cliente(self):
        from openai import AzureOpenAI
        return AzureOpenAI(api_key=settings.IA_API_KEY,
                           azure_endpoint=settings.IA_AZURE_ENDPOINT,
                           api_version="2024-02-01")


class GeminiProveedor(ProveedorIA):
    nombre = "gemini"

    def responder(self, sistema, pregunta):
        import google.generativeai as genai  # pip install google-generativeai
        genai.configure(api_key=settings.IA_API_KEY)
        modelo = genai.GenerativeModel(settings.IA_MODELO, system_instruction=sistema)
        return modelo.generate_content(pregunta).text.strip()


PROVEEDORES = {p.nombre: p for p in
               [MockProveedor, ClaudeProveedor, OpenAIProveedor, AzureProveedor, GeminiProveedor]}


def get_proveedor() -> ProveedorIA:
    clase = PROVEEDORES.get(settings.IA_PROVEEDOR)
    if clase is None:
        raise ValueError(
            f"IA_PROVEEDOR='{settings.IA_PROVEEDOR}' no existe. "
            f"Opciones: {', '.join(PROVEEDORES)}"
        )
    return clase()
