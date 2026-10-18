"""
Capa de proveedores de IA.

Todo el proyecto usa get_proveedor().responder(sistema, pregunta) o
get_proveedor().completar(sistema, mensajes). Cuál proveedor se usa se decide
en .env con IA_PROVEEDOR, así cambiar de Claude a OpenAI/Azure/Gemini en otra
empresa no requiere tocar código. Hay que instalar el SDK del que se use
(ver requirements.txt).

mensajes es una lista de {"role": "user" | "assistant", "content": "..."}.
"""
from django.conf import settings


MODELOS_POR_DEFECTO = {
    "claude": "claude-sonnet-5-5",
    "openai": "gpt-4.1",
    "azure": "gpt-4.1",
    "gemini": "gemini-2.5-flash",
}


class ProveedorIA:
    nombre = "base"
    simulado = False

    @property
    def modelo(self):
        return settings.IA_MODELO or MODELOS_POR_DEFECTO.get(self.nombre, "")

    def completar(self, sistema: str, mensajes: list, max_tokens: int = 1500) -> str:
        raise NotImplementedError

    def responder(self, sistema: str, pregunta: str) -> str:
        return self.completar(sistema, [{"role": "user", "content": pregunta}])


class MockProveedor(ProveedorIA):
    """Respuestas fijas para desarrollar la interfaz sin gastar tokens."""
    nombre = "mock"
    simulado = True

    def completar(self, sistema, mensajes, max_tokens=1500):
        pregunta = mensajes[-1]["content"] if mensajes else ""
        return (
            f"Respuesta de ejemplo a: «{pregunta}».\n\n"
            "El asistente todavía no está conectado a un modelo real. "
            "Cuando configures IA_PROVEEDOR e IA_API_KEY en el archivo .env, "
            "esta respuesta la va a generar el modelo usando los datos del módulo."
        )


class ClaudeProveedor(ProveedorIA):
    nombre = "claude"

    def completar(self, sistema, mensajes, max_tokens=1500):
        import anthropic  # pip install anthropic
        cliente = anthropic.Anthropic(api_key=settings.IA_API_KEY)
        r = cliente.messages.create(
            model=self.modelo,
            max_tokens=max_tokens,
            # El texto del sistema (esquema de la base) se repite en cada pregunta: se cachea
            system=[{"type": "text", "text": sistema, "cache_control": {"type": "ephemeral"}}],
            messages=mensajes,
        )
        return "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()


class OpenAIProveedor(ProveedorIA):
    nombre = "openai"

    def _cliente(self):
        from openai import OpenAI  # pip install openai
        return OpenAI(api_key=settings.IA_API_KEY)

    def completar(self, sistema, mensajes, max_tokens=1500):
        r = self._cliente().chat.completions.create(
            model=self.modelo,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": sistema}] + mensajes,
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

    def completar(self, sistema, mensajes, max_tokens=1500):
        import google.generativeai as genai  # pip install google-generativeai
        genai.configure(api_key=settings.IA_API_KEY)
        modelo = genai.GenerativeModel(self.modelo, system_instruction=sistema)
        historial = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [m["content"]]}
                     for m in mensajes]
        r = modelo.generate_content(historial, generation_config={"max_output_tokens": max_tokens})
        return r.text.strip()


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
