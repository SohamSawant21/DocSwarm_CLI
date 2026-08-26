import json
from pathlib import Path
from core.models import AnalysisResult

class HTMLReporter:
    @staticmethod
    def export(result: AnalysisResult, output_dir: str = ".docswarm"):
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        file_path = out_path / "interactive_report.html"
        
        # Serialize and escape payload
        data = result.model_dump()
        json_str = json.dumps(data)
        
        # Safe escape for script blocks
        json_str = json_str.replace("<", "\\u003c")
        json_str = json_str.replace(">", "\\u003e")
        json_str = json_str.replace("&", "\\u0026")
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>DocSwarm Architecture Report</title>
    <style>
        body {{ margin: 0; padding: 0; font-family: sans-serif; overflow: hidden; background: #1e1e1e; color: #fff; }}
        #info {{ position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.7); padding: 10px; border-radius: 5px; }}
        canvas {{ display: block; }}
    </style>
</head>
<body>
    <div id="info">Hover over a node</div>
    <canvas id="graphCanvas"></canvas>
    <script id="docswarm-data" type="application/json">{json_str}</script>
    <script>
        const rawData = document.getElementById('docswarm-data').textContent;
        const data = JSON.parse(rawData);
        
        const canvas = document.getElementById('graphCanvas');
        const ctx = canvas.getContext('2d');
        let width = window.innerWidth;
        let height = window.innerHeight;
        canvas.width = width;
        canvas.height = height;
        
        window.addEventListener('resize', () => {{
            width = window.innerWidth;
            height = window.innerHeight;
            canvas.width = width;
            canvas.height = height;
            draw();
        }});
        
        // Build graph
        const nodes = [];
        const edges = [];
        const nodeMap = {{}};
        
        // Deterministic sorting of node IDs for consistent initial positions
        const sortedNodeIds = Object.keys(data.graph.nodes).sort();
        
        // Seeded RNG for deterministic positions
        let seed = 12345;
        function random() {{
            seed = (seed * 9301 + 49297) % 233280;
            return seed / 233280;
        }}
        
        for (const id of sortedNodeIds) {{
            const node = data.graph.nodes[id];
            const n = {{
                id: id,
                name: node.name,
                role: node.role,
                x: random() * width,
                y: random() * height,
                vx: 0,
                vy: 0
            }};
            nodes.push(n);
            nodeMap[id] = n;
        }}
        
        for (const node of nodes) {{
            const rawNode = data.graph.nodes[node.id];
            for (const dep of rawNode.dependencies) {{
                if (nodeMap[dep.target_id]) {{
                    edges.push({{ source: node, target: nodeMap[dep.target_id] }});
                }}
            }}
        }}
        
        // Simple force layout
        function simulationStep() {{
            const k = Math.sqrt(width * height / nodes.length) || 100;
            
            // Repulsion
            for (let i = 0; i < nodes.length; i++) {{
                for (let j = i + 1; j < nodes.length; j++) {{
                    const u = nodes[i];
                    const v = nodes[j];
                    const dx = u.x - v.x;
                    const dy = u.y - v.y;
                    const distSq = dx * dx + dy * dy;
                    if (distSq > 0 && distSq < k * k * 10) {{
                        const dist = Math.sqrt(distSq);
                        const force = (k * k) / dist;
                        const fx = (dx / dist) * force;
                        const fy = (dy / dist) * force;
                        u.vx += fx;
                        u.vy += fy;
                        v.vx -= fx;
                        v.vy -= fy;
                    }}
                }}
            }}
            
            // Attraction
            for (const edge of edges) {{
                const u = edge.source;
                const v = edge.target;
                const dx = v.x - u.x;
                const dy = v.y - u.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist > 0) {{
                    const force = (dist * dist) / k;
                    const fx = (dx / dist) * force;
                    const fy = (dy / dist) * force;
                    u.vx += fx;
                    u.vy += fy;
                    v.vx -= fx;
                    v.vy -= fy;
                }}
            }}
            
            // Gravity to center
            const cx = width / 2;
            const cy = height / 2;
            for (const node of nodes) {{
                const dx = cx - node.x;
                const dy = cy - node.y;
                node.vx += dx * 0.05;
                node.vy += dy * 0.05;
            }}
            
            // Update positions
            for (const node of nodes) {{
                node.vx *= 0.8;
                node.vy *= 0.8;
                node.x += node.vx * 0.1;
                node.y += node.vy * 0.1;
            }}
        }}
        
        let hoveredNode = null;
        
        canvas.addEventListener('mousemove', (e) => {{
            const rect = canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;
            
            hoveredNode = null;
            for (const node of nodes) {{
                const dx = mouseX - node.x;
                const dy = mouseY - node.y;
                if (dx*dx + dy*dy < 400) {{
                    hoveredNode = node;
                    break;
                }}
            }}
            
            if (hoveredNode) {{
                document.getElementById('info').innerText = hoveredNode.id + ' (' + hoveredNode.role + ')';
            }} else {{
                document.getElementById('info').innerText = 'Hover over a node';
            }}
        }});
        
        function draw() {{
            ctx.clearRect(0, 0, width, height);
            
            // Draw edges
            ctx.strokeStyle = '#555';
            ctx.lineWidth = 1;
            for (const edge of edges) {{
                ctx.beginPath();
                ctx.moveTo(edge.source.x, edge.source.y);
                ctx.lineTo(edge.target.x, edge.target.y);
                ctx.stroke();
            }}
            
            // Draw nodes
            for (const node of nodes) {{
                ctx.beginPath();
                ctx.arc(node.x, node.y, 10, 0, 2 * Math.PI);
                ctx.fillStyle = node === hoveredNode ? '#ff0' : '#0af';
                ctx.fill();
                ctx.strokeStyle = '#fff';
                ctx.stroke();
            }}
        }}
        
        function animate() {{
            for (let i = 0; i < 5; i++) simulationStep();
            draw();
            requestAnimationFrame(animate);
        }}
        
        animate();
    </script>
</body>
</html>"""
        
        file_path.write_text(html_content, encoding="utf-8")
        return str(file_path)
