from fastapi import FastAPI

app = FastAPI(title='AI Finance CRM API', version='0.1.0')

@app.get('/')
def root():
    return {
        'name': 'AI Finance CRM API',
        'status': 'running',
        'version': '0.1.0'
    }

@app.get('/health')
def health():
    return {'status':'ok'}
