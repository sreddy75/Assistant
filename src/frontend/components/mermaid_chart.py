import streamlit.components.v1 as components

def render_mermaid(code: str, height: int = 100):
    html = f"""
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@8.14.0/dist/mermaid.min.js"></script>
    </head>
    <body>
        <pre class="mermaid" style="height: {height}px;">
            {code}
        </pre>
        <script>
            mermaid.initialize({{ startOnLoad: true, securityLevel: 'loose', logLevel: 'error' }});
        </script>
    </body>
    </html>
    """
    components.html(html, height=height+10, scrolling=True)