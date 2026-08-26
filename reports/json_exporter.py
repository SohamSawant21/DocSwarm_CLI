import json
from pathlib import Path
from core.models import AnalysisResult

class JSONExporter:
    @staticmethod
    def export(result: AnalysisResult, output_dir: str = ".docswarm"):
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        file_path = out_path / "graph.json"
        if not file_path.resolve().is_relative_to(Path(output_dir).resolve()):
            raise ValueError("Output path escapes target directory")

        # Create structured dictionary combining GraphModel and Analysis
        # using their built-in model_dump to ensure clean serialization
        data = result.model_dump()
        
        # Guarantee list determinism
        for node_id, node_data in data["graph"]["nodes"].items():
            node_data["dependencies"] = sorted(node_data["dependencies"], key=lambda d: (d["target_id"], d["type"]))
            node_data["imports"] = sorted(node_data["imports"])
            
        data["analysis"]["cycles"] = sorted([sorted(c) for c in data["analysis"]["cycles"]])
        data["analysis"]["hotspots"] = sorted(data["analysis"]["hotspots"], key=lambda h: (h["node"], h["metric"]))
        data["analysis"]["violations"] = sorted(data["analysis"]["violations"], key=lambda v: (v["rule_id"], v["message"]))
        
        # Write deterministically using sort_keys=True
        file_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return str(file_path)
