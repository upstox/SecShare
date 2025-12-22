import sys
import os

# Add the parent directory to the Python path to locate 'shared'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from download import create_app

app = create_app()

if __name__ == '__main__':
    import os
    port_number = os.environ['EXTERNAL_HTTP_PORT']
    app.run(port=port_number, host='0.0.0.0')
