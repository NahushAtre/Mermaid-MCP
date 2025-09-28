import os
import shutil
import subprocess
import tempfile
import base64
import logging
from typing import Optional, Literal

from pydantic import Field, BaseModel

# Import FastMCP
try:
    from fastmcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="mermaid",
    host="0.0.0.0",
    port=3000,
    stateless_http=True,
    debug=False,
)

class RenderResult(BaseModel):
    format: str
    mime: str
    content: str  # SVG text or base64 string for PNG/PDF

def find_mmdc():
    path = shutil.which("mmdc")
    if path:
        return path
    local = os.path.join(os.getcwd(), "node_modules", ".bin", "mmdc")
    if os.path.exists(local) and os.access(local, os.X_OK):
        return local
    if shutil.which("npx"):
        return "npx"
    return None

@mcp.tool(
    title="Render Mermaid diagram",
    description="Render Mermaid source to svg/png/pdf."
)
def render_mermaid(
    diagram: str = Field(..., description="Mermaid source, e.g. 'graph TD; A-->B;'"),
    output_format: Literal["svg", "png", "pdf"] = "svg",
    theme: Optional[str] = "default",
) -> RenderResult:
    mmdc = find_mmdc()
    if not mmdc:
        raise RuntimeError("mmdc not found. Run: npm install -D @mermaid-js/mermaid-cli")

    with tempfile.TemporaryDirectory() as tmp:
        in_file = os.path.join(tmp, "input.mmd")
        out_file = os.path.join(tmp, f"out.{output_format}")

        with open(in_file, "w", encoding="utf-8") as f:
            f.write(diagram)

        cmd = [mmdc, "-i", in_file, "-o", out_file, "--theme", theme]
        subprocess.run(cmd, check=True)

        if output_format == "svg":
            with open(out_file, "r", encoding="utf-8") as f:
                return RenderResult(format="svg", mime="image/svg+xml", content=f.read())
        else:
            with open(out_file, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            mime = "image/png" if output_format == "png" else "application/pdf"
            return RenderResult(format=output_format, mime=mime, content=b64)

if __name__ == "__main__":
    print(">>> Starting Mermaid MCP server on http://localhost:3000")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=3000)
