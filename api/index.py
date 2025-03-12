from mangum import Mangum
from main import app  # Adjust this if your FastAPI app file is named differently

# Create a handler that Vercel will use as the entrypoint
handler = Mangum(app)
