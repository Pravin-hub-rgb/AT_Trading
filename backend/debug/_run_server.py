import sys
import os
# backend/debug/ -> backend/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import server
import uvicorn
uvicorn.run('server:app', host='0.0.0.0', port=8003, reload=False)
