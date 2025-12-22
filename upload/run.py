import sys
import os

# 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from upload import create_app

app = create_app()

if __name__ == "__main__":
    import os
    port_number = os.environ['INTERNAL_HTTP_PORT']
    app.run(port=port_number, host='0.0.0.0')
