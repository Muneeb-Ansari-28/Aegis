"""Tier 2 Localhost Process and Port Discovery via psutil and socket probing."""
import logging
import socket
from typing import Dict, List, Optional
from pydantic import BaseModel

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger(__name__)

COMMON_DEV_PORTS = {
    3000: "Next.js / Node Web App",
    5173: "Vite Development Server",
    8000: "FastAPI / Python Web App",
    8001: "Aegis Weak Bot (Test Target)",
    8002: "Aegis Hardened Bot (Test Target)",
    8501: "Streamlit UI",
    7860: "Gradio UI",
    11434: "Ollama LLM Server",
    1234: "LM Studio Server",
}


class LocalTarget(BaseModel):
    port: int
    pid: Optional[int] = None
    process_name: str = ""
    command_line: str = ""
    cwd: Optional[str] = None
    candidate_url: str = ""
    inferred_technology: Optional[str] = None


class LocalDiscovery:
    """
    Tier 2 discovery mechanism for localhost / pre-deployment targets.
    Maps open TCP listening ports to process IDs, command lines, and candidate project roots.
    """

    @classmethod
    def discover_local_targets(cls, target_ports: Optional[List[int]] = None) -> List[LocalTarget]:
        """
        Discover active listening ports on localhost and resolve process metadata.
        Uses psutil when available, falling back to direct TCP socket probing if
        psutil lacks elevated privileges or fails.
        """
        ports_to_check = set(target_ports or COMMON_DEV_PORTS.keys())
        listening_map: Dict[int, Optional[int]] = {}

        # 1. Attempt psutil net_connections query
        if psutil is not None:
            try:
                connections = psutil.net_connections(kind="inet")
                for conn in connections:
                    if getattr(conn, "status", None) == psutil.CONN_LISTEN:
                        laddr = getattr(conn, "laddr", None)
                        port = getattr(laddr, "port", None)
                        if port is None and isinstance(laddr, tuple) and len(laddr) > 1:
                            port = laddr[1]
                        if port and port in ports_to_check:
                            listening_map[port] = getattr(conn, "pid", None)
            except Exception as e:
                logger.debug(f"psutil.net_connections failed (likely non-admin OS environment): {e}")

        # 2. Socket-level fallback probe for any unmapped ports
        unmapped_ports = ports_to_check - set(listening_map.keys())
        for port in unmapped_ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.08)
                    if s.connect_ex(("127.0.0.1", port)) == 0:
                        listening_map[port] = None
            except Exception:
                pass

        results: List[LocalTarget] = []

        # 3. Resolve process information for active ports
        for port, pid in listening_map.items():
            proc_name = ""
            cmd_line = ""
            proc_cwd = None
            inferred = COMMON_DEV_PORTS.get(port)

            if pid and psutil is not None:
                try:
                    proc = psutil.Process(pid)
                    try:
                        proc_name = proc.name() or ""
                    except Exception:
                        proc_name = ""
                    try:
                        cmd_line = " ".join(proc.cmdline() or [])
                    except Exception:
                        cmd_line = ""
                    try:
                        proc_cwd = proc.cwd()
                    except Exception:
                        proc_cwd = None

                    # Infer technology from process command line
                    cmd_lower = cmd_line.lower()
                    if "streamlit" in cmd_lower:
                        inferred = "Streamlit"
                    elif "gradio" in cmd_lower:
                        inferred = "Gradio"
                    elif "uvicorn" in cmd_lower or "fastapi" in cmd_lower:
                        inferred = "FastAPI / Uvicorn"
                    elif "next" in cmd_lower:
                        inferred = "Next.js"
                    elif "vite" in cmd_lower:
                        inferred = "Vite"
                    elif "ollama" in cmd_lower:
                        inferred = "Ollama"
                except Exception:
                    pass

            results.append(
                LocalTarget(
                    port=port,
                    pid=pid,
                    process_name=proc_name,
                    command_line=cmd_line,
                    cwd=proc_cwd,
                    candidate_url=f"http://localhost:{port}",
                    inferred_technology=inferred,
                )
            )

        return sorted(results, key=lambda t: t.port)

    @classmethod
    def inspect_port(cls, port: int) -> Optional[LocalTarget]:
        """Inspect a single port specifically."""
        found = cls.discover_local_targets([port])
        return found[0] if found else None
