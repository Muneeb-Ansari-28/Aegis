"""Tier 2 Localhost Process and Port Discovery via psutil."""
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

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
        """
        if psutil is None:
            logger.warning("psutil is not installed; local port discovery unavailable.")
            return []

        ports_to_check = set(target_ports or COMMON_DEV_PORTS.keys())
        results: List[LocalTarget] = []

        try:
            connections = psutil.net_connections(kind="inet")
        except Exception as e:
            logger.warning(f"Failed to query network connections with psutil: {e}")
            return []

        listening_map: Dict[int, int] = {}
        for conn in connections:
            if conn.status == psutil.CONN_LISTEN:
                laddr = conn.laddr
                port = laddr.port
                if port in ports_to_check:
                    listening_map[port] = conn.pid

        # Also probe ports to see if connection is actively answering
        for port, pid in listening_map.items():
            proc_name = ""
            cmd_line = ""
            proc_cwd = None
            inferred = COMMON_DEV_PORTS.get(port)

            if pid:
                try:
                    proc = psutil.Process(pid)
                    proc_name = proc.name()
                    cmd_line = " ".join(proc.cmdline() or [])
                    try:
                        proc_cwd = proc.cwd()
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        proc_cwd = None

                    # Infer technology from command line
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
                except (psutil.NoSuchProcess, psutil.AccessDenied):
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

