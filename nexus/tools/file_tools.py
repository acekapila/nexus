import os
import glob

def read_file(path: str) -> str:
    """Read contents of a local file."""
    try:
        with open(os.path.expanduser(path), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"❌ File not found: {path}"
    except Exception as e:
        return f"❌ Error reading {path}: {str(e)}"


def write_file(path: str, content: str) -> str:
    """Write content to a local file. Creates parent directories if needed."""
    try:
        path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Written to {path} ({len(content)} chars)"
    except Exception as e:
        return f"❌ Error writing {path}: {str(e)}"


def list_files(directory: str) -> str:
    """List files in a directory recursively (max 2 levels)."""
    try:
        directory = os.path.expanduser(directory)
        if not os.path.exists(directory):
            return f"❌ Directory not found: {directory}"
        results = []
        for root, dirs, files in os.walk(directory):
            # Limit depth
            depth = root.replace(directory, "").count(os.sep)
            if depth >= 2:
                dirs.clear()
            indent = "  " * depth
            results.append(f"{indent}📁 {os.path.basename(root)}/")
            for f in files:
                size = os.path.getsize(os.path.join(root, f))
                results.append(f"{indent}  📄 {f} ({size} bytes)")
        return "\n".join(results) if results else f"Empty directory: {directory}"
    except Exception as e:
        return f"❌ Error listing {directory}: {str(e)}"
