import uvicorn
import os
import sys

# Ensure backend directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    print("============================================================")
    print(" Starting Telecom Customer & Diwali Offers Server")
    print("============================================================")
    print(" Web App URL : http://127.0.0.1:8000")
    print(" Swagger Docs: http://127.0.0.1:8000/docs")
    print(" Database    : backend/telecom.db (SQLite)")
    print("============================================================")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False, app_dir=backend_dir)
